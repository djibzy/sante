from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from socle.audit import JournalAuditMixin
from socle.db import CONVENTION_NOMMAGE, HorodatageMixin, IdMixin

TYPES_ORGANISATION = (
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
)
ROLES_ORGANISATION = ("membre", "acheteur", "valideur", "gestionnaire")
LANGUES = ("fr", "bm")


def _liste_sql(valeurs: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valeurs)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENTION_NOMMAGE)


class Utilisateur(IdMixin, HorodatageMixin, Base):
    __tablename__ = "utilisateurs"

    telephone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(120), nullable=False)
    langue: Mapped[str] = mapped_column(String(8), nullable=False, default="fr")
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    est_actif: Mapped[bool] = mapped_column(nullable=False, default=True)
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String(60)), nullable=False, default=list, server_default="{}"
    )
    echecs_connexion: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    verrouille_jusqua: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JetonRafraichissement(IdMixin, Base):
    """Jeton de rafraîchissement : seule son empreinte SHA-256 est stockée."""

    __tablename__ = "jetons_rafraichissement"

    utilisateur_id: Mapped[UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    empreinte: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    appareil: Mapped[str | None] = mapped_column(String(120))
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoque_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remplace_par: Mapped[UUID | None] = mapped_column(Uuid)
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Consentement(IdMixin, Base):
    """Consentement daté, par objet et par version du texte accepté."""

    __tablename__ = "consentements"

    utilisateur_id: Mapped[UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    objet: Mapped[str] = mapped_column(String(60), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    accepte_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    retire_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Organisation(IdMixin, HorodatageMixin, Base):
    __tablename__ = "organisations"
    __table_args__ = (
        CheckConstraint(f"type IN ({_liste_sql(TYPES_ORGANISATION)})", name="type_valide"),
    )

    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(20))
    adresse: Mapped[str | None] = mapped_column(String(300))
    commune: Mapped[str | None] = mapped_column(String(120))
    cree_par: Mapped[UUID | None] = mapped_column(Uuid)


class Adhesion(IdMixin, Base):
    __tablename__ = "adhesions"
    __table_args__ = (
        UniqueConstraint("organisation_id", "utilisateur_id", name="uq_adhesions_membre"),
        CheckConstraint(f"role IN ({_liste_sql(ROLES_ORGANISATION)})", name="role_valide"),
    )

    organisation_id: Mapped[UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    utilisateur_id: Mapped[UUID] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class JournalAudit(JournalAuditMixin, Base):
    __tablename__ = "journal_audit"
