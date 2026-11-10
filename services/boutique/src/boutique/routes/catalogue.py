"""Catalogue public : rayons, métiers, liste de produits filtrable, fiche produit.

Les filtres sont ceux d'une boutique de tenues médicales : métier, genre, couleur, taille,
collection, nouveautés, promotions. Les facettes donnent, pour le rayon ou la recherche en
cours, les valeurs possibles et leur nombre de produits.
"""

from collections import Counter
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from boutique.catalogue_pdf import catalogue_pdf
from boutique.metiers import GENRES, METIERS
from boutique.models import Produit, Rayon, Variante
from boutique.schemas import (
    Facette,
    Facettes,
    Genre,
    Metier,
    MetierPublic,
    PageProduits,
    ProduitDetail,
    RayonPublic,
    Univers,
)
from boutique.vues import rang_taille, vers_detail, vers_resume
from socle.db import session_db
from socle.limites import LimiteDebit

routeur = APIRouter(prefix="/api/v1", tags=["catalogue"])
Tri = Literal["pertinence", "prix_croissant", "prix_decroissant", "nouveautes", "nom"]


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
        RayonPublic(
            id=r.id,
            slug=r.slug,
            nom=r.nom,
            description=r.description,
            univers=r.univers,
            nombre_produits=n,
        )
        for r, n in (await session.execute(requete)).all()
    ]


@routeur.get("/metiers", summary="Métiers de la santé, avec leur nombre de produits")
async def metiers(session: AsyncSession = Depends(session_db)) -> list[MetierPublic]:
    listes = await session.scalars(
        select(Produit.metiers).join(Produit.rayon).where(Produit.est_actif, Rayon.est_actif)
    )
    compte = Counter(metier for liste in listes for metier in liste)
    return [
        MetierPublic(slug=slug, nom=nom, nombre_produits=compte[slug])
        for slug, nom in METIERS.items()
    ]


def _filtres_de_base(rayon: str | None, q: str | None, univers: str | None = None) -> list[Any]:
    filtres: list[Any] = [Produit.est_actif, Rayon.est_actif]
    if rayon:
        filtres.append(Rayon.slug == rayon)
    if univers:
        filtres.append(Rayon.univers == univers)
    if q and q.strip():
        motif = func.immutable_unaccent(motif_recherche(q.strip().lower()))
        filtres.append(
            or_(
                _sans_accents(Produit.nom).like(motif, escape="\\"),
                _sans_accents(Produit.resume).like(motif, escape="\\"),
            )
        )
    return filtres


def _dans(ordre: dict[str, str], compte: Counter[str]) -> list[tuple[str, int]]:
    """Valeurs présentes, dans l'ordre du référentiel."""
    return [(cle, compte[cle]) for cle in ordre if compte[cle]]


async def _facettes(session: AsyncSession, filtres: list[Any]) -> Facettes:
    produits = (
        await session.execute(
            select(Produit.id, Produit.metiers, Produit.genre, Produit.collection)
            .join(Produit.rayon)
            .where(*filtres)
        )
    ).all()
    ids = [p.id for p in produits]
    variantes = (
        await session.execute(
            select(
                Variante.produit_id, Variante.couleur, Variante.couleur_hex, Variante.taille
            ).where(Variante.produit_id.in_(ids), Variante.est_active)
        )
    ).all()
    metiers = Counter(m for p in produits for m in p.metiers)
    genres = Counter(p.genre for p in produits if p.genre)
    collections = Counter(p.collection for p in produits if p.collection)
    couleurs = Counter({(v.produit_id, v.couleur) for v in variantes if v.couleur})
    teintes = {v.couleur: v.couleur_hex for v in variantes if v.couleur}
    par_couleur = Counter(couleur for _, couleur in couleurs)
    tailles = Counter(t for _, t in {(v.produit_id, v.taille) for v in variantes if v.taille})
    return Facettes(
        metiers=[
            Facette(valeur=m, libelle=METIERS[m], nombre=n) for m, n in _dans(METIERS, metiers)
        ],
        genres=[Facette(valeur=g, libelle=GENRES[g], nombre=n) for g, n in _dans(GENRES, genres)],
        couleurs=[
            Facette(valeur=c, libelle=c, nombre=n, hex=teintes[c])
            for c, n in sorted(par_couleur.items(), key=lambda e: (-e[1], e[0]))
        ],
        tailles=[
            Facette(valeur=t, libelle=t, nombre=tailles[t])
            for t in sorted(tailles, key=rang_taille)
        ],
        collections=[
            Facette(valeur=c, libelle=c, nombre=n) for c, n in sorted(collections.items())
        ],
    )


