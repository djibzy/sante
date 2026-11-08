"""Catalogue (rayons, produits, variantes, images), zones de livraison, commandes et devis.

Règle réglementaire (décret n° 04-557) : chaque produit porte une catégorie. Les articles du
domaine pharmaceutique ne sont pas vendus en ligne par la boutique ; ils passent par le
pharmacien partenaire.

Montants en FCFA, en entiers. Une commande ne contient aucune donnée de santé.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    MetaData,
    String,
    Text,
    Uuid,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from boutique.commandes.cycle import ModeLivraison, Moyen, Statut, valeurs_sql
from socle.audit import JournalAuditMixin
from socle.db import CONVENTION_NOMMAGE, HorodatageMixin, IdMixin

CATEGORIE_LIBRE = "libre"
CATEGORIE_PHARMACEUTIQUE = "pharmaceutique"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENTION_NOMMAGE)


class Rayon(IdMixin, HorodatageMixin, Base):
    __tablename__ = "rayons"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    est_actif: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())


class Produit(IdMixin, HorodatageMixin, Base):
    __tablename__ = "produits"
    __table_args__ = (
        CheckConstraint(
            f"categorie_reglementaire IN ('{CATEGORIE_LIBRE}', '{CATEGORIE_PHARMACEUTIQUE}')",
            name="categorie_valide",
        ),
        CheckConstraint(
            f"categorie_reglementaire <> '{CATEGORIE_LIBRE}' OR prix_public IS NOT NULL",
            name="prix_requis",
        ),
        CheckConstraint("prix_public IS NULL OR prix_public >= 0", name="prix_positif"),
    )

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    resume: Mapped[str] = mapped_column(String(300), nullable=False, default="", server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    rayon_id: Mapped[UUID] = mapped_column(ForeignKey("rayons.id"), index=True, nullable=False)
    categorie_reglementaire: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CATEGORIE_LIBRE, server_default=CATEGORIE_LIBRE
    )
    personnalisable: Mapped[bool] = mapped_column(nullable=False, default=False)
    prix_public: Mapped[int | None] = mapped_column()  # en FCFA, hors taxes
    prix_pro: Mapped[int | None] = mapped_column()  # prix professionnel, si différent
    delai_jours: Mapped[int] = mapped_column(nullable=False, default=7, server_default="7")
    est_actif: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())

    rayon: Mapped[Rayon] = relationship(lazy="raise")
    variantes: Mapped[list["Variante"]] = relationship(
        back_populates="produit",
        cascade="all, delete-orphan",
        order_by="Variante.position",
        lazy="raise",
    )
    images: Mapped[list["ImageProduit"]] = relationship(
        cascade="all, delete-orphan", order_by="ImageProduit.position", lazy="raise"
    )

    @property
    def vendable_en_ligne(self) -> bool:
        return self.categorie_reglementaire == CATEGORIE_LIBRE


class Variante(IdMixin, Base):
    __tablename__ = "variantes"

    produit_id: Mapped[UUID] = mapped_column(
        ForeignKey("produits.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    taille: Mapped[str | None] = mapped_column(String(20))
    couleur: Mapped[str | None] = mapped_column(String(40))
    prix: Mapped[int | None] = mapped_column()  # remplace le prix public du produit si renseigné
    stock: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    est_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())

    produit: Mapped[Produit] = relationship(back_populates="variantes", lazy="raise")


class ImageProduit(IdMixin, Base):
    __tablename__ = "images_produits"

    produit_id: Mapped[UUID] = mapped_column(
        ForeignKey("produits.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    texte_alternatif: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")


class ZoneLivraison(IdMixin, HorodatageMixin, Base):
    __tablename__ = "zones_livraison"
    __table_args__ = (
        CheckConstraint("frais >= 0", name="frais_positifs"),
        CheckConstraint("delai_jours >= 0", name="delai_positif"),
    )

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(120), nullable=False)
    frais: Mapped[int] = mapped_column(nullable=False)
    delai_jours: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    est_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())


def _maintenant() -> datetime:
    # Heure de l'application et non de la transaction : deux événements écrits dans la même
    # transaction gardent leur ordre.
    return datetime.now(UTC)


class Commande(IdMixin, HorodatageMixin, Base):
    """Commande d'un client, ou devis demandé par une structure qui devient commande s'il est
    accepté. Le numéro (référence BB-1001) est attribué par la base."""

    __tablename__ = "commandes"
    __table_args__ = (
        CheckConstraint(f"statut IN ({valeurs_sql(Statut)})", name="statut_valide"),
        CheckConstraint(
            f"mode_livraison IN ({valeurs_sql(ModeLivraison)})", name="mode_livraison_valide"
        ),
        CheckConstraint(
            f"mode_livraison = '{ModeLivraison.RETRAIT}' OR zone_id IS NOT NULL",
            name="zone_requise",
        ),
        CheckConstraint(
            "sous_total >= 0 AND frais_livraison >= 0 AND remise >= 0 AND montant_paye >= 0",
            name="montants_positifs",
        ),
        CheckConstraint("total = sous_total + frais_livraison - remise", name="total_coherent"),
        CheckConstraint("total >= 0", name="total_positif"),
    )

    numero: Mapped[int] = mapped_column(Integer, Identity(start=1001), unique=True, nullable=False)
    statut: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    client_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)  # compte unique, si connecté
    nom_client: Mapped[str] = mapped_column(String(120), nullable=False)
    telephone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # E.164
    email: Mapped[str | None] = mapped_column(String(200))
    etablissement: Mapped[str | None] = mapped_column(String(160))
    mode_livraison: Mapped[str] = mapped_column(String(20), nullable=False)
    zone_id: Mapped[UUID | None] = mapped_column(ForeignKey("zones_livraison.id"))
    adresse: Mapped[str] = mapped_column(String(300), nullable=False, default="", server_default="")
    note_client: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    mode_paiement: Mapped[str] = mapped_column(String(30), nullable=False)
    sous_total: Mapped[int] = mapped_column(nullable=False)
    frais_livraison: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    remise: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    total: Mapped[int] = mapped_column(nullable=False)
    montant_paye: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    date_promise: Mapped[date | None] = mapped_column(Date)
    devis_emis_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    devis_valable_jusqu_au: Mapped[date | None] = mapped_column(Date)
    # Empreinte SHA-256 de la clé du lien de suivi ; la clé elle-même n'est jamais stockée.
    empreinte_cle_suivi: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    zone: Mapped[ZoneLivraison | None] = relationship(lazy="raise")
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="LigneCommande.position",
        lazy="raise",
    )
    evenements: Mapped[list["EvenementCommande"]] = relationship(
        cascade="all, delete-orphan", order_by="EvenementCommande.cree_le", lazy="raise"
    )
    paiements: Mapped[list["Paiement"]] = relationship(
        order_by="Paiement.encaisse_le", lazy="raise"
    )

    @property
    def reference(self) -> str:
        return f"BB-{self.numero}"

    @property
    def reste_a_payer(self) -> int:
        return max(self.total - self.montant_paye, 0)


class LigneCommande(IdMixin, Base):
    """Ligne figée au moment de la commande (libellé et prix), ou ligne libre d'un devis
    (forfait de broderie d'un logo, par exemple) sans produit associé."""

    __tablename__ = "lignes_commande"
    __table_args__ = (
        CheckConstraint("quantite > 0", name="quantite_positive"),
        CheckConstraint("prix_unitaire >= 0", name="prix_positif"),
        CheckConstraint("montant = quantite * prix_unitaire", name="montant_coherent"),
    )

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    produit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("produits.id", ondelete="SET NULL"), index=True
    )
    variante_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("variantes.id", ondelete="SET NULL")
    )
    libelle: Mapped[str] = mapped_column(String(250), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(60))
    quantite: Mapped[int] = mapped_column(nullable=False)
    prix_unitaire: Mapped[int] = mapped_column(nullable=False)
    montant: Mapped[int] = mapped_column(nullable=False)
    personnalisation: Mapped[str | None] = mapped_column(String(200))  # texte à broder
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    commande: Mapped[Commande] = relationship(back_populates="lignes", lazy="raise")


class EvenementCommande(IdMixin, Base):
    """Historique daté : chaque changement de statut, avec une note éventuelle."""

    __tablename__ = "evenements_commande"

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    statut: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    visible_client: Mapped[bool] = mapped_column(nullable=False, default=True)
    acteur_id: Mapped[UUID | None] = mapped_column(Uuid)
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )


class Paiement(IdMixin, Base):
    """Encaissement enregistré par l'équipe (paiement à la livraison, acompte d'un devis)."""

    __tablename__ = "paiements"
    __table_args__ = (
        CheckConstraint("montant > 0", name="montant_positif"),
        CheckConstraint(f"moyen IN ({valeurs_sql(Moyen)})", name="moyen_valide"),
    )

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id"), index=True, nullable=False
    )
    montant: Mapped[int] = mapped_column(nullable=False)
    moyen: Mapped[str] = mapped_column(String(20), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(80))  # n° de transaction, de chèque…
    encaisse_par: Mapped[UUID | None] = mapped_column(Uuid)
    encaisse_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )


class JournalAudit(JournalAuditMixin, Base):
    __tablename__ = "journal_audit"
