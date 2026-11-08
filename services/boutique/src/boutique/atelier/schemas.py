"""Échanges de l'API de l'atelier et du stock."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from boutique.atelier.etats import EtatOrdre, MotifStock


class OrdreVue(BaseModel):
    id: UUID
    reference: str
    client: str
    poste: str
    libelle: str
    personnalisation: str | None
    quantite: int
    etat: EtatOrdre
    etat_libelle: str
    date_promise: date | None
    en_retard: bool
    note: str
    commence_le: datetime | None
    termine_le: datetime | None
    passages_possibles: list[EtatOrdre]


class ChangementEtat(BaseModel):
    etat: EtatOrdre
    note: str = Field("", max_length=300)


class PosteVue(BaseModel):
    code: str
    nom: str
    capacite_jour: int
    est_actif: bool
    charge: int  # pièces encore à fabriquer
    jours_de_file: int  # jours pour écouler la file à la capacité du poste


class ModificationPoste(BaseModel):
    nom: str | None = Field(None, min_length=2, max_length=80)
    capacite_jour: int | None = Field(None, ge=1, le=10_000)
    est_actif: bool | None = None


class LigneStock(BaseModel):
    produit_id: UUID
    variante_id: UUID | None
    produit_slug: str
    libelle: str
    sku: str | None
    niveau: int
    reserve: int  # dans des commandes confirmées, pas encore préparées
    disponible: int
    seuil_alerte: int
    alerte: bool


class NouveauMouvement(BaseModel):
    produit_id: UUID
    variante_id: UUID | None = None
    quantite: int = Field(
        ge=1, le=100_000, description="Toujours positive : le motif donne le sens"
    )
    motif: Literal[MotifStock.RECEPTION, MotifStock.PERTE, MotifStock.RETOUR]
    note: str = Field("", max_length=300)


class Inventaire(BaseModel):
    produit_id: UUID
    variante_id: UUID | None = None
    quantite_comptee: int = Field(ge=0, le=1_000_000)
    note: str = Field("", max_length=300)


class MouvementVue(BaseModel):
    id: UUID
    produit_id: UUID
    variante_id: UUID | None
    quantite: int
    motif: MotifStock
    commande: str | None
    note: str
    cree_le: datetime
