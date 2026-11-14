"""Demandes des structures, blanchisseries partenaires, contrats, collectes comptées, SMS.

Aucune donnée de santé : on compte des draps et des blouses, jamais des patients. Montants en
FCFA, en entiers ; téléphones en E.164.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from prestations.etats import (
    Formule,
    ModeTarif,
    StatutCollecte,
    StatutContrat,
    StatutDemande,
    TypePartenaire,
)
from prestations.linge import Article, Service, TypeStructure, valeurs_sql
from socle.audit import JournalAuditMixin
from socle.db import CONVENTION_NOMMAGE, HorodatageMixin, IdMixin


def _maintenant() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENTION_NOMMAGE)


class Partenaire(IdMixin, HorodatageMixin, Base):
    """Blanchisserie ou pressing qui lave pour nous. Notre propre blanchisserie, une fois
    ouverte, sera un partenaire « interne » : collectes et relevés ne changent pas."""

    __tablename__ = "partenaires"
    __table_args__ = (
        CheckConstraint(f"type IN ({valeurs_sql(TypePartenaire)})", name="type_valide"),
        CheckConstraint(f"mode_tarif IN ({valeurs_sql(ModeTarif)})", name="mode_tarif_valide"),
        CheckConstraint("delai_jours BETWEEN 0 AND 14", name="delai_valide"),
        CheckConstraint("tarif_kg IS NULL OR tarif_kg >= 0", name="tarif_kg_positif"),
        CheckConstraint(
            f"mode_tarif <> '{ModeTarif.KG}' OR tarif_kg IS NOT NULL", name="tarif_kg_requis"
        ),
        CheckConstraint(
            "capacite_pieces_jour IS NULL OR capacite_pieces_jour > 0", name="capacite_positive"
        ),
    )

    nom: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    est_interne: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=false())
    contact: Mapped[str] = mapped_column(String(120), nullable=False, default="", server_default="")
    telephone: Mapped[str] = mapped_column(String(20), nullable=False)  # E.164
    quartier: Mapped[str] = mapped_column(
        String(160), nullable=False, default="", server_default=""
    )
    # Délai habituel entre le dépôt du linge et le linge prêt, en jours.
    delai_jours: Mapped[int] = mapped_column(nullable=False, default=2, server_default="2")
    capacite_pieces_jour: Mapped[int | None] = mapped_column()  # indicative
    # Ce que le partenaire nous facture : un prix par article (FCFA par pièce), ou au kilo.
    mode_tarif: Mapped[str] = mapped_column(
        String(10), nullable=False, default=ModeTarif.PIECE, server_default=ModeTarif.PIECE.value
    )
    tarifs: Mapped[dict[str, int]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    tarif_kg: Mapped[int | None] = mapped_column()
    # Visite faite : linge médical lavé à part, à haute température, séchage et stockage propres.
    hygiene_verifiee_le: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    est_actif: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())


class Contrat(IdMixin, HorodatageMixin, Base):
    """Accord avec une structure : quel linge, quels jours, quel partenaire, à quel prix.

    Jours de collecte au format ISO (1 : lundi … 7 : dimanche) ; aucun jour : collectes sur
    appel seulement. Le rythme se négocie structure par structure.
    """

    __tablename__ = "contrats"
    __table_args__ = (
        CheckConstraint(f"service IN ({valeurs_sql(Service)})", name="service_valide"),
        CheckConstraint(
            f"type_structure IN ({valeurs_sql(TypeStructure)})", name="type_structure_valide"
        ),
        CheckConstraint(f"statut IN ({valeurs_sql(StatutContrat)})", name="statut_valide"),
        CheckConstraint(f"formule IN ({valeurs_sql(Formule)})", name="formule_valide"),
        CheckConstraint(
            "jours_collecte <@ ARRAY[1, 2, 3, 4, 5, 6, 7]::smallint[]", name="jours_valides"
        ),
        CheckConstraint("delai_retour_jours BETWEEN 1 AND 14", name="delai_valide"),
        CheckConstraint(
            f"formule <> '{Formule.FORFAIT}' OR forfait_mensuel IS NOT NULL",
            name="forfait_requis",
        ),
        CheckConstraint(
            "coalesce(forfait_mensuel, 0) >= 0 AND coalesce(pieces_incluses, 0) >= 0 "
            "AND coalesce(prix_piece_supplementaire, 0) >= 0",
            name="montants_positifs",
        ),
        CheckConstraint("fin_le IS NULL OR fin_le >= debut_le", name="dates_coherentes"),
    )

    numero: Mapped[int] = mapped_column(Integer, Identity(start=101), unique=True, nullable=False)
    service: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=Service.ENTRETIEN_LINGE,
        server_default=Service.ENTRETIEN_LINGE.value,
    )
    statut: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default=StatutContrat.ACTIF
    )
    structure: Mapped[str] = mapped_column(String(160), nullable=False)
    type_structure: Mapped[str] = mapped_column(String(20), nullable=False)
    contact: Mapped[str] = mapped_column(String(120), nullable=False)
    telephone: Mapped[str] = mapped_column(String(20), nullable=False)  # E.164
    # Lieu de collecte : quartier, rue, repère, à qui s'adresser.
    adresse: Mapped[str] = mapped_column(String(300), nullable=False)
    partenaire_id: Mapped[UUID | None] = mapped_column(ForeignKey("partenaires.id"), index=True)
    jours_collecte: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger), nullable=False, default=list, server_default="{}"
    )
    # Délai promis à la structure entre l'enlèvement et le retour, en jours (dimanche exclu).
    delai_retour_jours: Mapped[int] = mapped_column(nullable=False, default=3, server_default="3")
    formule: Mapped[str] = mapped_column(String(10), nullable=False)
    tarifs: Mapped[dict[str, int]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )  # FCFA par pièce rendue (formule à la pièce)
    forfait_mensuel: Mapped[int | None] = mapped_column()
    pieces_incluses: Mapped[int | None] = mapped_column()  # par mois ; vide : sans limite
    prix_piece_supplementaire: Mapped[int | None] = mapped_column()
    sms_actifs: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())
    debut_le: Mapped[date] = mapped_column(Date, nullable=False)
    fin_le: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    partenaire: Mapped[Partenaire | None] = relationship(lazy="raise")

    @property
    def reference(self) -> str:
        return f"CT-{self.numero}"


class Demande(IdMixin, HorodatageMixin, Base):
    """Demande d'une structure, envoyée depuis la page publique ; l'équipe la rappelle."""

    __tablename__ = "demandes"
    __table_args__ = (
        CheckConstraint(f"service IN ({valeurs_sql(Service)})", name="service_valide"),
        CheckConstraint(
            f"type_structure IN ({valeurs_sql(TypeStructure)})", name="type_structure_valide"
        ),
        CheckConstraint(f"statut IN ({valeurs_sql(StatutDemande)})", name="statut_valide"),
        CheckConstraint(
            "collectes_par_semaine IS NULL OR collectes_par_semaine BETWEEN 1 AND 7",
            name="collectes_valides",
        ),
    )

    numero: Mapped[int] = mapped_column(Integer, Identity(start=101), unique=True, nullable=False)
    service: Mapped[str] = mapped_column(String(30), nullable=False)
    statut: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default=StatutDemande.NOUVELLE
    )
    structure: Mapped[str] = mapped_column(String(160), nullable=False)
    type_structure: Mapped[str] = mapped_column(String(20), nullable=False)
    contact: Mapped[str] = mapped_column(String(120), nullable=False)
    telephone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # E.164
    quartier: Mapped[str] = mapped_column(String(160), nullable=False)
    # Pièces par semaine, estimées par la structure, par article.
    volumes: Mapped[dict[str, int]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    collectes_par_semaine: Mapped[int | None] = mapped_column()
    message: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    notes_equipe: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    contrat_id: Mapped[UUID | None] = mapped_column(ForeignKey("contrats.id"), index=True)

    @property
    def reference(self) -> str:
        return f"DE-{self.numero}"


class Collecte(IdMixin, HorodatageMixin, Base):
    """Un tour du linge : compté à la structure, lavé chez le partenaire, recompté au retour.

    Une collecte n'existe qu'une fois enlevée (ou demandée hors calendrier) : la tournée du jour
    se lit dans le calendrier des contrats, rien n'est planifié d'avance en base.
    """

    __tablename__ = "collectes"
    __table_args__ = (
        CheckConstraint(f"statut IN ({valeurs_sql(StatutCollecte)})", name="statut_valide"),
        CheckConstraint("sacs IS NULL OR sacs >= 0", name="sacs_positifs"),
        CheckConstraint("poids_kg IS NULL OR poids_kg > 0", name="poids_positif"),
        CheckConstraint("cout_kg IS NULL OR cout_kg >= 0", name="cout_kg_positif"),
        # Une seule collecte par contrat et par jour (hors annulées) : deux agents ne comptent
        # pas deux fois le même linge.
        Index(
            "uq_collectes_contrat_jour",
            "contrat_id",
            "prevue_le",
            unique=True,
            postgresql_where=text("statut <> 'annulee'"),
        ),
    )

    numero: Mapped[int] = mapped_column(Integer, Identity(start=1001), unique=True, nullable=False)
    contrat_id: Mapped[UUID] = mapped_column(ForeignKey("contrats.id"), index=True, nullable=False)
    partenaire_id: Mapped[UUID | None] = mapped_column(ForeignKey("partenaires.id"), index=True)
    prevue_le: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    statut: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    enlevee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deposee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prete_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rendue_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    annulee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retour_prevu_le: Mapped[date | None] = mapped_column(Date, index=True)
    sacs: Mapped[int | None] = mapped_column()
    poids_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))  # pesé au dépôt
    cout_kg: Mapped[int | None] = mapped_column()  # tarif au kilo du partenaire, au dépôt
    # Qui a remis le linge à la structure, qui l'a reçu au retour (nom et fonction).
    remis_par: Mapped[str] = mapped_column(
        String(120), nullable=False, default="", server_default=""
    )
    recu_par: Mapped[str] = mapped_column(
        String(120), nullable=False, default="", server_default=""
    )
    # Taches, accrocs, sacs mal fermés… à l'enlèvement puis au retour ; jamais un nom de patient.
    observations: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    observations_retour: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    motif_annulation: Mapped[str] = mapped_column(
        String(200), nullable=False, default="", server_default=""
    )
    enlevee_par: Mapped[UUID | None] = mapped_column(Uuid)  # compte de l'agent
    rendue_par: Mapped[UUID | None] = mapped_column(Uuid)

    contrat: Mapped[Contrat] = relationship(lazy="raise")
    partenaire: Mapped[Partenaire | None] = relationship(lazy="raise")
    lignes: Mapped[list["LigneCollecte"]] = relationship(
        cascade="all, delete-orphan", order_by="LigneCollecte.position", lazy="raise"
    )

    @property
    def reference(self) -> str:
        return f"BC-{self.numero}"


class LigneCollecte(IdMixin, Base):
    """Un article d'une collecte : compté à l'enlèvement, recompté au retour."""

    __tablename__ = "lignes_collecte"
    __table_args__ = (
        CheckConstraint(f"article IN ({valeurs_sql(Article)})", name="article_valide"),
        CheckConstraint(
            "quantite_enlevee >= 0 AND coalesce(quantite_rendue, 0) >= 0",
            name="quantites_positives",
        ),
        CheckConstraint(
            "coalesce(prix_unitaire, 0) >= 0 AND coalesce(cout_unitaire, 0) >= 0",
            name="prix_positifs",
        ),
        UniqueConstraint("collecte_id", "article", "precision"),
    )

    collecte_id: Mapped[UUID] = mapped_column(
        ForeignKey("collectes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    article: Mapped[str] = mapped_column(String(20), nullable=False)
    precision: Mapped[str] = mapped_column(
        String(80), nullable=False, default="", server_default=""
    )
    quantite_enlevee: Mapped[int] = mapped_column(nullable=False)
    quantite_rendue: Mapped[int | None] = mapped_column()
    # Prix facturé à la structure (formule à la pièce), relevé dans le contrat à l'enlèvement ;
    # prix payé au partenaire (tarif à la pièce), relevé à son tarif au dépôt. Vides si le tarif
    # manquait : le relevé prend alors le tarif du moment, ou signale qu'il est à fixer.
    prix_unitaire: Mapped[int | None] = mapped_column()
    cout_unitaire: Mapped[int | None] = mapped_column()


class Notification(IdMixin, Base):
    """SMS à envoyer (boîte d'envoi) ; jamais de donnée de santé dans le texte."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("etat IN ('a_envoyer', 'envoyee', 'echec')", name="etat_valide"),
    )

    objet_type: Mapped[str] = mapped_column(String(20), nullable=False)  # demande, collecte
    objet_id: Mapped[UUID] = mapped_column(Uuid, index=True, nullable=False)
    destinataire: Mapped[str] = mapped_column(String(20), nullable=False)  # E.164
    message: Mapped[str] = mapped_column(Text, nullable=False)
    etat: Mapped[str] = mapped_column(String(10), index=True, nullable=False, default="a_envoyer")
    tentatives: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    derniere_erreur: Mapped[str | None] = mapped_column(String(500))
    identifiant_fournisseur: Mapped[str | None] = mapped_column(String(200))
    prochain_essai: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )
    envoyee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JournalAudit(JournalAuditMixin, Base):
    __tablename__ = "journal_audit"
