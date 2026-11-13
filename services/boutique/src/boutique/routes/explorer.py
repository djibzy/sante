"""Découverte visuelle : les tenues en mur de couleurs, par famille de couleur, métier, type
et coupe ; ou les articles les plus proches d'une couleur (celle d'une photo, calculée sur le
téléphone du client : la photo ne quitte jamais l'appareil)."""

from collections import Counter
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from boutique import couleurs
from boutique.models import CATEGORIE_LIBRE, Produit, Rayon
from boutique.schemas import Exploration, FamilleCouleur, Genre, Metier, Tuile
from boutique.vues import vue_image
from socle.db import session_db

routeur = APIRouter(prefix="/api/v1", tags=["catalogue"])
CodeFamille = Literal["blanc", "rose", "rouge", "orange", "vert", "bleu", "violet", "gris"]
HEXA = r"^#[0-9a-fA-F]{6}$"
PROCHE_MAX = 30.0  # au-delà, la couleur n'a plus grand-chose à voir avec celle cherchée


def tuiles_du_produit(produit: Produit) -> list[Tuile]:
    """Une tuile par couleur active ayant une pastille ; la photo de cette couleur, ou la
    première photo si l'article n'existe qu'en une couleur."""
    prix_par_couleur: dict[str, list[int]] = {}
    pastilles: dict[str, str] = {}
    for variante in produit.variantes:
        if variante.est_active and variante.couleur and variante.couleur_hex:
            pastilles.setdefault(variante.couleur, variante.couleur_hex)
            if variante.prix is not None:
                prix_par_couleur.setdefault(variante.couleur, []).append(variante.prix)
    tuiles = []
    for nom, hexa in pastilles.items():
        photo = next((i for i in produit.images if i.couleur == nom), None)
        if photo is None and len(pastilles) == 1 and produit.images:
            photo = produit.images[0]
        prix = min(prix_par_couleur.get(nom, []), default=produit.prix_public)
        tuiles.append(
            Tuile(
                produit_slug=produit.slug,
                nom=produit.nom,
                rayon_slug=produit.rayon.slug,
                genre=produit.genre,
                couleur=nom,
                hex=hexa.lower(),
                famille=couleurs.famille(hexa),
                prix=prix,
                image=vue_image(photo) if photo else None,
            )
        )
    return tuiles


@routeur.get("/explorer", summary="Mur de couleurs des tenues, ou couleurs proches d'une teinte")
async def explorer(
    famille: CodeFamille | None = None,
    metier: Metier | None = None,
    rayon: str | None = Query(None, max_length=80),
    genre: Genre | None = Query(None, description="Femme ou homme : les articles mixtes aussi"),
    proche: str | None = Query(None, pattern=HEXA, description="Couleur cherchée, #rrggbb"),
    familles_seulement: bool = Query(False, description="Le nuancier sans les tuiles (accueil)"),
    session: AsyncSession = Depends(session_db),
) -> Exploration:
    filtres: list[Any] = [
        Produit.est_actif,
        Rayon.est_actif,
        Rayon.univers == "tenues",
        Produit.categorie_reglementaire == CATEGORIE_LIBRE,
    ]
    if metier:
        filtres.append(Produit.metiers.contains([metier]))
    if rayon:
        filtres.append(Rayon.slug == rayon)
    if genre:
        filtres.append(Produit.genre.in_({genre, "mixte"}))
    produits = await session.scalars(
        select(Produit)
        .join(Produit.rayon)
        .where(*filtres)
        .options(
            contains_eager(Produit.rayon),
            selectinload(Produit.variantes),
            selectinload(Produit.images),
        )
    )
    # Rang de chaque tuile : couleur, puis rayon (blouses avant chaussures), puis nom.
    rangees = [
        ((couleurs.rang(tuile.hex), produit.rayon.position, tuile.nom), tuile)
        for produit in produits.unique()
        for tuile in tuiles_du_produit(produit)
    ]
    tuiles = [tuile for _, tuile in sorted(rangees, key=lambda paire: paire[0])]
    nombres = Counter(tuile.famille for tuile in tuiles)
    if familles_seulement:
        tuiles = []
    elif famille:
        tuiles = [tuile for tuile in tuiles if tuile.famille == famille]
    if proche:
        for tuile in tuiles:
            tuile.distance = round(couleurs.distance(proche.lower(), tuile.hex), 1)
        tuiles = [t for t in tuiles if t.distance is not None and t.distance <= PROCHE_MAX]
        tuiles.sort(key=lambda t: t.distance or 0)  # tri stable : à écart égal, l'ordre du mur
    return Exploration(
        familles=[
            FamilleCouleur(code=f.code, nom=f.nom, hex=f.hex, nombre=nombres[f.code])
            for f in couleurs.FAMILLES
        ],
        tuiles=tuiles,
    )
