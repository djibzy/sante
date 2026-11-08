from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CategorieReglementaire = Literal["libre", "pharmaceutique"]
MOTIF_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class RayonPublic(BaseModel):
    id: UUID
    slug: str
    nom: str
    description: str
    nombre_produits: int


class ImagePublique(BaseModel):
    url: str
    texte_alternatif: str


class VariantePublique(BaseModel):
    id: UUID
    sku: str
    libelle: str
    taille: str | None
    couleur: str | None
    prix: int | None = Field(description="Prix effectif en FCFA ; vide si vendu sur demande")


class ProduitResume(BaseModel):
    id: UUID
    slug: str
    nom: str
    resume: str
    rayon_slug: str
    rayon_nom: str
    categorie_reglementaire: CategorieReglementaire
    vendable_en_ligne: bool
    personnalisable: bool
    prix_public: int | None
    prix_pro: int | None
    image: ImagePublique | None


class ProduitDetail(ProduitResume):
    description: str
    delai_jours: int
    variantes: list[VariantePublique]
    images: list[ImagePublique]


class PageProduits(BaseModel):
    elements: list[ProduitResume]
    total: int
    page: int
    par_page: int


class CreationRayon(BaseModel):
    slug: str = Field(pattern=MOTIF_SLUG, max_length=80)
    nom: str = Field(min_length=2, max_length=120)
    description: str = ""
    position: int = 0


class ModificationRayon(BaseModel):
    nom: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    position: int | None = None
    est_actif: bool | None = None


class CreationVariante(BaseModel):
    sku: str = Field(min_length=2, max_length=60)
    libelle: str = Field(min_length=1, max_length=120)
    taille: str | None = Field(default=None, max_length=20)
    couleur: str | None = Field(default=None, max_length=40)
    prix: int | None = Field(default=None, ge=0)
    position: int = 0


class CreationProduit(BaseModel):
    slug: str = Field(pattern=MOTIF_SLUG, max_length=120)
    nom: str = Field(min_length=2, max_length=200)
    resume: str = Field(default="", max_length=300)
    description: str = ""
    rayon_slug: str
    categorie_reglementaire: CategorieReglementaire = "libre"
    personnalisable: bool = False
    prix_public: int | None = Field(default=None, ge=0)
    prix_pro: int | None = Field(default=None, ge=0)
    delai_jours: int = Field(default=7, ge=0, le=120)
    poste_atelier: str | None = Field(default=None, description="broderie, impression…")
    seuil_alerte: int = Field(default=0, ge=0)
    variantes: list[CreationVariante] = []


class ModificationProduit(BaseModel):
    nom: str | None = Field(default=None, min_length=2, max_length=200)
    resume: str | None = Field(default=None, max_length=300)
    description: str | None = None
    personnalisable: bool | None = None
    prix_public: int | None = Field(default=None, ge=0)
    prix_pro: int | None = Field(default=None, ge=0)
    delai_jours: int | None = Field(default=None, ge=0, le=120)
    poste_atelier: str | None = None
    seuil_alerte: int | None = Field(default=None, ge=0)
    est_actif: bool | None = None
