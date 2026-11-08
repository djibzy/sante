"""Commandes et devis : zones de livraison, commandes, lignes, historique, paiements.

Le numéro de commande (BB-1001…) est une colonne IDENTITY attribuée par PostgreSQL.

Révision : 0002
Précédente : 0001
Créée le : 2026-11-08 03:10:06.498749
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "zones_livraison",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("nom", sa.String(length=120), nullable=False),
        sa.Column("frais", sa.Integer(), nullable=False),
        sa.Column("delai_jours", sa.Integer(), server_default="1", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("est_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("delai_jours >= 0", name=op.f("ck_zones_livraison_delai_positif")),
        sa.CheckConstraint("frais >= 0", name=op.f("ck_zones_livraison_frais_positifs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zones_livraison")),
        sa.UniqueConstraint("slug", name=op.f("uq_zones_livraison_slug")),
    )
    op.create_table(
        "commandes",
        sa.Column("numero", sa.Integer(), sa.Identity(always=False, start=1001), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("nom_client", sa.String(length=120), nullable=False),
        sa.Column("telephone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("etablissement", sa.String(length=160), nullable=True),
        sa.Column("mode_livraison", sa.String(length=20), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=True),
        sa.Column("adresse", sa.String(length=300), server_default="", nullable=False),
        sa.Column("note_client", sa.Text(), server_default="", nullable=False),
        sa.Column("mode_paiement", sa.String(length=30), nullable=False),
        sa.Column("sous_total", sa.Integer(), nullable=False),
        sa.Column("frais_livraison", sa.Integer(), server_default="0", nullable=False),
        sa.Column("remise", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("montant_paye", sa.Integer(), server_default="0", nullable=False),
        sa.Column("date_promise", sa.Date(), nullable=True),
        sa.Column("devis_emis_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("devis_valable_jusqu_au", sa.Date(), nullable=True),
        sa.Column("empreinte_cle_suivi", sa.String(length=64), nullable=False),
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
            "mode_livraison = 'retrait' OR zone_id IS NOT NULL",
            name=op.f("ck_commandes_zone_requise"),
        ),
        sa.CheckConstraint(
            "mode_livraison IN ('retrait', 'livraison')",
            name=op.f("ck_commandes_mode_livraison_valide"),
        ),
        sa.CheckConstraint(
            "statut IN ('devis_demande', 'devis_envoye', 'devis_refuse', 'en_attente', 'confirmee', 'en_preparation', 'prete', 'en_livraison', 'livree', 'annulee')",
            name=op.f("ck_commandes_statut_valide"),
        ),
        sa.CheckConstraint(
            "sous_total >= 0 AND frais_livraison >= 0 AND remise >= 0 AND montant_paye >= 0",
            name=op.f("ck_commandes_montants_positifs"),
        ),
        sa.CheckConstraint(
            "total = sous_total + frais_livraison - remise",
            name=op.f("ck_commandes_total_coherent"),
        ),
        sa.CheckConstraint("total >= 0", name=op.f("ck_commandes_total_positif")),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["zones_livraison.id"], name=op.f("fk_commandes_zone_id_zones_livraison")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commandes")),
        sa.UniqueConstraint("empreinte_cle_suivi", name=op.f("uq_commandes_empreinte_cle_suivi")),
        sa.UniqueConstraint("numero", name=op.f("uq_commandes_numero")),
    )
    op.create_index(op.f("ix_commandes_client_id"), "commandes", ["client_id"], unique=False)
    op.create_index(op.f("ix_commandes_statut"), "commandes", ["statut"], unique=False)
    op.create_index(op.f("ix_commandes_telephone"), "commandes", ["telephone"], unique=False)
    op.create_table(
        "evenements_commande",
        sa.Column("commande_id", sa.Uuid(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("visible_client", sa.Boolean(), nullable=False),
        sa.Column("acteur_id", sa.Uuid(), nullable=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["commande_id"],
            ["commandes.id"],
            name=op.f("fk_evenements_commande_commande_id_commandes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evenements_commande")),
    )
    op.create_index(
        op.f("ix_evenements_commande_commande_id"),
        "evenements_commande",
        ["commande_id"],
        unique=False,
    )
    op.create_table(
        "paiements",
        sa.Column("commande_id", sa.Uuid(), nullable=False),
        sa.Column("montant", sa.Integer(), nullable=False),
        sa.Column("moyen", sa.String(length=20), nullable=False),
        sa.Column("reference", sa.String(length=80), nullable=True),
        sa.Column("encaisse_par", sa.Uuid(), nullable=True),
        sa.Column("encaisse_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "moyen IN ('especes', 'orange_money', 'moov_money', 'virement', 'cheque')",
            name=op.f("ck_paiements_moyen_valide"),
        ),
        sa.CheckConstraint("montant > 0", name=op.f("ck_paiements_montant_positif")),
        sa.ForeignKeyConstraint(
            ["commande_id"], ["commandes.id"], name=op.f("fk_paiements_commande_id_commandes")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paiements")),
    )
    op.create_index(op.f("ix_paiements_commande_id"), "paiements", ["commande_id"], unique=False)
    op.create_table(
        "lignes_commande",
        sa.Column("commande_id", sa.Uuid(), nullable=False),
        sa.Column("produit_id", sa.Uuid(), nullable=True),
        sa.Column("variante_id", sa.Uuid(), nullable=True),
        sa.Column("libelle", sa.String(length=250), nullable=False),
        sa.Column("sku", sa.String(length=60), nullable=True),
        sa.Column("quantite", sa.Integer(), nullable=False),
        sa.Column("prix_unitaire", sa.Integer(), nullable=False),
        sa.Column("montant", sa.Integer(), nullable=False),
        sa.Column("personnalisation", sa.String(length=200), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "montant = quantite * prix_unitaire", name=op.f("ck_lignes_commande_montant_coherent")
        ),
        sa.CheckConstraint("prix_unitaire >= 0", name=op.f("ck_lignes_commande_prix_positif")),
        sa.CheckConstraint("quantite > 0", name=op.f("ck_lignes_commande_quantite_positive")),
        sa.ForeignKeyConstraint(
            ["commande_id"],
            ["commandes.id"],
            name=op.f("fk_lignes_commande_commande_id_commandes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["produit_id"],
            ["produits.id"],
            name=op.f("fk_lignes_commande_produit_id_produits"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variantes.id"],
            name=op.f("fk_lignes_commande_variante_id_variantes"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lignes_commande")),
    )
    op.create_index(
        op.f("ix_lignes_commande_commande_id"), "lignes_commande", ["commande_id"], unique=False
    )
    op.create_index(
        op.f("ix_lignes_commande_produit_id"), "lignes_commande", ["produit_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lignes_commande_produit_id"), table_name="lignes_commande")
    op.drop_index(op.f("ix_lignes_commande_commande_id"), table_name="lignes_commande")
    op.drop_table("lignes_commande")
    op.drop_index(op.f("ix_paiements_commande_id"), table_name="paiements")
    op.drop_table("paiements")
    op.drop_index(op.f("ix_evenements_commande_commande_id"), table_name="evenements_commande")
    op.drop_table("evenements_commande")
    op.drop_index(op.f("ix_commandes_telephone"), table_name="commandes")
    op.drop_index(op.f("ix_commandes_statut"), table_name="commandes")
    op.drop_index(op.f("ix_commandes_client_id"), table_name="commandes")
    op.drop_table("commandes")
    op.drop_table("zones_livraison")
