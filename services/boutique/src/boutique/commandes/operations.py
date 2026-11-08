"""Opérations sur les commandes, partagées par l'espace client et la gestion."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.atelier import delais, fabrication, stock
from boutique.atelier.etats import EtatOrdre
from boutique.commandes import acces, factures
from boutique.commandes.cycle import EN_ATTENTE_DE_L_EQUIPE, ModeLivraison, ModePaiement, Statut
from boutique.commandes.schemas import Coordonnees, LigneDemandee, Livraison
from boutique.commandes.tarifs import (
    Demande,
    LigneTarifee,
    charger_produits,
    frais_de_livraison,
    jours_de_transport,
    tarifer,
)
from boutique.config import ROLE_PRO, ParametresBoutique
from boutique.models import (
    Commande,
    EvenementCommande,
    JournalAudit,
    LigneCommande,
    OrdreFabrication,
    Produit,
    ZoneLivraison,
)
from boutique.notifications import boite
from socle.audit import journaliser
from socle.security import Principal
from socle.telephones import NumeroInvalide, normaliser_telephone

_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


@dataclass
class Nouvelle:
    commande: Commande
    cle: str
    creee: bool  # faux quand la même demande arrive une seconde fois (réseau instable)


def telephone(brut: str) -> str:
    try:
        return normaliser_telephone(brut)
    except NumeroInvalide as exc:
        raise HTTPException(_422, "Numéro de téléphone invalide") from exc


async def zone_de(session: AsyncSession, livraison: Livraison) -> ZoneLivraison | None:
    if livraison.mode == ModeLivraison.RETRAIT:
        return None
    if livraison.zone_id is None:
        raise HTTPException(_422, "Choisissez une zone de livraison")
    zone = await session.get(ZoneLivraison, livraison.zone_id)
    if zone is None or not zone.est_active:
        raise HTTPException(_422, "Nous ne livrons pas encore dans cette zone")
    if len(livraison.adresse.strip()) < 5:
        raise HTTPException(_422, "Indiquez l'adresse de livraison : quartier, rue, repère")
    return zone


def demandes(lignes: Sequence[LigneDemandee]) -> list[Demande]:
    return [
        Demande(ligne.produit_id, ligne.variante_id, ligne.quantite, ligne.personnalisation)
        for ligne in lignes
    ]


def refuser_si_non_commandable(lignes: Sequence[LigneTarifee]) -> None:
    refus = next((ligne for ligne in lignes if not ligne.commandable), None)
    if refus is not None:
        raise HTTPException(_422, f"{refus.libelle} : {refus.motif}")


def evenement(
    commande: Commande,
    statut: Statut,
    acteur_id: UUID | None,
    note: str = "",
    visible_client: bool = True,
) -> None:
    commande.statut = statut
    commande.evenements.append(
        EvenementCommande(
            statut=statut, note=note, visible_client=visible_client, acteur_id=acteur_id
        )
    )


async def produits_de(session: AsyncSession, commande: Commande) -> dict[UUID, Produit]:
    return await charger_produits(
        session, (ligne.produit_id for ligne in commande.lignes if ligne.produit_id)
    )


async def estimer_date(
    session: AsyncSession, commande: Commande, produits: dict[UUID, Produit] | None = None
) -> date:
    """Date promise selon la charge de l'atelier, le stock et le délai de livraison."""
    produits = produits if produits is not None else await produits_de(session, commande)
    articles = [
        delais.Article(
            produit.id,
            ligne.variante_id,
            produit.poste_atelier,
            produit.delai_jours,
            ligne.quantite,
        )
        for ligne in commande.lignes
        if ligne.produit_id and (produit := produits.get(ligne.produit_id)) is not None
    ]
    transport = commande.zone.delai_jours if commande.zone is not None else 0
    return await delais.estimer(session, articles, transport)


async def appliquer_statut(
    session: AsyncSession,
    commande: Commande,
    statut: Statut,
    acteur_id: UUID | None,
    note: str = "",
    visible_client: bool = True,
) -> None:
    """Change le statut et ses effets : ordres de fabrication à la confirmation, stock prélevé
    quand la commande est prête, facture à la livraison, ordres annulés et stock rendu à
    l'annulation."""
    produits = await produits_de(session, commande)
    if statut == Statut.CONFIRMEE:
        if commande.date_promise is None:
            commande.date_promise = await estimer_date(session, commande, produits)
        await fabrication.creer_ordres(session, commande, produits)
    elif statut == Statut.PRETE:
        await stock.prelever(session, commande, produits, acteur_id)
    elif statut == Statut.ANNULEE:
        await fabrication.annuler_ordres(session, commande.id)
        await stock.restituer(session, commande, acteur_id)
    elif statut == Statut.LIVREE:
        await factures.emettre(session, commande, acteur_id)
    evenement(commande, statut, acteur_id, note, visible_client)
    if visible_client:
        boite.apres_changement(session, commande, statut)


