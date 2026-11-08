"""Ordres de fabrication : un par ligne à fabriquer, créés quand la commande est confirmée."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.atelier.etats import OUVERTS, EtatOrdre
from boutique.models import Commande, OrdreFabrication, Produit


async def creer_ordres(
    session: AsyncSession, commande: Commande, produits: dict[UUID, Produit]
) -> int:
    """Crée les ordres manquants (une seule fois par ligne) ; renvoie le nombre créé."""
    existants = set(
        await session.scalars(
            select(OrdreFabrication.ligne_id).where(OrdreFabrication.commande_id == commande.id)
        )
    )
    crees = 0
    for ligne in commande.lignes:
        produit = produits.get(ligne.produit_id) if ligne.produit_id else None
        if produit is None or produit.poste_atelier is None or ligne.id in existants:
            continue
        session.add(
            OrdreFabrication(
                commande_id=commande.id,
                ligne_id=ligne.id,
                poste=produit.poste_atelier,
                libelle=ligne.libelle,
                personnalisation=ligne.personnalisation,
                quantite=ligne.quantite,
                etat=EtatOrdre.A_FAIRE,
                date_promise=commande.date_promise,
            )
        )
        crees += 1
    return crees


async def annuler_ordres(session: AsyncSession, commande_id: UUID) -> None:
    await session.execute(
        update(OrdreFabrication)
        .where(OrdreFabrication.commande_id == commande_id, OrdreFabrication.etat.in_(OUVERTS))
        .values(etat=EtatOrdre.ANNULE)
    )


async def etats_des_ordres(session: AsyncSession, commande_id: UUID) -> list[EtatOrdre]:
    etats = await session.scalars(
        select(OrdreFabrication.etat).where(
            OrdreFabrication.commande_id == commande_id,
            OrdreFabrication.etat != EtatOrdre.ANNULE,
        )
    )
    return [EtatOrdre(e) for e in etats]
