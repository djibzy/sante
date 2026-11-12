"""Paiement mobile en ligne : transactions auprès de l'agrégateur, et moyen d'encaissement
« mobile_money » quand l'opérateur n'est pas reconnu (contrainte refaite à la main).

Révision : 0007
Précédente : 0006
Créée le : 2026-11-12 22:53:38.962385
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transactions_paiement",
        sa.Column("commande_id", sa.Uuid(), nullable=False),
        sa.Column("fournisseur", sa.String(length=20), nullable=False),
        sa.Column("transaction_id", sa.String(length=60), nullable=False),
        sa.Column("montant", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=10), nullable=False),
        sa.Column("adresse_paiement", sa.String(length=500), nullable=True),
        sa.Column("operateur", sa.String(length=20), nullable=True),
        sa.Column("reference_operateur", sa.String(length=80), nullable=True),
        sa.Column("paiement_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "modifie_le",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "statut IN ('initiee', 'acceptee', 'refusee', 'anomalie')",
            name=op.f("ck_transactions_paiement_statut_valide"),
        ),
        sa.CheckConstraint("montant > 0", name=op.f("ck_transactions_paiement_montant_positif")),
        sa.ForeignKeyConstraint(
            ["commande_id"],
            ["commandes.id"],
            name=op.f("fk_transactions_paiement_commande_id_commandes"),
        ),
        sa.ForeignKeyConstraint(
            ["paiement_id"],
            ["paiements.id"],
            name=op.f("fk_transactions_paiement_paiement_id_paiements"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions_paiement")),
        sa.UniqueConstraint("transaction_id", name=op.f("uq_transactions_paiement_transaction_id")),
    )
    op.create_index(
        op.f("ix_transactions_paiement_commande_id"),
        "transactions_paiement",
        ["commande_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_paiement_statut"), "transactions_paiement", ["statut"], unique=False
    )
    op.drop_constraint(op.f("ck_paiements_moyen_valide"), "paiements", type_="check")
    op.create_check_constraint(
        op.f("ck_paiements_moyen_valide"),
        "paiements",
        "moyen IN ('especes', 'orange_money', 'moov_money', 'mobile_money', 'virement', 'cheque')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_paiements_moyen_valide"), "paiements", type_="check")
    op.create_check_constraint(
        op.f("ck_paiements_moyen_valide"),
        "paiements",
        "moyen IN ('especes', 'orange_money', 'moov_money', 'virement', 'cheque')",
    )
    op.drop_index(op.f("ix_transactions_paiement_statut"), table_name="transactions_paiement")
    op.drop_index(op.f("ix_transactions_paiement_commande_id"), table_name="transactions_paiement")
    op.drop_table("transactions_paiement")