async def apres_changement_ordre(
    session: AsyncSession, ordre: OrdreFabrication, acteur_id: UUID | None
) -> None:
    """La commande suit son atelier : en préparation dès la première pièce commencée, prête
    quand tout est fabriqué (sauf s'il reste des articles en stock à préparer)."""
    commande = await acces.charger_par_id(session, ordre.commande_id)
    statut = Statut(commande.statut)
    if ordre.etat == EtatOrdre.EN_COURS and statut == Statut.CONFIRMEE:
        await appliquer_statut(
            session, commande, Statut.EN_PREPARATION, acteur_id, "Fabrication commencée"
        )
        statut = Statut.EN_PREPARATION
    etats = await fabrication.etats_des_ordres(session, commande.id)
    if statut not in (Statut.CONFIRMEE, Statut.EN_PREPARATION) or not etats:
        return
    if all(etat == EtatOrdre.TERMINE for etat in etats):
        produits = await produits_de(session, commande)
        reste_en_stock = any(
            stock.est_en_stock(produits.get(ligne.produit_id)) if ligne.produit_id else False
            for ligne in commande.lignes
        )
        if reste_en_stock:
            evenement(
                commande,
                statut,
                acteur_id,
                "Fabrication terminée : articles en stock à préparer",
                visible_client=False,
            )
        else:
            await appliquer_statut(
                session, commande, Statut.PRETE, acteur_id, "Fabrication terminée"
            )


async def creer(
    session: AsyncSession,
    parametres: ParametresBoutique,
    *,
    statut: Statut,
    coordonnees: Coordonnees,
    livraison: Livraison,
    lignes: Sequence[LigneDemandee],
    note: str,
    cle: str | None,
    principal: Principal | None,
    adresse_ip: str | None,
    etablissement: str | None = None,
    email: str | None = None,
) -> Nouvelle:
    cle = cle or acces.nouvelle_cle()
    deja = await acces.charger_par_cle(session, cle)
    if deja is not None:
        return Nouvelle(deja, cle, creee=False)

    numero = telephone(coordonnees.telephone)
    zone = await zone_de(session, livraison)
    recentes = await session.scalar(
        select(func.count(Commande.id)).where(
            Commande.telephone == numero,
            Commande.statut.in_(EN_ATTENTE_DE_L_EQUIPE),
            Commande.cree_le >= datetime.now(UTC) - timedelta(hours=24),
        )
    )
    if (recentes or 0) >= parametres.demandes_max_par_telephone:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Plusieurs demandes de ce numéro attendent déjà notre appel. Nous vous rappelons "
            "très vite pour les confirmer.",
        )

    professionnel = principal is not None and principal.a_role(ROLE_PRO)
    tarifees = await tarifer(session, demandes(lignes), professionnel)
    refuser_si_non_commandable(tarifees)
    sous_total = sum(ligne.montant for ligne in tarifees)
    frais = frais_de_livraison(livraison.mode, zone)
    acteur = principal.id if principal else None
    commande = Commande(
        statut=statut,
        client_id=acteur,
        nom_client=coordonnees.nom.strip(),
        telephone=numero,
        email=email,
        etablissement=etablissement.strip() if etablissement else None,
        mode_livraison=livraison.mode,
        zone_id=zone.id if zone else None,
        adresse=livraison.adresse.strip(),
        note_client=note.strip(),
        mode_paiement=ModePaiement.A_LA_LIVRAISON,
        sous_total=sous_total,
        frais_livraison=frais,
        remise=0,
        total=sous_total + frais,
        date_promise=await delais.estimer(
            session,
            [delais.article(ligne) for ligne in tarifees],
            jours_de_transport(livraison.mode, zone),
        )
        if statut == Statut.EN_ATTENTE
        else None,
        empreinte_cle_suivi=acces.empreinte(cle),
    )
    commande.lignes = [
        LigneCommande(
            produit_id=ligne.produit_id,
            variante_id=ligne.variante_id,
            libelle=ligne.libelle,
            sku=ligne.sku,
            quantite=ligne.quantite,
            prix_unitaire=ligne.prix_unitaire or 0,
            montant=ligne.montant,
            personnalisation=ligne.personnalisation,
            position=position,
        )
        for position, ligne in enumerate(tarifees)
    ]
    commande.evenements = [EvenementCommande(statut=statut, acteur_id=acteur)]
    session.add(commande)
    try:
        await session.flush()
    except IntegrityError:
        # Deux envois simultanés de la même demande : le premier l'a enregistrée.
        await session.rollback()
        deja = await acces.charger_par_cle(session, cle)
        if deja is None:
            raise
        return Nouvelle(deja, cle, creee=False)
    reference = commande.reference
    base = parametres.url_publique.rstrip("/")
    boite.apres_creation(session, commande, f"{base}/suivi/{reference}?cle={cle}" if base else None)
    journaliser(
        session,
        JournalAudit,
        action="devis.demande" if statut == Statut.DEVIS_DEMANDE else "commande.creee",
        acteur_id=acteur,
        objet_type="commande",
        objet_id=reference,
        details={"total": commande.total, "lignes": len(tarifees)},
        adresse_ip=adresse_ip,
    )
    await session.commit()
    return Nouvelle(await acces.charger(session, reference), cle, creee=True)