@routeur.get("/produits", summary="Produits, par rayon, par recherche et par filtres")
async def produits(
    rayon: str | None = Query(default=None, max_length=80),
    univers: Univers | None = None,
    q: str | None = Query(default=None, max_length=100, description="Texte recherché"),
    metier: Metier | None = None,
    genre: Genre | None = None,
    couleur: str | None = Query(default=None, max_length=40),
    taille: str | None = Query(default=None, max_length=20),
    collection: str | None = Query(default=None, max_length=60),
    nouveau: bool = False,
    promo: bool = False,
    slug: list[str] | None = Query(default=None, max_length=50, description="Favoris"),
    tri: Tri = "pertinence",
    page: int = Query(default=1, ge=1),
    par_page: int = Query(default=24, ge=1, le=60),
    session: AsyncSession = Depends(session_db),
) -> PageProduits:
    base = _filtres_de_base(rayon, q, univers)
    filtres = list(base)
    if metier:
        filtres.append(Produit.metiers.contains([metier]))
    if genre:
        filtres.append(Produit.genre == genre)
    if collection:
        filtres.append(Produit.collection == collection)
    if nouveau:
        filtres.append(Produit.est_nouveau)
    if slug:
        filtres.append(Produit.slug.in_(slug))
    if promo:
        filtres.append(Produit.prix_avant_promo.is_not(None))
    for colonne, valeur in ((Variante.couleur, couleur), (Variante.taille, taille)):
        if valeur:
            filtres.append(Produit.variantes.any(and_(colonne == valeur, Variante.est_active)))
    ordre = {
        "pertinence": (Rayon.position, Produit.nom),
        "prix_croissant": (Produit.prix_public.asc().nulls_last(), Produit.nom),
        "prix_decroissant": (Produit.prix_public.desc().nulls_last(), Produit.nom),
        "nouveautes": (Produit.est_nouveau.desc(), Produit.cree_le.desc()),
        "nom": (Produit.nom,),
    }[tri]
    total = await session.scalar(
        select(func.count()).select_from(Produit).join(Produit.rayon).where(*filtres)
    )
    requete = (
        select(Produit)
        .join(Produit.rayon)
        .options(
            contains_eager(Produit.rayon),
            selectinload(Produit.images),
            selectinload(Produit.variantes),
        )
        .where(*filtres)
        .order_by(*ordre)
        .offset((page - 1) * par_page)
        .limit(par_page)
    )
    elements = (await session.execute(requete)).scalars().all()
    return PageProduits(
        elements=[vers_resume(p) for p in elements],
        total=total or 0,
        page=page,
        par_page=par_page,
        facettes=await _facettes(session, base),
    )


@routeur.get(
    "/catalogue.pdf",
    summary="Catalogue imprimable (PDF)",
    dependencies=[Depends(LimiteDebit("catalogue", nombre=30, secondes=60))],
)
async def catalogue_imprimable(session: AsyncSession = Depends(session_db)) -> Response:
    return Response(
        await catalogue_pdf(session),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="catalogue-bibou.pdf"',
            "Cache-Control": "public, max-age=600",
        },
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
