"""Dates promises tenant compte de la charge de l'atelier et du stock.

Pour un article fabriqué, le délai est le plus long entre son délai habituel (approvisionnement,
séchage…) et le temps d'écouler la file de son poste à sa capacité journalière, cette commande
comprise. Un article vendu tel quel est prêt le lendemain s'il est en stock, sinon il prend
son délai de réapprovisionnement. Les jours sont des jours calendaires.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.atelier.etats import OUVERTS
from boutique.commandes.tarifs import LigneTarifee, aujourd_hui
from boutique.models import MouvementStock, OrdreFabrication, PosteAtelier

PREPARATION_STOCK = 1  # jours pour préparer un article déjà en stock


@dataclass(frozen=True)
class Article:
    produit_id: UUID
    variante_id: UUID | None
    poste: str | None
    delai_jours: int
    quantite: int


@dataclass(frozen=True)
class EtatAtelier:
    capacites: dict[str, int]
    charges: dict[str, int]
    stock: dict[tuple[UUID, UUID | None], int]


async def niveaux_stock(
    session: AsyncSession, cles: Iterable[tuple[UUID, UUID | None]]
) -> dict[tuple[UUID, UUID | None], int]:
    cles = set(cles)
    if not cles:
        return {}
    produits = {produit for produit, _ in cles}
    requete = (
        select(
            MouvementStock.produit_id, MouvementStock.variante_id, func.sum(MouvementStock.quantite)
        )
        .where(MouvementStock.produit_id.in_(produits))
        .group_by(MouvementStock.produit_id, MouvementStock.variante_id)
    )
    niveaux = {(p, v): int(n) for p, v, n in await session.execute(requete)}
    return {cle: niveaux.get(cle, 0) for cle in cles}


async def charges_par_poste(session: AsyncSession) -> dict[str, int]:
    """Pièces encore à fabriquer, poste par poste."""
    requete = (
        select(OrdreFabrication.poste, func.sum(OrdreFabrication.quantite))
        .where(OrdreFabrication.etat.in_(OUVERTS))
        .group_by(OrdreFabrication.poste)
    )
    return {poste: int(n) for poste, n in await session.execute(requete)}


async def etat_atelier(session: AsyncSession, articles: Sequence[Article]) -> EtatAtelier:
    postes = await session.execute(
        select(PosteAtelier.code, PosteAtelier.capacite_jour).where(PosteAtelier.est_actif)
    )
    return EtatAtelier(
        capacites={code: capacite for code, capacite in postes},
        charges=await charges_par_poste(session),
        stock=await niveaux_stock(
            session, ((a.produit_id, a.variante_id) for a in articles if a.poste is None)
        ),
    )


def jours_de_preparation(articles: Sequence[Article], etat: EtatAtelier) -> int:
    jours = 0
    par_poste: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        if article.poste is None:
            disponible = etat.stock.get((article.produit_id, article.variante_id), 0)
            en_stock = disponible >= article.quantite
            jours = max(jours, PREPARATION_STOCK if en_stock else article.delai_jours)
        elif article.poste in etat.capacites:
            par_poste[article.poste].append(article)
        else:  # poste fermé : délai habituel
            jours = max(jours, article.delai_jours)
    for poste, groupe in par_poste.items():
        file = etat.charges.get(poste, 0) + sum(a.quantite for a in groupe)
        jours = max(jours, *(a.delai_jours for a in groupe), ceil(file / etat.capacites[poste]))
    return jours


def article(ligne: LigneTarifee) -> Article:
    return Article(
        ligne.produit_id, ligne.variante_id, ligne.poste, ligne.delai_jours, ligne.quantite
    )


async def estimer(session: AsyncSession, articles: Sequence[Article], transport: int) -> date:
    etat = await etat_atelier(session, articles)
    return aujourd_hui() + timedelta(days=jours_de_preparation(articles, etat) + transport)
