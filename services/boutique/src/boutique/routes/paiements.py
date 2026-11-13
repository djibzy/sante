"""Paiement mobile en ligne : depuis le lien de suivi, « Mes commandes » ou le lien de
paiement envoyé à un proche, et notifications de l'agrégateur. Éteint tant que
BOUTIQUE_PAIEMENT_MOBILE vaut « aucun »."""

from collections.abc import AsyncIterator
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.avis.service import auteur_de
from boutique.commandes import acces, acompte
from boutique.commandes.cycle import LIBELLES, Statut
from boutique.config import ParametresBoutique
from boutique.models import Commande, JournalAudit
from boutique.paiements import fournisseurs, service
from boutique.paiements.fournisseurs import Fournisseur
from boutique.paiements.schemas import (
    ArticleAPayer,
    ChoixPaiement,
    CommandeAPayer,
    Disponibilite,
    EtatPaiement,
    LienDePaiement,
    PaiementOuvert,
)
from boutique.routes.commandes import CLE, LIMITE_LECTURES
from socle.audit import journaliser
from socle.db import session_db
from socle.limites import LimiteDebit
from socle.security import Principal, principal_requis

routeur = APIRouter(prefix="/api/v1", tags=["paiement en ligne"])
LIMITE_OUVERTURES = Depends(LimiteDebit("paiements", nombre=30, secondes=600))
LIMITE_VERIFICATIONS = Depends(LimiteDebit("verifications-paiement", nombre=60, secondes=60))
LIMITE_NOTIFICATIONS = Depends(LimiteDebit("notifications-paiement", nombre=300, secondes=60))
ETEINT = "Le paiement en ligne n'est pas encore ouvert : vous payez à la livraison."


def _parametres(request: Request) -> ParametresBoutique:
    parametres: ParametresBoutique = request.app.state.parametres
    return parametres


async def agregateur(request: Request) -> AsyncIterator[Fournisseur | None]:
    """Agrégateur configuré (ou rien), avec un client HTTP le temps de la requête. Les tests
    remplacent le réseau par `app.state.transport_paiement`."""
    transport = getattr(request.app.state, "transport_paiement", None)
    async with httpx.AsyncClient(timeout=15, transport=transport) as client:
        yield fournisseurs.fournisseur(_parametres(request), client)


async def _etat(request: Request, session: AsyncSession, commande: Commande) -> EtatPaiement:
    return await service.etat(session, commande, fournisseurs.est_ouvert(_parametres(request)))


async def _payer(
    request: Request,
    session: AsyncSession,
    fournisseur: Fournisseur | None,
    commande: Commande,
    acteur: Principal | None,
    choix: ChoixPaiement | None,
    retour: Literal["suivi", "payer"] = "suivi",
) -> PaiementOuvert:
    if fournisseur is None:
        raise HTTPException(status.HTTP_409_CONFLICT, ETEINT)
    adresse = await service.ouvrir(
        session,
        _parametres(request),
        fournisseur,
        commande,
        acteur.id if acteur else None,
        request.client.host if request.client else None,
        (choix or ChoixPaiement()).objet,
        retour,
    )
    return PaiementOuvert(adresse=adresse)


async def _lien(
    request: Request, session: AsyncSession, commande: Commande, acteur: Principal | None
) -> LienDePaiement:
    """Nouvelle clé de paiement : le lien envoyé auparavant cesse de marcher."""
    if not fournisseurs.est_ouvert(_parametres(request)):
        raise HTTPException(status.HTTP_409_CONFLICT, ETEINT)
    examen = service.examiner(commande)
    if not examen.possible:
        raise HTTPException(
            status.HTTP_409_CONFLICT, examen.raison or "Cette commande ne se paie pas en ligne"
        )
    cle = acces.nouvelle_cle()
    commande.empreinte_cle_paiement = acces.empreinte(cle)
    journaliser(
        session,
        JournalAudit,
        action="commande.lien_de_paiement",
        acteur_id=acteur.id if acteur else None,
        objet_type="commande",
        objet_id=commande.reference,
        adresse_ip=request.client.host if request.client else None,
    )
    await session.commit()
    base = _parametres(request).url_publique.rstrip("/")
    return LienDePaiement(adresse=f"{base}/payer/{commande.reference}?cle={cle}", cle=cle)


