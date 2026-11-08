"""Catalogue public : rayons, liste de produits avec recherche, fiche produit."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from boutique.models import Produit, Rayon
from boutique.schemas import PageProduits, ProduitDetail, RayonPublic
from boutique.vues import vers_detail, vers_resume
from socle.db import session_db

routeur = APIRouter(prefix="/api/v1", tags=["catalogue"])


def motif_recherche(texte: str) -> str:
    """Motif LIKE « contient », avec % et _ échappés."""
    echappe = texte.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{echappe}%"


def _sans_accents(colonne: Any) -> Any:
    return func.immutable_unaccent(func.lower(colonne))


@routeur.get("/rayons", summary="Rayons de la boutique")
async def rayons(session: AsyncSession = Depends(session_db)) -> list[RayonPublic]:
    nombre = func.count(Produit.id).filter(Produit.est_actif)
    requete = (
        select(Rayon, nombre)
        .outerjoin(Produit, Produit.rayon_id == Rayon.id)
        .where(Rayon.est_actif)
        .group_by(Rayon.id)
        .order_by(Rayon.position, Rayon.nom)
    )
    return [
        RayonPublic(id=r.id, slug=r.slug, nom=r.nom, description=r.description, nombre_produits=n)
        for r, n in (await session.execute(requete)).all()
    ]


@routeur.get("/produits", summary="Produits, par rayon ou par recherche")
async def produits(
    rayon: str | None = Query(default=None, max_length=80),
    q: str | None = Query(default=None, max_length=100, description="Texte recherché"),
    page: int = Query(default=1, ge=1),
    par_page: int = Query(default=24, ge=1, le=60),
    session: AsyncSession = Depends(session_db),
) -> PageProduits:
    filtres: list[Any] = [Produit.est_actif, Rayon.est_actif]
    if rayon:
        filtres.append(Rayon.slug == rayon)
    if q and q.strip():
        motif = func.immutable_unaccent(motif_recherche(q.strip().lower()))
        filtres.append(
            or_(
                _sans_accents(Produit.nom).like(motif, escape="\\"),
                _sans_accents(Produit.resume).like(motif, escape="\\"),
            )
        )
    total = await session.scalar(
        select(func.count()).select_from(Produit).join(Produit.rayon).where(*filtres)
    )
    requete = (
        select(Produit)
        .join(Produit.rayon)
        .options(contains_eager(Produit.rayon), selectinload(Produit.images))
        .where(*filtres)
        .order_by(Rayon.position, Produit.nom)
        .offset((page - 1) * par_page)
        .limit(par_page)
    )
    elements = (await session.execute(requete)).scalars().all()
    return PageProduits(
        elements=[vers_resume(p) for p in elements], total=total or 0, page=page, par_page=par_page
    )


@routeur.get("/produits/{slug}", summary="Fiche produit")
async def produit(slug: str, session: AsyncSession = Depends(session_db)) -> ProduitDetail:
    requete = (
        select(Produit)
        .join(Produit.rayon)
        .options(
            contains_eager(Produit.rayon),
            selectinload(Produit.images),
            selectinload(Produit.variantes),
        )
        .where(Produit.slug == slug, Produit.est_actif, Rayon.est_actif)
    )
    trouve = (await session.execute(requete)).scalar_one_or_none()
    if trouve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit introuvable")
    return vers_detail(trouve)
