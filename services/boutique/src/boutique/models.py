"""Catalogue : rayons, produits, variantes, images.

Règle réglementaire (décret n° 04-557) : chaque produit porte une catégorie. Les articles du
domaine pharmaceutique ne sont pas vendus en ligne par la boutique ; ils passent par le
pharmacien partenaire.
"""

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, MetaData, String, Text, true
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

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


class JournalAudit(JournalAuditMixin, Base):
    __tablename__ = "journal_audit"
