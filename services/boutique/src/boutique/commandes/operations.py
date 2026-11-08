"""Opérations sur les commandes, partagées par l'espace client et la gestion."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.commandes import acces
from boutique.commandes.cycle import EN_ATTENTE_DE_L_EQUIPE, ModeLivraison, ModePaiement, Statut
from boutique.commandes.schemas import Coordonnees, LigneDemandee, Livraison
from boutique.commandes.tarifs import (
    Demande,
    LigneTarifee,
    aujourd_hui,
    charger_produits,
    date_estimee,
    frais_de_livraison,
    tarifer,
)
from boutique.config import ROLE_PRO, ParametresBoutique
from boutique.models import Commande, EvenementCommande, JournalAudit, LigneCommande, ZoneLivraison
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


async def estimer_date(session: AsyncSession, commande: Commande) -> date:
    """Date promise : délai de fabrication le plus long des articles, plus la livraison."""
    produits = await charger_produits(
        session, (ligne.produit_id for ligne in commande.lignes if ligne.produit_id)
    )
    fabrication = max((p.delai_jours for p in produits.values()), default=0)
    transport = commande.zone.delai_jours if commande.zone is not None else 0
    return aujourd_hui() + timedelta(days=fabrication + transport)


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
        date_promise=date_estimee(tarifees, livraison.mode, zone)
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
