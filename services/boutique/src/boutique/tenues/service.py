"""Pièces des tenues proposées : vérifiées à l'enregistrement, résolues à l'affichage."""

from collections.abc import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from boutique.models import CATEGORIE_LIBRE, Produit, Rayon, TenueProposee
from boutique.tenues.schemas import PieceProposee, PieceTenue, TenueGestion, TenueVue


async def produits_en_vente(session: AsyncSession, ids: Iterable[UUID]) -> dict[UUID, Produit]:
    """Tenues en vente en ligne, avec leurs variantes."""
    resultat = await session.scalars(
        select(Produit)
        .join(Produit.rayon)
        .where(
            Produit.id.in_(set(ids)),
            Produit.est_actif,
            Rayon.est_actif,
            Rayon.univers == "tenues",
            Produit.categorie_reglementaire == CATEGORIE_LIBRE,
        )
        .options(contains_eager(Produit.rayon), selectinload(Produit.variantes))
    )
    return {p.id: p for p in resultat.unique()}


def _pastilles(produit: Produit) -> dict[str, str | None]:
    pastilles: dict[str, str | None] = {}
    for variante in produit.variantes:
        if variante.est_active and variante.couleur:
            pastilles.setdefault(variante.couleur, variante.couleur_hex)
    return pastilles


async def verifier(session: AsyncSession, pieces: list[PieceTenue]) -> list[dict[str, str | None]]:
    """Chaque pièce doit être en vente, et dans une de ses couleurs (s'il en a)."""
    produits = await produits_en_vente(session, (p.produit_id for p in pieces))
    enregistrees: list[dict[str, str | None]] = []
    for piece in pieces:
        produit = produits.get(piece.produit_id)
        if produit is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Une pièce n'est pas une tenue en vente"
            )
        pastilles = _pastilles(produit)
        if pastilles and piece.couleur not in pastilles:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"{produit.nom} n'existe pas en « {piece.couleur or 'sans couleur'} »",
            )
        enregistrees.append(
            {
                "piece": piece.piece,
                "produit_id": str(produit.id),
                "couleur": piece.couleur if pastilles else None,
            }
        )
    return enregistrees


async def vues(session: AsyncSession, tenues: list[TenueProposee]) -> list[TenueGestion]:
    """Tenues avec leurs pièces encore disponibles (nom, couleur, prix du moment)."""
    ids = [UUID(str(p["produit_id"])) for t in tenues for p in t.pieces]
    produits = await produits_en_vente(session, ids)
    resultat = []
    for tenue in tenues:
        pieces: list[PieceProposee] = []
        for piece in tenue.pieces:
            produit = produits.get(UUID(str(piece["produit_id"])))
            if produit is None:
                continue
            pastilles = _pastilles(produit)
            couleur = piece.get("couleur")
            if pastilles and couleur not in pastilles:
                continue
            pieces.append(
                PieceProposee.model_validate(
                    {
                        "piece": piece["piece"],
                        "produit_slug": produit.slug,
                        "nom": produit.nom,
                        "rayon_slug": produit.rayon.slug,
                        "couleur": couleur,
                        "hex": pastilles.get(couleur) if couleur else None,
                        "prix": produit.prix_public,
                        "personnalisable": produit.personnalisable,
                    }
                )
            )
        resultat.append(
            TenueGestion(
                id=tenue.id,
                nom=tenue.nom,
                description=tenue.description,
                metier=tenue.metier,
                pieces=pieces,
                total=sum(p.prix or 0 for p in pieces),
                position=tenue.position,
                est_active=tenue.est_active,
                incomplete=len(pieces) < len(tenue.pieces),
            )
        )
    return resultat


def publique(tenue: TenueGestion) -> TenueVue:
    return TenueVue.model_validate(tenue.model_dump())
