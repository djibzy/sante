"""Remboursements : l'argent rendu au client, sortie de caisse pour la comptabilité.

Révision : 0015
Précédente : 0014
Créée le : 2026-11-13 17:20:41.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "remboursements",
        sa.Column("commande_id", sa.Uuid(), nullable=False),
        sa.Column("montant", sa.Integer(), nullable=False),
        sa.Column("moyen", sa.String(length=20), nullable=False),
        sa.Column("reference", sa.String(length=80), nullable=True),
        sa.Column("motif", sa.String(length=200), server_default="", nullable=False),
        sa.Column("rembourse_par", sa.Uuid(), nullable=True),
        sa.Column("rembourse_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "moyen IN ('especes', 'orange_money', 'moov_money', 'mobile_money', 'virement', "
            "'cheque')",
            name=op.f("ck_remboursements_moyen_valide"),
        ),
        sa.CheckConstraint("montant > 0", name=op.f("ck_remboursements_montant_positif")),
        sa.ForeignKeyConstraint(
            ["commande_id"], ["commandes.id"], name=op.f("fk_remboursements_commande_id_commandes")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_remboursements")),
    )
    op.create_index(
        op.f("ix_remboursements_commande_id"), "remboursements", ["commande_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_remboursements_commande_id"), table_name="remboursements")
    op.drop_table("remboursements")