async def _verifier(
    request: Request, session: AsyncSession, fournisseur: Fournisseur | None, commande: Commande
) -> EtatPaiement:
    if fournisseur is not None:
        await service.verifier_commande(session, fournisseur, commande)
        commande = await acces.charger_par_id(session, commande.id)
    return await _etat(request, session, commande)


@routeur.get("/paiements/disponibilite", summary="Le paiement mobile en ligne est-il ouvert ?")
async def disponibilite(request: Request) -> Disponibilite:
    ouvert = fournisseurs.est_ouvert(_parametres(request))
    return Disponibilite(disponible=ouvert, moyens=service.MOYENS if ouvert else [])


@routeur.get(
    "/suivi/{reference}/paiement-mobile",
    summary="Paiement en ligne possible, et dernière tentative",
    dependencies=[LIMITE_LECTURES],
)
async def etat_suivi(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> EtatPaiement:
    return await _etat(request, session, await acces.charger_pour_client(session, reference, cle))


@routeur.post(
    "/suivi/{reference}/paiement-mobile",
    summary="Ouvrir le paiement en ligne du reste à payer",
    dependencies=[LIMITE_OUVERTURES],
)
async def payer_suivi(
    reference: str,
    request: Request,
    choix: ChoixPaiement | None = None,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
    fournisseur: Fournisseur | None = Depends(agregateur),
) -> PaiementOuvert:
    commande = await acces.charger_pour_client(session, reference, cle)
    return await _payer(request, session, fournisseur, commande, None, choix)


@routeur.post(
    "/suivi/{reference}/paiement-mobile/verification",
    summary="Relire le paiement en cours (retour de la page de paiement)",
    dependencies=[LIMITE_VERIFICATIONS],
)
async def verifier_suivi(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
    fournisseur: Fournisseur | None = Depends(agregateur),
) -> EtatPaiement:
    commande = await acces.charger_pour_client(session, reference, cle)
    return await _verifier(request, session, fournisseur, commande)


@routeur.get("/mes-commandes/{reference}/paiement-mobile", summary="Paiement en ligne : état")
async def etat_mien(
    reference: str,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> EtatPaiement:
    commande = await acces.charger_pour_compte(session, reference, principal.id)
    return await _etat(request, session, commande)


@routeur.post(
    "/mes-commandes/{reference}/paiement-mobile",
    summary="Paiement en ligne : ouvrir",
    dependencies=[LIMITE_OUVERTURES],
)
async def payer_mien(
    reference: str,
    request: Request,
    choix: ChoixPaiement | None = None,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
    fournisseur: Fournisseur | None = Depends(agregateur),
) -> PaiementOuvert:
    commande = await acces.charger_pour_compte(session, reference, principal.id)
    return await _payer(request, session, fournisseur, commande, principal, choix)


@routeur.post(
    "/mes-commandes/{reference}/paiement-mobile/verification",
    summary="Paiement en ligne : relire",
    dependencies=[LIMITE_VERIFICATIONS],
)
async def verifier_mien(
    reference: str,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
    fournisseur: Fournisseur | None = Depends(agregateur),
) -> EtatPaiement:
    commande = await acces.charger_pour_compte(session, reference, principal.id)
    return await _verifier(request, session, fournisseur, commande)


@routeur.post(
    "/suivi/{reference}/lien-de-paiement",
    status_code=status.HTTP_201_CREATED,
    summary="Créer un lien pour faire payer un proche (remplace le précédent)",
    dependencies=[LIMITE_OUVERTURES],
)
async def lien_suivi(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> LienDePaiement:
    commande = await acces.charger_pour_client(session, reference, cle)
    return await _lien(request, session, commande, None)


@routeur.post(
    "/mes-commandes/{reference}/lien-de-paiement",
    status_code=status.HTTP_201_CREATED,
    summary="Créer un lien pour faire payer un proche (remplace le précédent)",
    dependencies=[LIMITE_OUVERTURES],
)
async def lien_mien(
    reference: str,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> LienDePaiement:
    commande = await acces.charger_pour_compte(session, reference, principal.id)
    return await _lien(request, session, commande, principal)


@routeur.get(
    "/payer/{reference}",
    summary="Commande à payer, vue par le proche qui a reçu le lien",
    dependencies=[LIMITE_LECTURES],
)
async def a_payer(
    reference: str, cle: str | None = CLE, session: AsyncSession = Depends(session_db)
) -> CommandeAPayer:
    commande = await acces.charger_pour_payeur(session, reference, cle)
    return CommandeAPayer(
        reference=commande.reference,
        statut_libelle=LIBELLES[Statut(commande.statut)],
        pour=auteur_de(commande.nom_client),
        articles=[ArticleAPayer(libelle=a.libelle, quantite=a.quantite) for a in commande.lignes],
        total=commande.total,
        montant_paye=commande.montant_paye,
        reste_a_payer=commande.reste_a_payer,
        acompte_restant=acompte.restant(commande),
    )


@routeur.get(
    "/payer/{reference}/paiement-mobile",
    summary="Lien de paiement : paiement possible, et dernière tentative",
    dependencies=[LIMITE_LECTURES],
)
async def etat_payeur(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> EtatPaiement:
    return await _etat(request, session, await acces.charger_pour_payeur(session, reference, cle))


@routeur.post(
    "/payer/{reference}/paiement-mobile",
    summary="Lien de paiement : ouvrir le paiement",
    dependencies=[LIMITE_OUVERTURES],
)
async def payer_payeur(
    reference: str,
    request: Request,
    choix: ChoixPaiement | None = None,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
    fournisseur: Fournisseur | None = Depends(agregateur),
) -> PaiementOuvert:
    commande = await acces.charger_pour_payeur(session, reference, cle)
    return await _payer(request, session, fournisseur, commande, None, choix, "payer")


@routeur.post(
    "/payer/{reference}/paiement-mobile/verification",
    summary="Lien de paiement : relire le paiement en cours",
    dependencies=[LIMITE_VERIFICATIONS],
)
async def verifier_payeur(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
    fournisseur: Fournisseur | None = Depends(agregateur),
) -> EtatPaiement:
    commande = await acces.charger_pour_payeur(session, reference, cle)
    return await _verifier(request, session, fournisseur, commande)


@routeur.api_route(
    "/paiements/retour/{reference}", methods=["GET", "POST"], include_in_schema=False
)
async def retour(
    reference: str,
    request: Request,
    vers: Literal["suivi", "payer"] = Query("suivi"),
) -> RedirectResponse:
    """L'agrégateur renvoie ici (parfois en POST) : le client sur son suivi, le proche sur la
    page de paiement partagée. La clé n'est jamais passée à l'agrégateur : la page la retrouve
    dans l'onglet."""
    numero = acces.numero(reference)  # rien d'autre qu'une référence : pas de redirection libre
    base = _parametres(request).url_publique.rstrip("/")
    return RedirectResponse(
        f"{base}/{vers}/BB-{numero}?paiement=retour", status_code=status.HTTP_303_SEE_OTHER
    )


@routeur.post(
    "/paiements/cinetpay/notification",
    summary="Notification de CinetPay (le statut est relu auprès de CinetPay)",
    dependencies=[LIMITE_NOTIFICATIONS],
)
async def notification_cinetpay(
    request: Request,
    session: AsyncSession = Depends(session_db),
    fournisseur: Fournisseur | None = Depends(agregateur),
) -> Response:
    # Seul l'identifiant de la tentative est lu : le statut et le montant de la notification
    # ne font pas foi, on les redemande à CinetPay avec notre clé.
    formulaire = await request.form()
    transaction_id = str(formulaire.get("cpm_trans_id") or "")[:60]
    site = str(formulaire.get("cpm_site_id") or "")
    attendu = _parametres(request).cinetpay_site_id
    pour_nous = not site or site == attendu
    if fournisseur is not None and fournisseur.nom == "cinetpay" and transaction_id and pour_nous:
        await service.verifier(session, fournisseur, transaction_id)
        await session.commit()
    return Response(status_code=status.HTTP_200_OK)


@routeur.get("/paiements/cinetpay/notification", include_in_schema=False)
async def notification_disponible() -> dict[str, str]:
    """CinetPay vérifie que l'adresse de notification répond."""
    return {"statut": "ok"}
