"""Notifications : boîte d'envoi des SMS aux clients, lue par le processus d'envoi.

Révision : 0005
Précédente : 0004
Créée le : 2026-11-08 03:45:47.410423
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("commande_id", sa.Uuid(), nullable=True),
        sa.Column("canal", sa.String(length=10), nullable=False),
        sa.Column("destinataire", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("etat", sa.String(length=10), nullable=False),
        sa.Column("tentatives", sa.Integer(), server_default="0", nullable=False),
        sa.Column("derniere_erreur", sa.String(length=500), nullable=True),
        sa.Column("identifiant_fournisseur", sa.String(length=200), nullable=True),
        sa.Column("prochain_essai", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("envoyee_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("canal IN ('sms')", name=op.f("ck_notifications_canal_valide")),
        sa.CheckConstraint(
            "etat IN ('a_envoyer', 'envoyee', 'echec')", name=op.f("ck_notifications_etat_valide")
        ),
        sa.ForeignKeyConstraint(
            ["commande_id"], ["commandes.id"], name=op.f("fk_notifications_commande_id_commandes")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(
        op.f("ix_notifications_commande_id"), "notifications", ["commande_id"], unique=False
    )
    op.create_index(op.f("ix_notifications_etat"), "notifications", ["etat"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_etat"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_commande_id"), table_name="notifications")
    op.drop_table("notifications")
