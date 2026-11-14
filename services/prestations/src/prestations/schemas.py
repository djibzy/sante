"""Données reçues et renvoyées par l'API. Les vues de l'équipe de terrain ne portent aucun prix."""

from datetime import date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from prestations.etats import (
    Formule,
    ModeTarif,
    StatutCollecte,
    StatutContrat,
    StatutDemande,
    TypePartenaire,
)
from prestations.linge import Article, Service, TypeStructure

Quantite = Annotated[int, Field(ge=0, le=100_000)]
Prix = Annotated[int, Field(ge=0, le=1_000_000)]
Volumes = dict[Article, Quantite]
Tarifs = dict[Article, Prix]
Mois = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-11"])]


# --- Offre publique -------------------------------------------------------------------------


class ArticleOffre(BaseModel):
    code: Article
    libelle: str
    pluriel: str
    famille: str
    libelle_famille: str
    note: str


class Choix(BaseModel):
    code: str
    libelle: str


class Offre(BaseModel):
    services: list[Choix]
    articles: list[ArticleOffre]
    types_structure: list[Choix]


# --- Demandes ---------------------------------------------------------------------------------


class NouvelleDemande(BaseModel):
    service: Service = Service.ENTRETIEN_LINGE
    structure: str = Field(min_length=2, max_length=160)
    type_structure: TypeStructure
    contact: str = Field(min_length=2, max_length=120, description="Nom et fonction")
    telephone: str = Field(min_length=6, max_length=30)
    quartier: str = Field(min_length=2, max_length=160, description="Quartier et ville")
    volumes: Volumes = Field(default_factory=dict, description="Pièces par semaine, estimées")
    collectes_par_semaine: int | None = Field(None, ge=1, le=7)
    message: str = Field("", max_length=1000)


class DemandeRecue(BaseModel):
    reference: str
    message: str


class DemandeVue(BaseModel):
    id: UUID
    reference: str
    service: Service
    statut: StatutDemande
    libelle_statut: str
    structure: str
    type_structure: TypeStructure
    libelle_type: str
    contact: str
    telephone: str
    quartier: str
    volumes: dict[str, int]
    pieces_par_semaine: int
    collectes_par_semaine: int | None
    message: str
    notes_equipe: str
    contrat_reference: str | None
    cree_le: datetime
    modifie_le: datetime


class ModificationDemande(BaseModel):
    statut: StatutDemande | None = None
    notes_equipe: str | None = Field(None, max_length=2000)

    @field_validator("statut")
    @classmethod
    def _pas_signee_a_la_main(cls, statut: StatutDemande | None) -> StatutDemande | None:
        if statut == StatutDemande.SIGNEE:
            raise ValueError("Une demande est signée en créant son contrat")
        return statut


class PageDemandes(BaseModel):
    elements: list[DemandeVue]
    total: int
    nouvelles: int


# --- Partenaires ------------------------------------------------------------------------------


class _ChampsPartenaire(BaseModel):
    nom: str = Field(min_length=2, max_length=120)
    type: TypePartenaire = TypePartenaire.BLANCHISSERIE
    est_interne: bool = False
    contact: str = Field("", max_length=120)
    telephone: str = Field(min_length=6, max_length=30)
    quartier: str = Field("", max_length=160)
    delai_jours: int = Field(2, ge=0, le=14)
    capacite_pieces_jour: int | None = Field(None, ge=1, le=100_000)
    mode_tarif: ModeTarif = ModeTarif.PIECE
    tarifs: Tarifs = Field(default_factory=dict)
    tarif_kg: Prix | None = None
    hygiene_verifiee_le: date | None = None
    notes: str = Field("", max_length=2000)
    est_actif: bool = True


class NouveauPartenaire(_ChampsPartenaire):
    @model_validator(mode="after")
    def _tarif_kg(self) -> Self:
        if self.mode_tarif == ModeTarif.KG and self.tarif_kg is None:
            raise ValueError("Indiquez le prix au kilo de ce partenaire")
        return self


class ModificationPartenaire(BaseModel):
    nom: str | None = Field(None, min_length=2, max_length=120)
    type: TypePartenaire | None = None
    est_interne: bool | None = None
    contact: str | None = Field(None, max_length=120)
    telephone: str | None = Field(None, min_length=6, max_length=30)
    quartier: str | None = Field(None, max_length=160)
    delai_jours: int | None = Field(None, ge=0, le=14)
    capacite_pieces_jour: int | None = Field(None, ge=1, le=100_000)
    mode_tarif: ModeTarif | None = None
    tarifs: Tarifs | None = None
    tarif_kg: Prix | None = None
    hygiene_verifiee_le: date | None = None
    notes: str | None = Field(None, max_length=2000)
    est_actif: bool | None = None


class PartenaireVue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
    type: TypePartenaire
    est_interne: bool
    contact: str
    telephone: str
    quartier: str
    delai_jours: int
    capacite_pieces_jour: int | None
    mode_tarif: ModeTarif
    tarifs: dict[str, int]
    tarif_kg: int | None
    hygiene_verifiee_le: date | None
    notes: str
    est_actif: bool
    cree_le: datetime


