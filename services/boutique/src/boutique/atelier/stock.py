"""Stock des articles vendus tels quels : prélevé quand la commande est prête, rendu si elle
est annulée ensuite."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from boutique.atelier.delais import niveaux_stock
from boutique.atelier.etats import MotifStock
from boutique.atelier.schemas import LigneStock
from boutique.commandes.cycle import Statut
from boutique.models import (
    CATEGORIE_LIBRE,
    Commande,
    LigneCommande,
    MouvementStock,
    Produit,
    Variante,
)

A_PREPARER = (Statut.CONFIRMEE, Statut.EN_PREPARATION)


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


async def articles_tenus(session: AsyncSession) -> list[tuple[Produit, Variante | None]]:
    produits = await session.scalars(
        select(Produit)
        .options(selectinload(Produit.variantes))
        .where(
            Produit.est_actif,
            Produit.poste_atelier.is_(None),
            Produit.categorie_reglementaire == CATEGORIE_LIBRE,
        )
        .order_by(Produit.nom)
    )
    articles: list[tuple[Produit, Variante | None]] = []
    for produit in produits:
        variantes = [v for v in produit.variantes if v.est_active]
        if variantes:
            articles.extend((produit, v) for v in variantes)
        else:
            articles.append((produit, None))
    return articles


async def reserves(
    session: AsyncSession, produits: set[UUID]
) -> dict[tuple[UUID, UUID | None], int]:
    requete = (
        select(
            LigneCommande.produit_id, LigneCommande.variante_id, func.sum(LigneCommande.quantite)
        )
        .join(Commande, LigneCommande.commande_id == Commande.id)
        .where(Commande.statut.in_(A_PREPARER), LigneCommande.produit_id.in_(produits))
        .group_by(LigneCommande.produit_id, LigneCommande.variante_id)
    )
    reservees: dict[tuple[UUID, UUID | None], int] = defaultdict(int)
    for produit_id, variante_id, quantite in await session.execute(requete):
        if produit_id is not None:
            reservees[(produit_id, variante_id)] = int(quantite)
    return reservees


async def lignes_de_stock(session: AsyncSession) -> list[LigneStock]:
    """Niveau, réservé et disponible de chaque article tenu en stock, avec son alerte."""
    articles = await articles_tenus(session)
    cles = [(p.id, v.id if v else None) for p, v in articles]
    stock = await niveaux_stock(session, cles)
    reserve = await reserves(session, {p.id for p, _ in articles})
    lignes = []
    for (produit, variante), cle in zip(articles, cles, strict=True):
        disponible = stock[cle] - reserve.get(cle, 0)
        lignes.append(
            LigneStock(
                produit_id=produit.id,
                variante_id=cle[1],
                produit_slug=produit.slug,
                libelle=f"{produit.nom} – {variante.libelle}" if variante else produit.nom,
                sku=variante.sku if variante else None,
                niveau=stock[cle],
                reserve=reserve.get(cle, 0),
                disponible=disponible,
                seuil_alerte=produit.seuil_alerte,
                alerte=disponible <= produit.seuil_alerte,
            )
        )
    return lignes
