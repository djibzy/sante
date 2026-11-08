"""Atelier et stock : postes et capacités, ordres de fabrication, journal des mouvements.

Trois postes sont créés avec une capacité prudente, à ajuster par l'équipe. La colonne
variantes.stock, jamais utilisée, est remplacée par le journal des mouvements de stock.

Révision : 0003
Précédente : 0002
Créée le : 2026-11-08 03:32:48.216483
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from socle.ids import uuid7

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "postes_atelier",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("nom", sa.String(length=80), nullable=False),
        sa.Column("capacite_jour", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("capacite_jour > 0", name=op.f("ck_postes_atelier_capacite_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_postes_atelier")),
        sa.UniqueConstraint("code", name=op.f("uq_postes_atelier_code")),
    )
    postes = sa.table(
        "postes_atelier",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("nom", sa.String()),
        sa.column("capacite_jour", sa.Integer()),
    )
    op.bulk_insert(
        postes,
        [
            {"id": uuid7(), "code": "broderie", "nom": "Broderie", "capacite_jour": 30},
            {"id": uuid7(), "code": "impression", "nom": "Impression", "capacite_jour": 80},
            {
                "id": uuid7(),
                "code": "assemblage",
                "nom": "Assemblage des kits",
                "capacite_jour": 40,
            },
        ],
    )
    op.create_table(
        "mouvements_stock",
        sa.Column("produit_id", sa.Uuid(), nullable=False),
        sa.Column("variante_id", sa.Uuid(), nullable=True),
        sa.Column("quantite", sa.Integer(), nullable=False),
        sa.Column("motif", sa.String(length=20), nullable=False),
        sa.Column("commande_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=300), server_default="", nullable=False),
        sa.Column("acteur_id", sa.Uuid(), nullable=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "motif IN ('reception', 'vente', 'annulation', 'inventaire', 'perte', 'retour')",
            name=op.f("ck_mouvements_stock_motif_valide"),
        ),
        sa.CheckConstraint("quantite <> 0", name=op.f("ck_mouvements_stock_quantite_non_nulle")),
        sa.ForeignKeyConstraint(
            ["commande_id"],
            ["commandes.id"],
            name=op.f("fk_mouvements_stock_commande_id_commandes"),
        ),
        sa.ForeignKeyConstraint(
            ["produit_id"], ["produits.id"], name=op.f("fk_mouvements_stock_produit_id_produits")
        ),
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variantes.id"],
            name=op.f("fk_mouvements_stock_variante_id_variantes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mouvements_stock")),
    )
    op.create_index(
        op.f("ix_mouvements_stock_commande_id"), "mouvements_stock", ["commande_id"], unique=False
    )
    op.create_index(
        op.f("ix_mouvements_stock_produit_id"), "mouvements_stock", ["produit_id"], unique=False
    )
    op.create_index(
        op.f("ix_mouvements_stock_variante_id"), "mouvements_stock", ["variante_id"], unique=False
    )
    op.create_table(
        "ordres_fabrication",
        sa.Column("commande_id", sa.Uuid(), nullable=False),
        sa.Column("ligne_id", sa.Uuid(), nullable=False),
        sa.Column("poste", sa.String(length=20), nullable=False),
        sa.Column("libelle", sa.String(length=250), nullable=False),
        sa.Column("personnalisation", sa.String(length=200), nullable=True),
        sa.Column("quantite", sa.Integer(), nullable=False),
        sa.Column("etat", sa.String(length=20), nullable=False),
        sa.Column("date_promise", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("commence_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("termine_le", sa.DateTime(timezone=True), nullable=True),
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
            "etat IN ('a_faire', 'en_cours', 'controle', 'termine', 'annule')",
            name=op.f("ck_ordres_fabrication_etat_valide"),
        ),
        sa.CheckConstraint("quantite > 0", name=op.f("ck_ordres_fabrication_quantite_positive")),
        sa.ForeignKeyConstraint(
            ["commande_id"],
            ["commandes.id"],
            name=op.f("fk_ordres_fabrication_commande_id_commandes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ligne_id"],
            ["lignes_commande.id"],
            name=op.f("fk_ordres_fabrication_ligne_id_lignes_commande"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["poste"],
            ["postes_atelier.code"],
            name=op.f("fk_ordres_fabrication_poste_postes_atelier"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ordres_fabrication")),
        sa.UniqueConstraint("ligne_id", name=op.f("uq_ordres_fabrication_ligne_id")),
    )
    op.create_index(
        op.f("ix_ordres_fabrication_commande_id"),
        "ordres_fabrication",
        ["commande_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ordres_fabrication_etat"), "ordres_fabrication", ["etat"], unique=False
    )
    op.add_column("produits", sa.Column("poste_atelier", sa.String(length=20), nullable=True))
    op.add_column(
        "produits", sa.Column("seuil_alerte", sa.Integer(), server_default="0", nullable=False)
    )
    op.create_foreign_key(
        op.f("fk_produits_poste_atelier_postes_atelier"),
        "produits",
        "postes_atelier",
        ["poste_atelier"],
        ["code"],
    )
    op.drop_column("variantes", "stock")


def downgrade() -> None:
    op.add_column(
        "variantes",
        sa.Column(
            "stock", sa.INTEGER(), server_default=sa.text("0"), autoincrement=False, nullable=False
        ),
    )
    op.drop_constraint(
        op.f("fk_produits_poste_atelier_postes_atelier"), "produits", type_="foreignkey"
    )
    op.drop_column("produits", "seuil_alerte")
    op.drop_column("produits", "poste_atelier")
    op.drop_index(op.f("ix_ordres_fabrication_etat"), table_name="ordres_fabrication")
    op.drop_index(op.f("ix_ordres_fabrication_commande_id"), table_name="ordres_fabrication")
    op.drop_table("ordres_fabrication")
    op.drop_index(op.f("ix_mouvements_stock_variante_id"), table_name="mouvements_stock")
    op.drop_index(op.f("ix_mouvements_stock_produit_id"), table_name="mouvements_stock")
    op.drop_index(op.f("ix_mouvements_stock_commande_id"), table_name="mouvements_stock")
    op.drop_table("mouvements_stock")
    op.drop_table("postes_atelier")
