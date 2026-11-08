from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Langue = Literal["fr", "bm"]
TypeOrganisation = Literal[
    "cscom",
    "csref",
    "hopital",
    "clinique",
    "cabinet",
    "pharmacie",
    "ecole",
    "ong",
    "entreprise",
    "administration",
    "autre",
]
RoleOrganisation = Literal["membre", "acheteur", "valideur", "gestionnaire"]


class Inscription(BaseModel):
    telephone: str = Field(min_length=6, max_length=30, examples=["76 12 34 56"])
    nom: str = Field(min_length=2, max_length=120)
    mot_de_passe: str = Field(min_length=8, max_length=128)
    langue: Langue = "fr"
    accepte_conditions: bool = Field(
        description="Acceptation des conditions d'utilisation et de la politique de données"
    )


class Connexion(BaseModel):
    telephone: str = Field(min_length=6, max_length=30)
    mot_de_passe: str = Field(min_length=1, max_length=128)
    appareil: str | None = Field(default=None, max_length=120)


class DemandeRafraichissement(BaseModel):
    jeton_rafraichissement: str | None = None


class UtilisateurPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telephone: str
    nom: str
    langue: str
    roles: list[str]
    cree_le: datetime


class Jetons(BaseModel):
    jeton_acces: str
    type_jeton: str = "bearer"
    expire_dans: int = Field(description="Durée de validité du jeton d'accès, en secondes")
    jeton_rafraichissement: str | None = Field(
        default=None,
        description="Absent pour les navigateurs : il est alors dans un cookie httpOnly",
    )
    utilisateur: UtilisateurPublic


class CreationOrganisation(BaseModel):
    nom: str = Field(min_length=2, max_length=200)
    type: TypeOrganisation
    telephone: str | None = Field(default=None, max_length=30)
    adresse: str | None = Field(default=None, max_length=300)
    commune: str | None = Field(default=None, max_length=120)


class OrganisationPublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
    type: str
    telephone: str | None
    adresse: str | None
    commune: str | None
    cree_le: datetime


class MonOrganisation(OrganisationPublique):
    mon_role: str


class AjoutMembre(BaseModel):
    telephone: str = Field(min_length=6, max_length=30)
    role: RoleOrganisation = "membre"


class Membre(BaseModel):
    utilisateur_id: UUID
    nom: str
    telephone: str
    role: str
