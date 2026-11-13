"""Codes de réduction (codes promo) et code appliqué à chaque commande.

Révision : 0013
Précédente : 0012
Créée le : 2026-11-13 09:28:02.912575
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "codes_promo",
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("libelle", sa.String(length=120), nullable=False),
        sa.Column("nature", sa.String(length=12), nullable=False),
        sa.Column("valeur", sa.Integer(), nullable=False),
        sa.Column("minimum", sa.Integer(), server_default="0", nullable=False),
        sa.Column("debut", sa.Date(), nullable=False),
        sa.Column("fin", sa.Date(), nullable=True),
        sa.Column("utilisations_max", sa.Integer(), nullable=True),
        sa.Column(
            "une_fois_par_client", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("est_actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "nature IN ('pourcentage', 'montant')", name=op.f("ck_codes_promo_nature_valide")
        ),
        sa.CheckConstraint(
            "valeur > 0 AND (nature <> 'pourcentage' OR valeur <= 90)",
            name=op.f("ck_codes_promo_valeur_valide"),
        ),
        sa.CheckConstraint("code = upper(code)", name=op.f("ck_codes_promo_code_majuscules")),
        sa.CheckConstraint(
            "fin IS NULL OR fin >= debut", name=op.f("ck_codes_promo_periode_valide")
        ),
        sa.CheckConstraint("minimum >= 0", name=op.f("ck_codes_promo_minimum_positif")),
        sa.CheckConstraint(
            "utilisations_max IS NULL OR utilisations_max > 0",
            name=op.f("ck_codes_promo_utilisations_valides"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_codes_promo")),
        sa.UniqueConstraint("code", name=op.f("uq_codes_promo_code")),
    )
    op.add_column("commandes", sa.Column("code_promo", sa.String(length=30), nullable=True))
    op.create_index(op.f("ix_commandes_code_promo"), "commandes", ["code_promo"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_commandes_code_promo"), table_name="commandes")
    op.drop_column("commandes", "code_promo")
    op.drop_table("codes_promo")
