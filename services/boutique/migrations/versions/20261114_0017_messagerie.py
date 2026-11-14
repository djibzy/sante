"""Messagerie : le fil d'une commande ou d'un devis (messages du client et de l'équipe,
propositions à accepter ou refuser, retrait motivé), avec l'index des messages à lire.

Révision : 0017
Précédente : 0016
Créée le : 2026-11-14 18:57:29.432746
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("commande_id", sa.Uuid(), nullable=False),
        sa.Column("auteur", sa.String(length=10), nullable=False),
        sa.Column("auteur_id", sa.Uuid(), nullable=True),
        sa.Column("nom_auteur", sa.String(length=120), server_default="", nullable=False),
        sa.Column("texte", sa.Text(), nullable=False),
        sa.Column("image", sa.String(length=60), nullable=True),
        sa.Column("etat", sa.String(length=12), nullable=True),
        sa.Column("repondue_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lu_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notifie", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("retire_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retire_par", sa.Uuid(), nullable=True),
        sa.Column("motif_retrait", sa.String(length=200), server_default="", nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "auteur IN ('client', 'equipe')", name=op.f("ck_messages_auteur_valide")
        ),
        sa.CheckConstraint(
            "etat IS NULL OR auteur = 'equipe'", name=op.f("ck_messages_proposition_de_l_equipe")
        ),
        sa.CheckConstraint(
            "etat IS NULL OR etat IN ('en_attente', 'acceptee', 'refusee', 'annulee')",
            name=op.f("ck_messages_etat_valide"),
        ),
        sa.ForeignKeyConstraint(
            ["commande_id"],
            ["commandes.id"],
            name=op.f("fk_messages_commande_id_commandes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    # Messages de clients pas encore lus par l'équipe (file de la gestion, alertes).
    op.create_index(
        "ix_messages_a_lire",
        "messages",
        ["commande_id"],
        unique=False,
        postgresql_where=sa.text("auteur = 'client' AND lu_le IS NULL AND retire_le IS NULL"),
    )
    op.create_index("ix_messages_fil", "messages", ["commande_id", "cree_le"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_fil", table_name="messages")
    op.drop_index(
        "ix_messages_a_lire",
        table_name="messages",
        postgresql_where=sa.text("auteur = 'client' AND lu_le IS NULL AND retire_le IS NULL"),
    )
    op.drop_table("messages")
