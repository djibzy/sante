"""Codes de réduction vus par l'équipe."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

Nature = Literal["pourcentage", "montant"]


class NouveauCode(BaseModel):
    code: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")
    libelle: str = Field(min_length=3, max_length=120, description="Montré au client")
    nature: Nature
    valeur: int = Field(gt=0, le=10_000_000, description="Pourcentage (90 au plus) ou FCFA")
    minimum: int = Field(0, ge=0, description="Montant d'articles minimal, en FCFA")
    debut: date | None = Field(None, description="Aujourd'hui si vide")
    fin: date | None = None
    utilisations_max: int | None = Field(None, gt=0)
    une_fois_par_client: bool = True

    @model_validator(mode="after")
    def coherent(self) -> "NouveauCode":
        if self.nature == "pourcentage" and self.valeur > 90:
            raise ValueError("Un pourcentage de réduction va de 1 à 90")
        if self.debut and self.fin and self.fin < self.debut:
            raise ValueError("La fin doit suivre le début")
        return self


class ModificationCode(BaseModel):
    libelle: str | None = Field(None, min_length=3, max_length=120)
    fin: date | None = None
    utilisations_max: int | None = Field(None, gt=0)
    est_actif: bool | None = None


class CodeVue(BaseModel):
    id: UUID
    code: str
    libelle: str
    nature: Nature
    valeur: int
    minimum: int
    debut: date
    fin: date | None
    utilisations_max: int | None
    une_fois_par_client: bool
    est_actif: bool
    utilisations: int = Field(description="Commandes non annulées qui portent le code")
    remises: int = Field(description="Total des réductions accordées, en FCFA")
