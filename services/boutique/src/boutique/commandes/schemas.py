"""Échanges de l'API des commandes et des devis."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from boutique.commandes.cycle import ModeLivraison, ModePaiement, Moyen, Statut

_CLE = r"^[A-Za-z0-9_-]+$"


class ZonePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    nom: str
    frais: int
    delai_jours: int


class ZoneGestion(ZonePublique):
    position: int
    est_active: bool


class CreationZone(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    nom: str = Field(min_length=2, max_length=120)
    frais: int = Field(ge=0, le=1_000_000)
    delai_jours: int = Field(1, ge=0, le=60)
    position: int = 0


class ModificationZone(BaseModel):
    nom: str | None = Field(None, min_length=2, max_length=120)
    frais: int | None = Field(None, ge=0, le=1_000_000)
    delai_jours: int | None = Field(None, ge=0, le=60)
    position: int | None = None
    est_active: bool | None = None


class LigneDemandee(BaseModel):
    produit_id: UUID
    variante_id: UUID | None = None
    quantite: int = Field(ge=1, le=500)
    personnalisation: str | None = Field(None, max_length=200, description="Texte à broder")


class Livraison(BaseModel):
    mode: ModeLivraison = ModeLivraison.RETRAIT
    zone_id: UUID | None = None
    adresse: str = Field("", max_length=300, description="Quartier, rue, porte, repère")


class DemandeChiffrage(BaseModel):
    lignes: list[LigneDemandee] = Field(min_length=1, max_length=50)
    livraison: Livraison = Livraison()


class LigneChiffree(BaseModel):
    produit_id: UUID
    variante_id: UUID | None
    produit_slug: str | None
    libelle: str
    sku: str | None
    quantite: int
    prix_unitaire: int | None
    montant: int
    personnalisation: str | None
    commandable: bool
    motif: str | None


class Chiffrage(BaseModel):
    lignes: list[LigneChiffree]
    sous_total: int
    frais_livraison: int
    total: int
    date_estimee: date
    commandable: bool


class Coordonnees(BaseModel):
    nom: str = Field(min_length=2, max_length=120)
    telephone: str = Field(min_length=6, max_length=30)


class CreationCommande(BaseModel):
    client: Coordonnees
    livraison: Livraison
    lignes: list[LigneDemandee] = Field(min_length=1, max_length=50)
    note: str = Field("", max_length=500)
    mode_paiement: ModePaiement = ModePaiement.A_LA_LIVRAISON
    cle_suivi: str | None = Field(
        None,
        min_length=22,
        max_length=64,
        pattern=_CLE,
        description="Clé secrète tirée au hasard par l'appareil : sert de lien de suivi et "
        "évite un doublon si la commande est envoyée deux fois.",
    )


class CreationDevis(BaseModel):
    etablissement: str = Field(min_length=2, max_length=160)
    client: Coordonnees
    email: str | None = Field(None, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    livraison: Livraison = Livraison()
    lignes: list[LigneDemandee] = Field(min_length=1, max_length=50)
    note: str = Field("", max_length=1000)
    cle_suivi: str | None = Field(None, min_length=22, max_length=64, pattern=_CLE)


class LigneVue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    produit_id: UUID | None
    variante_id: UUID | None
    libelle: str
    sku: str | None
    quantite: int
    prix_unitaire: int
    montant: int
    personnalisation: str | None


class EvenementVue(BaseModel):
    statut: Statut
    libelle: str
    note: str
    cree_le: datetime


class CommandeClient(BaseModel):
    """Ce que voit le client sur son lien de suivi."""

    reference: str
    statut: Statut
    statut_libelle: str
    est_devis: bool
    cree_le: datetime
    nom_client: str
    telephone: str
    etablissement: str | None
    mode_livraison: ModeLivraison
    zone_nom: str | None
    adresse: str
    mode_paiement: ModePaiement
    lignes: list[LigneVue]
    sous_total: int
    frais_livraison: int
    remise: int
    total: int
    montant_paye: int
    reste_a_payer: int
    date_promise: date | None
    devis_valable_jusqu_au: date | None
    devis_disponible: bool
    facture: str | None
    livreur_nom: str | None
    livreur_telephone: str | None
    peut_annuler: bool
    peut_accepter: bool
    historique: list[EvenementVue]


class CommandeCreee(BaseModel):
    commande: CommandeClient
    cle_suivi: str


class CommandeResume(BaseModel):
    reference: str
    statut: Statut
    statut_libelle: str
    est_devis: bool
    cree_le: datetime
    nom_client: str
    telephone: str
    etablissement: str | None
    mode_livraison: ModeLivraison
    zone_nom: str | None
    total: int
    montant_paye: int
    nombre_articles: int
    date_promise: date | None


class PageCommandes(BaseModel):
    elements: list[CommandeResume]
    total: int
    page: int
    par_page: int


class EvenementGestion(EvenementVue):
    visible_client: bool
    acteur_id: UUID | None


class PaiementVue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    montant: int
    moyen: Moyen
    reference: str | None
    encaisse_par: UUID | None
    encaisse_le: datetime


class CommandeGestion(CommandeClient):
    """Vue complète pour l'équipe : notes internes, paiements, passages possibles."""

    id: UUID
    client_id: UUID | None
    email: str | None
    note_client: str
    devis_emis_le: datetime | None
    paiements: list[PaiementVue]
    historique_complet: list[EvenementGestion]
    passages_possibles: list[Statut]


