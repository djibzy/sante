"""Tenues proposées : composées par l'équipe, montrées aux clients comme idées de tenue."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from boutique.schemas import Metier

Place = Literal["haut", "bas", "dessus", "chaussures", "calot"]
ORDRE: tuple[Place, ...] = ("haut", "bas", "dessus", "chaussures", "calot")


class PieceTenue(BaseModel):
    piece: Place
    produit_id: UUID
    couleur: str | None = Field(None, max_length=40)


class NouvelleTenue(BaseModel):
    nom: str = Field(min_length=3, max_length=80)
    description: str = Field("", max_length=300)
    metier: Metier | None = None
    pieces: list[PieceTenue] = Field(min_length=2, max_length=5)

    @field_validator("pieces")
    @classmethod
    def une_piece_par_place(cls, pieces: list[PieceTenue]) -> list[PieceTenue]:
        places = [p.piece for p in pieces]
        if len(set(places)) != len(places):
            raise ValueError("Une seule pièce par place (haut, pantalon…)")
        return sorted(pieces, key=lambda p: ORDRE.index(p.piece))


class ModificationTenue(BaseModel):
    nom: str | None = Field(None, min_length=3, max_length=80)
    description: str | None = Field(None, max_length=300)
    position: int | None = Field(None, ge=0, le=1000)
    est_active: bool | None = None


class PieceProposee(BaseModel):
    piece: Place
    produit_slug: str
    nom: str
    rayon_slug: str
    couleur: str | None
    hex: str | None
    prix: int | None
    personnalisable: bool


class TenueVue(BaseModel):
    id: UUID
    nom: str
    description: str
    metier: Metier | None
    pieces: list[PieceProposee]
    total: int


class TenueGestion(TenueVue):
    position: int
    est_active: bool
    incomplete: bool = Field(description="Une pièce n'est plus en vente (ou plus dans sa couleur)")
