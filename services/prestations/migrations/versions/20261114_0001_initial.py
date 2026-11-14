"""Prestations : demandes des structures, blanchisseries partenaires, contrats, collectes
comptées article par article, boîte d'envoi des SMS, journal d'audit.

Révision : 0001
Précédente :
Créée le : 2026-11-14 08:42:38.165133
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journal_audit",
        sa.Column("acteur_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("objet_type", sa.String(length=80), nullable=True),
        sa.Column("objet_id", sa.String(length=64), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("adresse_ip", sa.String(length=45), nullable=True),
        sa.Column(
            "cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_audit")),
    )
    op.create_index(
        op.f("ix_journal_audit_acteur_id"), "journal_audit", ["acteur_id"], unique=False
    )
    op.create_table(
        "notifications",
        sa.Column("objet_type", sa.String(length=20), nullable=False),
        sa.Column("objet_id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "etat IN ('a_envoyer', 'envoyee', 'echec')", name=op.f("ck_notifications_etat_valide")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(op.f("ix_notifications_etat"), "notifications", ["etat"], unique=False)
    op.create_index(op.f("ix_notifications_objet_id"), "notifications", ["objet_id"], unique=False)
    op.create_table(
        "partenaires",
        sa.Column("nom", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("est_interne", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("contact", sa.String(length=120), server_default="", nullable=False),
        sa.Column("telephone", sa.String(length=20), nullable=False),
        sa.Column("quartier", sa.String(length=160), server_default="", nullable=False),
        sa.Column("delai_jours", sa.Integer(), server_default="2", nullable=False),
        sa.Column("capacite_pieces_jour", sa.Integer(), nullable=True),
        sa.Column("mode_tarif", sa.String(length=10), server_default="piece", nullable=False),
        sa.Column(
            "tarifs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("tarif_kg", sa.Integer(), nullable=True),
        sa.Column("hygiene_verifiee_le", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
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
            "mode_tarif <> 'kg' OR tarif_kg IS NOT NULL",
            name=op.f("ck_partenaires_tarif_kg_requis"),
        ),
        sa.CheckConstraint(
            "mode_tarif IN ('piece', 'kg')", name=op.f("ck_partenaires_mode_tarif_valide")
        ),
        sa.CheckConstraint(
            "type IN ('blanchisserie', 'pressing')", name=op.f("ck_partenaires_type_valide")
        ),
        sa.CheckConstraint(
            "capacite_pieces_jour IS NULL OR capacite_pieces_jour > 0",
            name=op.f("ck_partenaires_capacite_positive"),
        ),
        sa.CheckConstraint(
            "delai_jours BETWEEN 0 AND 14", name=op.f("ck_partenaires_delai_valide")
        ),
        sa.CheckConstraint(
            "tarif_kg IS NULL OR tarif_kg >= 0", name=op.f("ck_partenaires_tarif_kg_positif")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partenaires")),
        sa.UniqueConstraint("nom", name=op.f("uq_partenaires_nom")),
    )
    op.create_table(
        "contrats",
        sa.Column("numero", sa.Integer(), sa.Identity(always=False, start=101), nullable=False),
        sa.Column(
            "service", sa.String(length=30), server_default="entretien_linge", nullable=False
        ),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("structure", sa.String(length=160), nullable=False),
        sa.Column("type_structure", sa.String(length=20), nullable=False),
        sa.Column("contact", sa.String(length=120), nullable=False),
        sa.Column("telephone", sa.String(length=20), nullable=False),
        sa.Column("adresse", sa.String(length=300), nullable=False),
        sa.Column("partenaire_id", sa.Uuid(), nullable=True),
        sa.Column(
            "jours_collecte",
            postgresql.ARRAY(sa.SmallInteger()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("delai_retour_jours", sa.Integer(), server_default="3", nullable=False),
        sa.Column("formule", sa.String(length=10), nullable=False),
        sa.Column(
            "tarifs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("forfait_mensuel", sa.Integer(), nullable=True),
        sa.Column("pieces_incluses", sa.Integer(), nullable=True),
        sa.Column("prix_piece_supplementaire", sa.Integer(), nullable=True),
        sa.Column("sms_actifs", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("debut_le", sa.Date(), nullable=False),
        sa.Column("fin_le", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
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
            "formule <> 'forfait' OR forfait_mensuel IS NOT NULL",
            name=op.f("ck_contrats_forfait_requis"),
        ),
        sa.CheckConstraint(
            "formule IN ('piece', 'forfait')", name=op.f("ck_contrats_formule_valide")
        ),
        sa.CheckConstraint(
            "service IN ('entretien_linge')", name=op.f("ck_contrats_service_valide")
        ),
        sa.CheckConstraint(
            "statut IN ('actif', 'suspendu', 'termine')", name=op.f("ck_contrats_statut_valide")
        ),
        sa.CheckConstraint(
            "type_structure IN ('clinique', 'cscom', 'hopital', 'cabinet', 'maternite', 'laboratoire', 'pharmacie', 'ecole', 'ong', 'autre')",
            name=op.f("ck_contrats_type_structure_valide"),
        ),
        sa.CheckConstraint(
            "coalesce(forfait_mensuel, 0) >= 0 AND coalesce(pieces_incluses, 0) >= 0 AND coalesce(prix_piece_supplementaire, 0) >= 0",
            name=op.f("ck_contrats_montants_positifs"),
        ),
        sa.CheckConstraint(
            "delai_retour_jours BETWEEN 1 AND 14", name=op.f("ck_contrats_delai_valide")
        ),
        sa.CheckConstraint(
            "fin_le IS NULL OR fin_le >= debut_le", name=op.f("ck_contrats_dates_coherentes")
        ),
        sa.CheckConstraint(
            "jours_collecte <@ ARRAY[1, 2, 3, 4, 5, 6, 7]::smallint[]",
            name=op.f("ck_contrats_jours_valides"),
        ),
        sa.ForeignKeyConstraint(
            ["partenaire_id"],
            ["partenaires.id"],
            name=op.f("fk_contrats_partenaire_id_partenaires"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contrats")),
        sa.UniqueConstraint("numero", name=op.f("uq_contrats_numero")),
    )
    op.create_index(op.f("ix_contrats_partenaire_id"), "contrats", ["partenaire_id"], unique=False)
    op.create_index(op.f("ix_contrats_statut"), "contrats", ["statut"], unique=False)
    op.create_table(
        "collectes",
        sa.Column("numero", sa.Integer(), sa.Identity(always=False, start=1001), nullable=False),
        sa.Column("contrat_id", sa.Uuid(), nullable=False),
        sa.Column("partenaire_id", sa.Uuid(), nullable=True),
        sa.Column("prevue_le", sa.Date(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("enlevee_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deposee_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prete_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rendue_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("annulee_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retour_prevu_le", sa.Date(), nullable=True),
        sa.Column("sacs", sa.Integer(), nullable=True),
        sa.Column("poids_kg", sa.Numeric(precision=6, scale=1), nullable=True),
        sa.Column("cout_kg", sa.Integer(), nullable=True),
        sa.Column("remis_par", sa.String(length=120), server_default="", nullable=False),
        sa.Column("recu_par", sa.String(length=120), server_default="", nullable=False),
        sa.Column("observations", sa.Text(), server_default="", nullable=False),
        sa.Column("observations_retour", sa.Text(), server_default="", nullable=False),
        sa.Column("motif_annulation", sa.String(length=200), server_default="", nullable=False),
        sa.Column("enlevee_par", sa.Uuid(), nullable=True),
        sa.Column("rendue_par", sa.Uuid(), nullable=True),
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
            "statut IN ('prevue', 'enlevee', 'chez_partenaire', 'prete', 'rendue', 'annulee')",
            name=op.f("ck_collectes_statut_valide"),
        ),
        sa.CheckConstraint(
            "cout_kg IS NULL OR cout_kg >= 0", name=op.f("ck_collectes_cout_kg_positif")
        ),
        sa.CheckConstraint(
            "poids_kg IS NULL OR poids_kg > 0", name=op.f("ck_collectes_poids_positif")
        ),
        sa.CheckConstraint("sacs IS NULL OR sacs >= 0", name=op.f("ck_collectes_sacs_positifs")),
        sa.ForeignKeyConstraint(
            ["contrat_id"], ["contrats.id"], name=op.f("fk_collectes_contrat_id_contrats")
        ),
        sa.ForeignKeyConstraint(
            ["partenaire_id"],
            ["partenaires.id"],
            name=op.f("fk_collectes_partenaire_id_partenaires"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collectes")),
        sa.UniqueConstraint("numero", name=op.f("uq_collectes_numero")),
    )
    op.create_index(op.f("ix_collectes_contrat_id"), "collectes", ["contrat_id"], unique=False)
    op.create_index(
        op.f("ix_collectes_partenaire_id"), "collectes", ["partenaire_id"], unique=False
    )
    op.create_index(op.f("ix_collectes_prevue_le"), "collectes", ["prevue_le"], unique=False)
    op.create_index(op.f("ix_collectes_rendue_le"), "collectes", ["rendue_le"], unique=False)
    op.create_index(
        op.f("ix_collectes_retour_prevu_le"), "collectes", ["retour_prevu_le"], unique=False
    )
    op.create_index(op.f("ix_collectes_statut"), "collectes", ["statut"], unique=False)
    # Une seule collecte par contrat et par jour, hors collectes annulées.
    op.create_index(
        "uq_collectes_contrat_jour",
        "collectes",
        ["contrat_id", "prevue_le"],
        unique=True,
        postgresql_where=sa.text("statut <> 'annulee'"),
    )
    op.create_table(
        "demandes",
        sa.Column("numero", sa.Integer(), sa.Identity(always=False, start=101), nullable=False),
        sa.Column("service", sa.String(length=30), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("structure", sa.String(length=160), nullable=False),
        sa.Column("type_structure", sa.String(length=20), nullable=False),
        sa.Column("contact", sa.String(length=120), nullable=False),
        sa.Column("telephone", sa.String(length=20), nullable=False),
        sa.Column("quartier", sa.String(length=160), nullable=False),
        sa.Column(
            "volumes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("collectes_par_semaine", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), server_default="", nullable=False),
        sa.Column("notes_equipe", sa.Text(), server_default="", nullable=False),
        sa.Column("contrat_id", sa.Uuid(), nullable=True),
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
            "service IN ('entretien_linge')", name=op.f("ck_demandes_service_valide")
        ),
        sa.CheckConstraint(
            "statut IN ('nouvelle', 'en_discussion', 'signee', 'sans_suite')",
            name=op.f("ck_demandes_statut_valide"),
        ),
        sa.CheckConstraint(
            "type_structure IN ('clinique', 'cscom', 'hopital', 'cabinet', 'maternite', 'laboratoire', 'pharmacie', 'ecole', 'ong', 'autre')",
            name=op.f("ck_demandes_type_structure_valide"),
        ),
        sa.CheckConstraint(
            "collectes_par_semaine IS NULL OR collectes_par_semaine BETWEEN 1 AND 7",
            name=op.f("ck_demandes_collectes_valides"),
        ),
        sa.ForeignKeyConstraint(
            ["contrat_id"], ["contrats.id"], name=op.f("fk_demandes_contrat_id_contrats")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_demandes")),
        sa.UniqueConstraint("numero", name=op.f("uq_demandes_numero")),
    )
    op.create_index(op.f("ix_demandes_contrat_id"), "demandes", ["contrat_id"], unique=False)
    op.create_index(op.f("ix_demandes_statut"), "demandes", ["statut"], unique=False)
    op.create_index(op.f("ix_demandes_telephone"), "demandes", ["telephone"], unique=False)
    op.create_table(
        "lignes_collecte",
        sa.Column("collecte_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("article", sa.String(length=20), nullable=False),
        sa.Column("precision", sa.String(length=80), server_default="", nullable=False),
        sa.Column("quantite_enlevee", sa.Integer(), nullable=False),
        sa.Column("quantite_rendue", sa.Integer(), nullable=True),
        sa.Column("prix_unitaire", sa.Integer(), nullable=True),
        sa.Column("cout_unitaire", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "article IN ('blouse', 'tunique', 'pantalon', 'casaque', 'drap', 'alese', 'taie', 'couverture', 'serviette', 'champ', 'rideau', 'autre')",
            name=op.f("ck_lignes_collecte_article_valide"),
        ),
        sa.CheckConstraint(
            "coalesce(prix_unitaire, 0) >= 0 AND coalesce(cout_unitaire, 0) >= 0",
            name=op.f("ck_lignes_collecte_prix_positifs"),
        ),
        sa.CheckConstraint(
            "quantite_enlevee >= 0 AND coalesce(quantite_rendue, 0) >= 0",
            name=op.f("ck_lignes_collecte_quantites_positives"),
        ),
        sa.ForeignKeyConstraint(
            ["collecte_id"],
            ["collectes.id"],
            name=op.f("fk_lignes_collecte_collecte_id_collectes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lignes_collecte")),
        sa.UniqueConstraint(
            "collecte_id", "article", "precision", name=op.f("uq_lignes_collecte_collecte_id")
        ),
    )
    op.create_index(
        op.f("ix_lignes_collecte_collecte_id"), "lignes_collecte", ["collecte_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lignes_collecte_collecte_id"), table_name="lignes_collecte")
    op.drop_table("lignes_collecte")
    op.drop_index(op.f("ix_demandes_telephone"), table_name="demandes")
    op.drop_index(op.f("ix_demandes_statut"), table_name="demandes")
    op.drop_index(op.f("ix_demandes_contrat_id"), table_name="demandes")
    op.drop_table("demandes")
    op.drop_index(
        "uq_collectes_contrat_jour",
        table_name="collectes",
        postgresql_where=sa.text("statut <> 'annulee'"),
    )
    op.drop_index(op.f("ix_collectes_statut"), table_name="collectes")
    op.drop_index(op.f("ix_collectes_retour_prevu_le"), table_name="collectes")
    op.drop_index(op.f("ix_collectes_rendue_le"), table_name="collectes")
    op.drop_index(op.f("ix_collectes_prevue_le"), table_name="collectes")
    op.drop_index(op.f("ix_collectes_partenaire_id"), table_name="collectes")
    op.drop_index(op.f("ix_collectes_contrat_id"), table_name="collectes")
    op.drop_table("collectes")
    op.drop_index(op.f("ix_contrats_statut"), table_name="contrats")
    op.drop_index(op.f("ix_contrats_partenaire_id"), table_name="contrats")
    op.drop_table("contrats")
    op.drop_table("partenaires")
    op.drop_index(op.f("ix_notifications_objet_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_etat"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_journal_audit_acteur_id"), table_name="journal_audit")
    op.drop_table("journal_audit")