class PartenaireResume(BaseModel):
    """Ce que voit l'équipe de terrain : où déposer le linge, qui appeler."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
    type: TypePartenaire
    est_interne: bool
    contact: str
    telephone: str
    quartier: str
    delai_jours: int
    pesee_requise: bool


# --- Contrats ---------------------------------------------------------------------------------


def _jours_tries(jours: list[int]) -> list[int]:
    if any(not 1 <= jour <= 7 for jour in jours):
        raise ValueError("Jours de 1 (lundi) à 7 (dimanche)")
    return sorted(set(jours))


class _ChampsContrat(BaseModel):
    structure: str = Field(min_length=2, max_length=160)
    type_structure: TypeStructure
    contact: str = Field(min_length=2, max_length=120)
    telephone: str = Field(min_length=6, max_length=30)
    adresse: str = Field(min_length=5, max_length=300)
    partenaire_id: UUID | None = None
    jours_collecte: list[int] = Field(default_factory=list, max_length=7)
    delai_retour_jours: int = Field(3, ge=1, le=14)
    formule: Formule = Formule.PIECE
    tarifs: Tarifs = Field(default_factory=dict)
    forfait_mensuel: int | None = Field(None, ge=0, le=100_000_000)
    pieces_incluses: int | None = Field(None, ge=0, le=1_000_000)
    prix_piece_supplementaire: Prix | None = None
    sms_actifs: bool = True
    debut_le: date
    fin_le: date | None = None
    notes: str = Field("", max_length=2000)

    @field_validator("jours_collecte")
    @classmethod
    def _jours(cls, jours: list[int]) -> list[int]:
        return _jours_tries(jours)


class NouveauContrat(_ChampsContrat):
    demande_id: UUID | None = Field(None, description="La demande qui devient ce contrat")

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        verifier_contrat(self.formule, self.forfait_mensuel, self.debut_le, self.fin_le)
        return self


def verifier_contrat(
    formule: Formule | str, forfait: int | None, debut: date, fin: date | None
) -> None:
    if formule == Formule.FORFAIT and forfait is None:
        raise ValueError("Indiquez le montant du forfait mensuel")
    if fin is not None and fin < debut:
        raise ValueError("La fin du contrat précède son début")


class ModificationContrat(BaseModel):
    statut: StatutContrat | None = None
    structure: str | None = Field(None, min_length=2, max_length=160)
    type_structure: TypeStructure | None = None
    contact: str | None = Field(None, min_length=2, max_length=120)
    telephone: str | None = Field(None, min_length=6, max_length=30)
    adresse: str | None = Field(None, min_length=5, max_length=300)
    partenaire_id: UUID | None = None
    jours_collecte: list[int] | None = Field(None, max_length=7)
    delai_retour_jours: int | None = Field(None, ge=1, le=14)
    formule: Formule | None = None
    tarifs: Tarifs | None = None
    forfait_mensuel: int | None = Field(None, ge=0, le=100_000_000)
    pieces_incluses: int | None = Field(None, ge=0, le=1_000_000)
    prix_piece_supplementaire: Prix | None = None
    sms_actifs: bool | None = None
    debut_le: date | None = None
    fin_le: date | None = None
    notes: str | None = Field(None, max_length=2000)

    @field_validator("jours_collecte")
    @classmethod
    def _jours(cls, jours: list[int] | None) -> list[int] | None:
        return None if jours is None else _jours_tries(jours)


class ContratResume(BaseModel):
    """Le contrat vu de la tournée : où aller, qui appeler, quand revenir. Sans les prix."""

    id: UUID
    reference: str
    structure: str
    type_structure: TypeStructure
    contact: str
    telephone: str
    adresse: str
    jours_collecte: list[int]
    libelle_jours: str
    delai_retour_jours: int
    partenaire: PartenaireResume | None


class ContratVue(ContratResume):
    service: Service
    statut: StatutContrat
    formule: Formule
    tarifs: dict[str, int]
    forfait_mensuel: int | None
    pieces_incluses: int | None
    prix_piece_supplementaire: int | None
    sms_actifs: bool
    debut_le: date
    fin_le: date | None
    notes: str
    demande_reference: str | None
    cree_le: datetime


# --- Collectes --------------------------------------------------------------------------------


class LigneComptee(BaseModel):
    article: Article
    precision: str = Field("", max_length=80, description="Pour « autre » : nappes, tabliers…")
    quantite: int = Field(ge=0, le=10_000)

    @field_validator("precision")
    @classmethod
    def _propre(cls, precision: str) -> str:
        return " ".join(precision.split())


def _lignes_distinctes(lignes: list[LigneComptee]) -> list[LigneComptee]:
    vues: set[tuple[Article, str]] = set()
    for ligne in lignes:
        cle = (ligne.article, ligne.precision.lower())
        if cle in vues:
            raise ValueError("Chaque article ne se compte qu'une fois")
        if ligne.article == Article.AUTRE and not ligne.precision:
            raise ValueError("Précisez la pièce comptée en « autre »")
        vues.add(cle)
    return lignes


class Enlevement(BaseModel):
    contrat_id: UUID
    jour: date | None = Field(None, description="Jour de la collecte ; par défaut aujourd'hui")
    lignes: list[LigneComptee] = Field(min_length=1, max_length=30)
    sacs: int | None = Field(None, ge=0, le=500)
    remis_par: str = Field(min_length=2, max_length=120, description="Qui a remis le linge")
    observations: str = Field("", max_length=1000)

    @field_validator("lignes")
    @classmethod
    def _lignes(cls, lignes: list[LigneComptee]) -> list[LigneComptee]:
        if not any(ligne.quantite for ligne in lignes):
            raise ValueError("Aucune pièce comptée : annulez plutôt le passage")
        return _lignes_distinctes(lignes)


class Depot(BaseModel):
    partenaire_id: UUID | None = Field(None, description="Par défaut, celui du contrat")
    poids_kg: float | None = Field(None, gt=0, le=9_999)


class Retour(BaseModel):
    lignes: list[LigneComptee] = Field(min_length=1, max_length=30)
    recu_par: str = Field(min_length=2, max_length=120, description="Qui a reçu le linge")
    observations: str = Field("", max_length=1000)

    @field_validator("lignes")
    @classmethod
    def _lignes(cls, lignes: list[LigneComptee]) -> list[LigneComptee]:
        return _lignes_distinctes(lignes)


class Annulation(BaseModel):
    motif: str = Field(min_length=3, max_length=200)


class AnnulationPassage(Annulation):
    contrat_id: UUID
    jour: date


class CollectePonctuelle(BaseModel):
    contrat_id: UUID
    prevue_le: date
    observations: str = Field("", max_length=1000)


class LigneVue(BaseModel):
    article: Article
    precision: str
    libelle: str
    quantite_enlevee: int
    quantite_rendue: int | None
    ecart: int | None  # rendues moins enlevées : négatif, des pièces manquent


class CollecteVue(BaseModel):
    id: UUID
    reference: str
    statut: StatutCollecte
    libelle_statut: str
    prevue_le: date
    retour_prevu_le: date | None
    en_retard: bool
    enlevee_le: datetime | None
    deposee_le: datetime | None
    prete_le: datetime | None
    rendue_le: datetime | None
    annulee_le: datetime | None
    sacs: int | None
    poids_kg: float | None
    remis_par: str
    recu_par: str
    observations: str
    observations_retour: str
    motif_annulation: str
    contrat: ContratResume
    partenaire: PartenaireResume | None
    lignes: list[LigneVue]
    pieces_enlevees: int
    pieces_rendues: int | None
    pieces_manquantes: int | None


class PageCollectes(BaseModel):
    elements: list[CollecteVue]
    total: int


class Passage(BaseModel):
    """Un arrêt de la tournée : la structure, et ce qui a été fait (rien encore : à enlever)."""

    contrat: ContratResume
    collecte: CollecteVue | None
    au_calendrier: bool  # sinon, collecte ponctuelle demandée par la structure


class Tournee(BaseModel):
    jour: date
    libelle_jour: str
    passages: list[Passage]
    a_deposer: list[CollecteVue]
    a_rendre: list[CollecteVue]


# --- Relevés ----------------------------------------------------------------------------------


class LigneReleve(BaseModel):
    article: Article
    libelle: str
    prix_unitaire: int | None  # vide : forfait, ou prix à fixer dans le contrat
    enlevees: int
    rendues: int
    manquantes: int
    montant: int


class CollecteReleve(BaseModel):
    reference: str
    enlevee_le: date
    rendue_le: date
    pieces_enlevees: int
    pieces_rendues: int


class Releve(BaseModel):
    mois: str
    libelle_mois: str
    contrat: ContratVue
    collectes: list[CollecteReleve]
    lignes: list[LigneReleve]
    pieces_enlevees: int
    pieces_rendues: int
    pieces_manquantes: int
    forfait: int | None
    pieces_supplementaires: int
    montant_supplement: int
    total: int
    prix_manquants: bool  # des articles sans prix au contrat : à fixer avant d'envoyer
    # Pour l'équipe seulement : jamais imprimé sur le relevé envoyé à la structure.
    cout_partenaires: int
    cout_incomplet: bool


class SyntheseContrat(BaseModel):
    reference: str
    structure: str
    formule: Formule
    collectes: int
    pieces_rendues: int
    pieces_manquantes: int
    chiffre: int
    cout: int
    marge: int
    cout_incomplet: bool
    prix_manquants: bool


class SynthesePartenaire(BaseModel):
    id: UUID
    nom: str
    mode_tarif: ModeTarif
    collectes: int
    pieces: int
    poids_kg: float
    cout: int
    cout_incomplet: bool


class Synthese(BaseModel):
    mois: str
    libelle_mois: str
    contrats: list[SyntheseContrat]
    partenaires: list[SynthesePartenaire]
    chiffre: int
    cout: int
    marge: int
    pieces_rendues: int
    pieces_manquantes: int
    en_cours: int  # pièces sorties des structures et pas encore rendues, à ce jour
