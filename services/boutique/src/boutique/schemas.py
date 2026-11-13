from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CategorieReglementaire = Literal["libre", "pharmaceutique"]
MOTIF_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"


Metier = Literal[
    "infirmier", "sage-femme", "medecin", "pharmacie", "laboratoire", "dentiste",
    "aide-soignant", "etudiant",
]  # fmt: skip
Genre = Literal["femme", "homme", "mixte"]
Manches = Literal["courtes", "longues"]
Univers = Literal["tenues", "equipement", "campagnes"]
HEX = r"^#[0-9a-f]{6}$"


class RayonPublic(BaseModel):
    id: UUID
    slug: str
    nom: str
    description: str
    univers: Univers
    nombre_produits: int


class MetierPublic(BaseModel):
    slug: Metier
    nom: str
    nombre_produits: int


class ConditionsVente(BaseModel):
    """Règles réglables de la boutique, citées par les conditions de vente."""

    acompte_pourcent: int = Field(description="Acompte des articles faits à la demande ; 0 : aucun")
    validite_devis_jours: int


class Couleur(BaseModel):
    nom: str
    hex: str | None


class Facette(BaseModel):
    valeur: str
    libelle: str
    nombre: int
    hex: str | None = None


class Facettes(BaseModel):
    """Valeurs possibles des filtres pour le rayon ou la recherche en cours, avec leur nombre
    de produits."""

    metiers: list[Facette] = []
    genres: list[Facette] = []
    couleurs: list[Facette] = []
    tailles: list[Facette] = []
    collections: list[Facette] = []


class ImagePublique(BaseModel):
    url: str
    texte_alternatif: str
    couleur: str | None = Field(None, description="Couleur de l'article sur la photo")


class FamilleCouleur(BaseModel):
    code: str
    nom: str
    hex: str
    nombre: int = Field(description="Articles de cette famille, avec les autres filtres")


class Tuile(BaseModel):
    """Un article dans une de ses couleurs : une case du mur de couleurs."""

    produit_slug: str
    nom: str
    rayon_slug: str
    genre: Genre | None
    couleur: str
    hex: str
    famille: str
    prix: int | None
    image: ImagePublique | None = Field(description="Photo de l'article dans cette couleur")
    distance: float | None = Field(None, description="Écart avec la couleur cherchée, 0 à 100")


class Exploration(BaseModel):
    familles: list[FamilleCouleur]
    tuiles: list[Tuile]


class VariantePublique(BaseModel):
    id: UUID
    sku: str
    libelle: str
    taille: str | None
    couleur: str | None
    couleur_hex: str | None
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
    prix_avant_promo: int | None = Field(description="Prix barré pendant une promotion")
    image: ImagePublique | None
    genre: Genre | None
    metiers: list[Metier]
    collection: str | None
    est_nouveau: bool
    couleurs: list[Couleur]
    tailles: list[str]
    delai_jours: int
    fabrique_sur_commande: bool = Field(description="Fabriqué ou brodé à l'atelier")
    note_moyenne: float | None = Field(None, description="Moyenne des avis publiés, sur 5")
    nombre_avis: int = 0


class ProduitDetail(ProduitResume):
    description: str
    manches: Manches | None
    matiere: str
    entretien: str
    variantes: list[VariantePublique]
    images: list[ImagePublique]
    acompte_pourcent: int | None = Field(
        None, description="Acompte non remboursable des articles faits à la demande, en %"
    )
    acompte_toujours: bool = Field(
        False, description="Toujours fait à la demande ; sinon, seulement s'il est personnalisé"
    )


class PageProduits(BaseModel):
    elements: list[ProduitResume]
    total: int
    page: int
    par_page: int
    facettes: Facettes = Facettes()


class CreationRayon(BaseModel):
    slug: str = Field(pattern=MOTIF_SLUG, max_length=80)
    nom: str = Field(min_length=2, max_length=120)
    description: str = ""
    univers: Univers = "tenues"
    position: int = 0


class ModificationRayon(BaseModel):
    nom: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    position: int | None = None
    est_actif: bool | None = None
    univers: Univers | None = None


class CreationVariante(BaseModel):
    sku: str = Field(min_length=2, max_length=60)
    libelle: str = Field(min_length=1, max_length=120)
    taille: str | None = Field(default=None, max_length=20)
    couleur: str | None = Field(default=None, max_length=40)
    couleur_hex: str | None = Field(default=None, pattern=HEX)
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
    metiers: list[Metier] = []
    genre: Genre | None = None
    manches: Manches | None = None
    collection: str | None = Field(default=None, max_length=60)
    matiere: str = Field(default="", max_length=200)
    entretien: str = Field(default="", max_length=300)
    est_nouveau: bool = False
    prix_avant_promo: int | None = Field(default=None, ge=0, description="Prix barré")
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
    metiers: list[Metier] | None = None
    genre: Genre | None = None
    manches: Manches | None = None
    collection: str | None = Field(default=None, max_length=60)
    matiere: str | None = Field(default=None, max_length=200)
    entretien: str | None = Field(default=None, max_length=300)
    est_nouveau: bool | None = None
    prix_avant_promo: int | None = Field(default=None, ge=0)
    est_actif: bool | None = None


class VarianteGestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str
    libelle: str
    taille: str | None
    couleur: str | None
    couleur_hex: str | None
    prix: int | None
    position: int
    est_active: bool


class ProduitGestion(BaseModel):
    """Vue complète pour l'équipe : produits et variantes inactifs compris, prix réels."""

    id: UUID
    slug: str
    nom: str
    resume: str
    description: str
    rayon_slug: str
    rayon_nom: str
    categorie_reglementaire: CategorieReglementaire
    personnalisable: bool
    prix_public: int | None
    prix_pro: int | None
    delai_jours: int
    poste_atelier: str | None
    seuil_alerte: int
    metiers: list[str]
    genre: str | None
    manches: str | None
    collection: str | None
    matiere: str
    entretien: str
    est_nouveau: bool
    prix_avant_promo: int | None
    est_actif: bool
    variantes: list[VarianteGestion]
    images: list[ImagePublique]


class RayonGestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    univers: str
    nom: str
    description: str
    position: int
    est_actif: bool


class ModificationVariante(BaseModel):
    libelle: str | None = Field(default=None, min_length=1, max_length=120)
    taille: str | None = Field(default=None, max_length=20)
    couleur: str | None = Field(default=None, max_length=40)
    couleur_hex: str | None = Field(default=None, pattern=HEX)
    prix: int | None = Field(default=None, ge=0)
    position: int | None = None
    est_active: bool | None = None


class NouvelleImage(BaseModel):
    url: str = Field(max_length=500, pattern=r"^(https://|/)[^\s<>\"']+$")
    texte_alternatif: str = Field(min_length=3, max_length=200)
    couleur: str | None = Field(None, max_length=40, description="Une couleur des variantes")


class ImagesProduit(BaseModel):
    images: list[NouvelleImage] = Field(max_length=8)
