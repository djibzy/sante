"""Stock des articles vendus tels quels : niveaux, alertes, arrivages, pertes, inventaires."""

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from boutique.atelier.delais import niveaux_stock
from boutique.atelier.etats import MotifStock
from boutique.atelier.schemas import Inventaire, LigneStock, MouvementVue, NouveauMouvement
from boutique.atelier.stock import est_en_stock
from boutique.commandes.cycle import Statut
from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.models import (
    CATEGORIE_LIBRE,
    Commande,
    JournalAudit,
    LigneCommande,
    MouvementStock,
    Produit,
    Variante,
)
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role

routeur = APIRouter(prefix="/api/v1/admin/stock", tags=["stock"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)
_422 = status.HTTP_422_UNPROCESSABLE_CONTENT
A_PREPARER = (Statut.CONFIRMEE, Statut.EN_PREPARATION)


async def _articles(session: AsyncSession) -> list[tuple[Produit, Variante | None]]:
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


async def _reserves(
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
    reserves: dict[tuple[UUID, UUID | None], int] = defaultdict(int)
    for produit_id, variante_id, quantite in await session.execute(requete):
        if produit_id is not None:
            reserves[(produit_id, variante_id)] = int(quantite)
    return reserves


@routeur.get("", summary="Niveaux de stock et alertes")
async def niveaux(
    alerte: bool = Query(False, description="Seulement les articles sous leur seuil"),
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> list[LigneStock]:
    articles = await _articles(session)
    cles = [(p.id, v.id if v else None) for p, v in articles]
    stock = await niveaux_stock(session, cles)
    reserves = await _reserves(session, {p.id for p, _ in articles})
    lignes = []
    for (produit, variante), cle in zip(articles, cles, strict=True):
        disponible = stock[cle] - reserves.get(cle, 0)
        lignes.append(
            LigneStock(
                produit_id=produit.id,
                variante_id=cle[1],
                produit_slug=produit.slug,
                libelle=f"{produit.nom} – {variante.libelle}" if variante else produit.nom,
                sku=variante.sku if variante else None,
                niveau=stock[cle],
                reserve=reserves.get(cle, 0),
                disponible=disponible,
                seuil_alerte=produit.seuil_alerte,
                alerte=disponible <= produit.seuil_alerte,
            )
        )
    return [ligne for ligne in lignes if ligne.alerte] if alerte else lignes


async def _article(session: AsyncSession, produit_id: UUID, variante_id: UUID | None) -> Produit:
    produit = await session.scalar(
        select(Produit).options(selectinload(Produit.variantes)).where(Produit.id == produit_id)
    )
    if produit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit introuvable")
    if not est_en_stock(produit):
        raise HTTPException(_422, "Cet article est fabriqué à l'atelier : il n'est pas en stock")
    variantes = {v.id for v in produit.variantes if v.est_active}
    if (variante_id is None and variantes) or (
        variante_id is not None and variante_id not in variantes
    ):
        raise HTTPException(_422, "Choisissez une variante de ce produit")
    return produit


def _vue(mouvement: MouvementStock, numero: int | None) -> MouvementVue:
    return MouvementVue(
        id=mouvement.id,
        produit_id=mouvement.produit_id,
        variante_id=mouvement.variante_id,
        quantite=mouvement.quantite,
        motif=MotifStock(mouvement.motif),
        commande=f"BB-{numero}" if numero else None,
        note=mouvement.note,
        cree_le=mouvement.cree_le,
    )


async def _enregistrer(
    session: AsyncSession, mouvement: MouvementStock, principal: Principal
) -> MouvementVue:
    session.add(mouvement)
    await session.flush()
    journaliser(
        session,
        JournalAudit,
        action=f"stock.{mouvement.motif}",
        acteur_id=principal.id,
        objet_type="produit",
        objet_id=mouvement.produit_id,
        details={"variante": str(mouvement.variante_id), "quantite": mouvement.quantite},
    )
    await session.commit()
    return _vue(mouvement, None)


@routeur.post(
    "/mouvements", status_code=status.HTTP_201_CREATED, summary="Arrivage, perte ou retour"
)
async def mouvement(
    donnees: NouveauMouvement,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> MouvementVue:
    await _article(session, donnees.produit_id, donnees.variante_id)
    signe = -1 if donnees.motif == MotifStock.PERTE else 1
    return await _enregistrer(
        session,
        MouvementStock(
            produit_id=donnees.produit_id,
            variante_id=donnees.variante_id,
            quantite=signe * donnees.quantite,
            motif=donnees.motif,
            note=donnees.note.strip(),
            acteur_id=principal.id,
        ),
        principal,
    )


@routeur.post("/inventaire", summary="Corriger le stock d'après un comptage")
async def inventaire(
    donnees: Inventaire,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> MouvementVue | None:
    await _article(session, donnees.produit_id, donnees.variante_id)
    cle = (donnees.produit_id, donnees.variante_id)
    ecart = donnees.quantite_comptee - (await niveaux_stock(session, [cle]))[cle]
    if ecart == 0:
        return None
    return await _enregistrer(
        session,
        MouvementStock(
            produit_id=donnees.produit_id,
            variante_id=donnees.variante_id,
            quantite=ecart,
            motif=MotifStock.INVENTAIRE,
            note=donnees.note.strip() or f"Comptage : {donnees.quantite_comptee}",
            acteur_id=principal.id,
        ),
        principal,
    )


@routeur.get("/mouvements", summary="Historique des mouvements d'un article")
async def historique(
    produit_id: UUID,
    variante_id: UUID | None = None,
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> list[MouvementVue]:
    requete = (
        select(MouvementStock, Commande.numero)
        .outerjoin(Commande, MouvementStock.commande_id == Commande.id)
        .where(MouvementStock.produit_id == produit_id)
        .order_by(MouvementStock.cree_le.desc())
        .limit(100)
    )
    if variante_id is not None:
        requete = requete.where(MouvementStock.variante_id == variante_id)
    return [_vue(m, n) for m, n in await session.execute(requete)]
