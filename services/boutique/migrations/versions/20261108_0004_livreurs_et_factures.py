"""Livreurs et factures : livreur d'une commande en livraison, factures numérotées sans trou
par année (compteur verrouillé à chaque émission).

Révision : 0004
Précédente : 0003
Créée le : 2026-11-08 03:42:23.896006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compteurs_factures",
        sa.Column("annee", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("dernier", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("annee", name=op.f("pk_compteurs_factures")),
    )
    op.create_table(
        "livreurs",
        sa.Column("nom", sa.String(length=120), nullable=False),
        sa.Column("telephone", sa.String(length=20), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_livreurs")),
    )
    op.create_table(
        "factures",
        sa.Column("commande_id", sa.Uuid(), nullable=False),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("montant", sa.Integer(), nullable=False),
        sa.Column("emise_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("emise_par", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["commande_id"], ["commandes.id"], name=op.f("fk_factures_commande_id_commandes")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_factures")),
        sa.UniqueConstraint("annee", "numero", name=op.f("uq_factures_annee")),
        sa.UniqueConstraint("commande_id", name=op.f("uq_factures_commande_id")),
    )
    op.add_column("commandes", sa.Column("livreur_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_commandes_livreur_id"), "commandes", ["livreur_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_commandes_livreur_id_livreurs"), "commandes", "livreurs", ["livreur_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_commandes_livreur_id_livreurs"), "commandes", type_="foreignkey")
    op.drop_index(op.f("ix_commandes_livreur_id"), table_name="commandes")
    op.drop_column("commandes", "livreur_id")
    op.drop_table("factures")
    op.drop_table("livreurs")
    op.drop_table("compteurs_factures")
