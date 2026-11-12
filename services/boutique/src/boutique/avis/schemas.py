from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from boutique.schemas import ImagePublique

StatutAvis = Literal["en_attente", "publie", "refuse"]


class NouvelAvis(BaseModel):
    produit_id: UUID
    note: int = Field(ge=1, le=5)
    texte: str = Field(min_length=10, max_length=1000)


class AvisClient(BaseModel):
    """Ce que le client voit de son propre avis."""

    note: int
    texte: str
    statut: StatutAvis
    motif_refus: str | None
    reponse: str | None


class ProduitAEvaluer(BaseModel):
    produit_id: UUID
    slug: str
    nom: str
    image: ImagePublique | None
    avis: AvisClient | None


class AvisCommande(BaseModel):
    possible: bool
    raison: str | None
    produits: list[ProduitAEvaluer]


class AvisPublic(BaseModel):
    id: UUID
    auteur: str
    note: int
    texte: str
    reponse: str | None
    date: datetime
    achat_verifie: bool = True  # toujours : seuls les clients livrés peuvent écrire


class PageAvis(BaseModel):
    moyenne: float | None
    nombre: int
    repartition: dict[int, int] = Field(description="Nombre d'avis par note, de 5 à 1")
    elements: list[AvisPublic]
    page: int
    par_page: int


class AvisGestion(BaseModel):
    id: UUID
    produit_id: UUID
    produit_nom: str
    produit_slug: str
    commande_reference: str
    auteur: str
    note: int
    texte: str
    statut: StatutAvis
    motif_refus: str | None
    reponse: str | None
    cree_le: datetime
    modere_le: datetime | None


class PageAvisGestion(BaseModel):
    elements: list[AvisGestion]
    total: int
    page: int
    par_page: int


class Moderation(BaseModel):
    decision: Literal["publier", "refuser"]
    motif: str | None = Field(None, max_length=200, description="Montré au client en cas de refus")
    reponse: str | None = Field(None, max_length=1000, description="Réponse publiée avec l'avis")