class ChangementStatut(BaseModel):
    statut: Statut
    note: str = Field("", max_length=500)
    visible_client: bool = True
    date_promise: date | None = None
    livreur_id: UUID | None = Field(None, description="Livreur, au départ en livraison")


class LivreurVue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
    telephone: str
    est_actif: bool


class CreationLivreur(BaseModel):
    nom: str = Field(min_length=2, max_length=120)
    telephone: str = Field(min_length=6, max_length=30)


class ModificationLivreur(BaseModel):
    nom: str | None = Field(None, min_length=2, max_length=120)
    telephone: str | None = Field(None, min_length=6, max_length=30)
    est_actif: bool | None = None


class ArretLivraison(BaseModel):
    """Une commande sur la feuille de route : où aller, qui appeler, combien encaisser."""

    reference: str
    statut: Statut
    client: str
    telephone: str
    zone_nom: str | None
    adresse: str
    reste_a_payer: int
    nombre_articles: int
    date_promise: date | None
    livreur_id: UUID | None
    livreur_nom: str | None


class NouveauPaiement(BaseModel):
    montant: int = Field(ge=1, le=100_000_000)
    moyen: Moyen
    reference: str | None = Field(None, max_length=80)

    @field_validator("moyen")
    @classmethod
    def _pas_en_ligne(cls, moyen: Moyen) -> Moyen:
        if moyen == Moyen.MOBILE_MONEY:
            raise ValueError("Réservé aux paiements faits en ligne par le client")
        return moyen


class LigneDevis(BaseModel):
    """Ligne d'un devis : produit du catalogue, ou ligne libre (forfait de broderie…)."""

    produit_id: UUID | None = None
    variante_id: UUID | None = None
    libelle: str | None = Field(None, min_length=2, max_length=250)
    quantite: int = Field(ge=1, le=10_000)
    prix_unitaire: int | None = Field(None, ge=0, le=100_000_000)
    personnalisation: str | None = Field(None, max_length=200)


class EmissionDevis(BaseModel):
    lignes: list[LigneDevis] = Field(min_length=1, max_length=80)
    remise: int = Field(0, ge=0)
    frais_livraison: int | None = Field(None, ge=0, le=1_000_000)
    validite_jours: int | None = Field(None, ge=1, le=120)
    note: str = Field("", max_length=500)
