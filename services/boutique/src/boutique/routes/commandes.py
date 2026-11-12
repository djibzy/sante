"""Espace client : chiffrer un panier, commander, demander un devis, suivre sa commande.

Sans compte, le client suit sa commande grâce à la clé secrète de son lien de suivi ; avec un
compte, il retrouve aussi ses commandes dans « Mes commandes ».
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.atelier import delais
from boutique.commandes import acces, operations
from boutique.commandes.cycle import ANNULABLES_PAR_CLIENT, Statut
from boutique.commandes.pdf import reponse_devis, reponse_facture
from boutique.commandes.schemas import (
    Chiffrage,
    CommandeClient,
    CommandeCreee,
    CommandeResume,
    CreationCommande,
    CreationDevis,
    DemandeChiffrage,
    LigneChiffree,
    ZonePublique,
)
from boutique.commandes.tarifs import frais_de_livraison, jours_de_transport, tarifer
from boutique.commandes.vues import devis_expire, vue_client, vue_resume
from boutique.config import ROLE_PRO, ParametresBoutique
from boutique.models import Commande, JournalAudit, ZoneLivraison
from socle.audit import journaliser
from socle.db import session_db
from socle.limites import LimiteDebit
from socle.security import Principal, principal_optionnel, principal_requis

routeur = APIRouter(prefix="/api/v1", tags=["commandes"])
# Par adresse IP. Les opérateurs mobiles partagent une même adresse entre de nombreux abonnés :
# des seuils larges, la vraie limite étant celle des demandes en attente par téléphone.
LIMITE_DEMANDES = Depends(LimiteDebit("demandes", nombre=60, secondes=600))
LIMITE_LECTURES = Depends(LimiteDebit("lectures", nombre=300, secondes=60))
CLE = Query(None, max_length=64, description="Clé du lien de suivi")


def _parametres(request: Request) -> ParametresBoutique:
    parametres: ParametresBoutique = request.app.state.parametres
    return parametres


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@routeur.get("/zones-livraison", summary="Zones de livraison et leurs frais")
async def zones(session: AsyncSession = Depends(session_db)) -> list[ZonePublique]:
    requete = (
        select(ZoneLivraison)
        .where(ZoneLivraison.est_active)
        .order_by(ZoneLivraison.position, ZoneLivraison.nom)
    )
    return [ZonePublique.model_validate(z) for z in (await session.execute(requete)).scalars()]


@routeur.post(
    "/panier/chiffrage",
    summary="Prix, frais et date estimée d'un panier",
    dependencies=[LIMITE_LECTURES],
)
async def chiffrer(
    demande: DemandeChiffrage,
    principal: Principal | None = Depends(principal_optionnel),
    session: AsyncSession = Depends(session_db),
) -> Chiffrage:
    professionnel = principal is not None and principal.a_role(ROLE_PRO)
    lignes = await tarifer(session, operations.demandes(demande.lignes), professionnel)
    zone = None
    if demande.livraison.zone_id is not None:
        zone = await session.get(ZoneLivraison, demande.livraison.zone_id)
        zone = zone if zone is not None and zone.est_active else None
    sous_total = sum(ligne.montant for ligne in lignes)
    frais = frais_de_livraison(demande.livraison.mode, zone)
    return Chiffrage(
        lignes=[
            LigneChiffree(
                produit_id=ligne.produit_id,
                variante_id=ligne.variante_id,
                produit_slug=ligne.produit_slug,
                libelle=ligne.libelle,
                sku=ligne.sku,
                quantite=ligne.quantite,
                prix_unitaire=ligne.prix_unitaire,
                montant=ligne.montant,
                personnalisation=ligne.personnalisation,
                commandable=ligne.commandable,
                motif=ligne.motif,
            )
            for ligne in lignes
        ],
        sous_total=sous_total,
        frais_livraison=frais,
        total=sous_total + frais,
        date_estimee=await delais.estimer(
            session,
            [delais.article(ligne) for ligne in lignes if ligne.commandable],
            jours_de_transport(demande.livraison.mode, zone),
        ),
        commandable=all(ligne.commandable for ligne in lignes),
    )


@routeur.post(
    "/commandes",
    status_code=status.HTTP_201_CREATED,
    summary="Passer commande, paiement à la livraison",
    dependencies=[LIMITE_DEMANDES],
)
async def commander(
    donnees: CreationCommande,
    request: Request,
    response: Response,
    principal: Principal | None = Depends(principal_optionnel),
    session: AsyncSession = Depends(session_db),
) -> CommandeCreee:
    nouvelle = await operations.creer(
        session,
        _parametres(request),
        statut=Statut.EN_ATTENTE,
        coordonnees=donnees.client,
        livraison=donnees.livraison,
        lignes=donnees.lignes,
        note=donnees.note,
        cle=donnees.cle_suivi,
        principal=principal,
        adresse_ip=_ip(request),
    )
    if not nouvelle.creee:
        response.status_code = status.HTTP_200_OK
    return CommandeCreee(commande=vue_client(nouvelle.commande), cle_suivi=nouvelle.cle)


@routeur.post(
    "/devis",
    status_code=status.HTTP_201_CREATED,
    summary="Demander un devis (structures)",
    dependencies=[LIMITE_DEMANDES],
)
async def demander_devis(
    donnees: CreationDevis,
    request: Request,
    response: Response,
    principal: Principal | None = Depends(principal_optionnel),
    session: AsyncSession = Depends(session_db),
) -> CommandeCreee:
    nouvelle = await operations.creer(
        session,
        _parametres(request),
        statut=Statut.DEVIS_DEMANDE,
        coordonnees=donnees.client,
        livraison=donnees.livraison,
        lignes=donnees.lignes,
        note=donnees.note,
        cle=donnees.cle_suivi,
        principal=principal,
        adresse_ip=_ip(request),
        etablissement=donnees.etablissement,
        email=donnees.email,
    )
    if not nouvelle.creee:
        response.status_code = status.HTTP_200_OK
    return CommandeCreee(commande=vue_client(nouvelle.commande), cle_suivi=nouvelle.cle)


@routeur.get(
    "/suivi/{reference}",
    summary="Suivre une commande avec son lien",
    dependencies=[LIMITE_LECTURES],
)
async def suivre(
    reference: str, cle: str | None = CLE, session: AsyncSession = Depends(session_db)
) -> CommandeClient:
    return vue_client(await acces.charger_pour_client(session, reference, cle))


async def _annuler(
    session: AsyncSession, commande: Commande, acteur: Principal | None, ip: str | None
) -> CommandeClient:
    if Statut(commande.statut) not in ANNULABLES_PAR_CLIENT:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cette commande est déjà confirmée : appelez-nous pour l'annuler.",
        )
    acteur_id = acteur.id if acteur else None
    await operations.appliquer_statut(
        session, commande, Statut.ANNULEE, acteur_id, "Annulée par le client"
    )
    journaliser(
        session,
        JournalAudit,
        action="commande.annulee_par_client",
        acteur_id=acteur_id,
        objet_type="commande",
        objet_id=commande.reference,
        adresse_ip=ip,
    )
    await session.commit()
    return vue_client(await acces.charger(session, commande.reference))


async def _accepter(
    session: AsyncSession, commande: Commande, acteur: Principal | None, ip: str | None
) -> CommandeClient:
    if commande.statut != Statut.DEVIS_ENVOYE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce devis ne peut pas être accepté")
    if devis_expire(commande) and commande.devis_valable_jusqu_au is not None:
        fin = commande.devis_valable_jusqu_au.strftime("%d/%m/%Y")
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ce devis a expiré le {fin}. Demandez-nous de le renouveler.",
        )
    acteur_id = acteur.id if acteur else None
    commande.date_promise = await operations.estimer_date(session, commande)
    await operations.appliquer_statut(
        session, commande, Statut.CONFIRMEE, acteur_id, "Devis accepté par le client"
    )
    journaliser(
        session,
        JournalAudit,
        action="devis.accepte",
        acteur_id=acteur_id,
        objet_type="commande",
        objet_id=commande.reference,
        details={"total": commande.total},
        adresse_ip=ip,
    )
    await session.commit()
    return vue_client(await acces.charger(session, commande.reference))


@routeur.post(
    "/suivi/{reference}/annulation",
    summary="Annuler sa commande ou son devis",
    dependencies=[LIMITE_LECTURES],
)
async def annuler(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> CommandeClient:
    commande = await acces.charger_pour_client(session, reference, cle)
    return await _annuler(session, commande, None, _ip(request))


@routeur.post(
    "/suivi/{reference}/acceptation",
    summary="Accepter le devis reçu",
    dependencies=[LIMITE_LECTURES],
)
async def accepter(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> CommandeClient:
    commande = await acces.charger_pour_client(session, reference, cle)
    return await _accepter(session, commande, None, _ip(request))


@routeur.get(
    "/suivi/{reference}/devis.pdf",
    summary="Télécharger le devis en PDF",
    dependencies=[LIMITE_LECTURES],
)
async def telecharger_devis(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> Response:
    commande = await acces.charger_pour_client(session, reference, cle)
    return reponse_devis(commande, _parametres(request))


async def _mienne(session: AsyncSession, reference: str, principal: Principal) -> Commande:
    return await acces.charger_pour_compte(session, reference, principal.id)


@routeur.get("/mes-commandes", summary="Mes commandes et devis")
async def mes_commandes(
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> list[CommandeResume]:
    requete = (
        acces.requete_resumes()
        .where(Commande.client_id == principal.id)
        .order_by(Commande.cree_le.desc())
        .limit(100)
    )
    return [vue_resume(c, zone, nombre) for c, zone, nombre in await session.execute(requete)]


@routeur.get("/mes-commandes/{reference}", summary="Une de mes commandes")
async def ma_commande(
    reference: str,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> CommandeClient:
    return vue_client(await _mienne(session, reference, principal))


@routeur.post("/mes-commandes/{reference}/annulation", summary="Annuler une de mes commandes")
async def annuler_la_mienne(
    reference: str,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> CommandeClient:
    commande = await _mienne(session, reference, principal)
    return await _annuler(session, commande, principal, _ip(request))


@routeur.post("/mes-commandes/{reference}/acceptation", summary="Accepter un de mes devis")
async def accepter_le_mien(
    reference: str,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> CommandeClient:
    commande = await _mienne(session, reference, principal)
    return await _accepter(session, commande, principal, _ip(request))


@routeur.get(
    "/suivi/{reference}/facture.pdf",
    summary="Télécharger la facture en PDF",
    dependencies=[LIMITE_LECTURES],
)
async def telecharger_facture(
    reference: str,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> Response:
    commande = await acces.charger_pour_client(session, reference, cle)
    return reponse_facture(commande, _parametres(request))


@routeur.get("/mes-commandes/{reference}/facture.pdf", summary="Télécharger une de mes factures")
async def telecharger_ma_facture(
    reference: str,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> Response:
    return reponse_facture(await _mienne(session, reference, principal), _parametres(request))


@routeur.get("/mes-commandes/{reference}/devis.pdf", summary="Télécharger un de mes devis")
async def telecharger_mon_devis(
    reference: str,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> Response:
    return reponse_devis(await _mienne(session, reference, principal), _parametres(request))
