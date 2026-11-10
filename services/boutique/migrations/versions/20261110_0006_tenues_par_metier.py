"""Tenues par métier : métiers, genre, manches, collection, matière, entretien, nouveauté,
prix barré des promotions, couleur des pastilles ; famille du menu de chaque rayon. Contraintes ajoutées à la main (Alembic ne
les détecte pas sur une table existante).

Révision : 0006
Précédente : 0005
Créée le : 2026-11-10 22:40:04.371999
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "produits",
        sa.Column(
            "metiers", postgresql.ARRAY(sa.String(length=30)), server_default="{}", nullable=False
        ),
    )
    op.add_column("produits", sa.Column("genre", sa.String(length=10), nullable=True))
    op.add_column("produits", sa.Column("manches", sa.String(length=10), nullable=True))
    op.add_column("produits", sa.Column("collection", sa.String(length=60), nullable=True))
    op.add_column(
        "produits", sa.Column("matiere", sa.String(length=200), server_default="", nullable=False)
    )
    op.add_column(
        "produits", sa.Column("entretien", sa.String(length=300), server_default="", nullable=False)
    )
    op.add_column(
        "produits",
        sa.Column("est_nouveau", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("produits", sa.Column("prix_avant_promo", sa.Integer(), nullable=True))
    op.create_index(
        "ix_produits_metiers", "produits", ["metiers"], unique=False, postgresql_using="gin"
    )
    op.add_column("variantes", sa.Column("couleur_hex", sa.String(length=7), nullable=True))
    op.create_check_constraint(
        op.f("ck_produits_promo_coherente"),
        "produits",
        "prix_avant_promo IS NULL OR prix_avant_promo > prix_public",
    )
    op.create_check_constraint(
        op.f("ck_produits_genre_valide"),
        "produits",
        "genre IS NULL OR genre IN ('femme', 'homme', 'mixte')",
    )
    op.create_check_constraint(
        op.f("ck_produits_manches_valides"),
        "produits",
        "manches IS NULL OR manches IN ('courtes', 'longues')",
    )
    op.add_column(
        "rayons",
        sa.Column("univers", sa.String(length=20), server_default="tenues", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_rayons_univers_valide"),
        "rayons",
        "univers IN ('tenues', 'equipement', 'campagnes')",
    )
    op.create_check_constraint(
        op.f("ck_variantes_hex_valide"),
        "variantes",
        "couleur_hex IS NULL OR couleur_hex ~ '^#[0-9a-f]{6}$'",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_variantes_hex_valide"), "variantes", type_="check")
    op.drop_constraint(op.f("ck_rayons_univers_valide"), "rayons", type_="check")
    op.drop_column("rayons", "univers")
    op.drop_constraint(op.f("ck_produits_manches_valides"), "produits", type_="check")
    op.drop_constraint(op.f("ck_produits_genre_valide"), "produits", type_="check")
    op.drop_constraint(op.f("ck_produits_promo_coherente"), "produits", type_="check")
    op.drop_column("variantes", "couleur_hex")
    op.drop_index("ix_produits_metiers", table_name="produits", postgresql_using="gin")
    op.drop_column("produits", "prix_avant_promo")
    op.drop_column("produits", "est_nouveau")
    op.drop_column("produits", "entretien")
    op.drop_column("produits", "matiere")
    op.drop_column("produits", "collection")
    op.drop_column("produits", "manches")
    op.drop_column("produits", "genre")
    op.drop_column("produits", "metiers")
