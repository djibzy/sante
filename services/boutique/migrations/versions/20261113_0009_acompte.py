"""Acompte des articles faits à la demande : montant sur la commande, part gardée si le client
annule, statut « en attente de l'acompte ». Contraintes ajoutées à la main (Alembic ne voit
pas les CHECK des tables existantes).

Révision : 0009
Précédente : 0008
Créée le : 2026-11-13 07:58:20.558829
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AVANT = (
    "'devis_demande', 'devis_envoye', 'devis_refuse', 'en_attente', 'confirmee', "
    "'en_preparation', 'prete', 'en_livraison', 'livree', 'annulee'"
)
APRES = (
    "'devis_demande', 'devis_envoye', 'devis_refuse', 'en_attente', 'acompte_attendu', "
    "'confirmee', 'en_preparation', 'prete', 'en_livraison', 'livree', 'annulee'"
)


def upgrade() -> None:
    op.add_column(
        "commandes", sa.Column("acompte", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "commandes",
        sa.Column("acompte_garde", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_commandes_acompte_valide"), "commandes", "acompte >= 0 AND acompte <= total"
    )
    op.create_check_constraint(
        op.f("ck_commandes_acompte_garde_valide"),
        "commandes",
        "acompte_garde >= 0 AND acompte_garde <= acompte",
    )
    op.drop_constraint(op.f("ck_commandes_statut_valide"), "commandes", type_="check")
    op.create_check_constraint(
        op.f("ck_commandes_statut_valide"), "commandes", f"statut IN ({APRES})"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_commandes_statut_valide"), "commandes", type_="check")
    op.create_check_constraint(
        op.f("ck_commandes_statut_valide"), "commandes", f"statut IN ({AVANT})"
    )
    op.drop_constraint(op.f("ck_commandes_acompte_garde_valide"), "commandes", type_="check")
    op.drop_constraint(op.f("ck_commandes_acompte_valide"), "commandes", type_="check")
    op.drop_column("commandes", "acompte_garde")
    op.drop_column("commandes", "acompte")
