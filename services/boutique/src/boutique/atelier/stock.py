"""Stock des articles vendus tels quels : prélevé quand la commande est prête, rendu si elle
est annulée ensuite."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.atelier.etats import MotifStock
from boutique.models import Commande, MouvementStock, Produit


def est_en_stock(produit: Produit | None) -> bool:
    """Article suivi en stock : vendable en ligne et fabriqué par aucun poste de l'atelier."""
    return produit is not None and produit.vendable_en_ligne and produit.poste_atelier is None


async def _solde_commande(
    session: AsyncSession, commande_id: UUID
) -> dict[tuple[UUID, UUID | None], int]:
    """Quantités prélevées pour la commande et pas encore rendues, article par article."""
    requete = (
        select(
            MouvementStock.produit_id, MouvementStock.variante_id, func.sum(MouvementStock.quantite)
        )
        .where(
            MouvementStock.commande_id == commande_id,
            MouvementStock.motif.in_([MotifStock.VENTE, MotifStock.ANNULATION]),
        )
        .group_by(MouvementStock.produit_id, MouvementStock.variante_id)
    )
    return {(p, v): -int(n) for p, v, n in await session.execute(requete) if n}


async def prelever(
    session: AsyncSession,
    commande: Commande,
    produits: dict[UUID, Produit],
    acteur_id: UUID | None,
) -> None:
    if await _solde_commande(session, commande.id):
        return  # déjà prélevée (retour en boutique après une livraison manquée)
    for ligne in commande.lignes:
        produit = produits.get(ligne.produit_id) if ligne.produit_id else None
        if produit is None or not est_en_stock(produit):
            continue
        session.add(
            MouvementStock(
                produit_id=produit.id,
                variante_id=ligne.variante_id,
                quantite=-ligne.quantite,
                motif=MotifStock.VENTE,
                commande_id=commande.id,
                acteur_id=acteur_id,
            )
        )


async def restituer(session: AsyncSession, commande: Commande, acteur_id: UUID | None) -> None:
    for (produit_id, variante_id), quantite in (
        await _solde_commande(session, commande.id)
    ).items():
        if quantite > 0:
            session.add(
                MouvementStock(
                    produit_id=produit_id,
                    variante_id=variante_id,
                    quantite=quantite,
                    motif=MotifStock.ANNULATION,
                    commande_id=commande.id,
                    acteur_id=acteur_id,
                    note=f"Commande {commande.reference} annulée",
                )
            )
