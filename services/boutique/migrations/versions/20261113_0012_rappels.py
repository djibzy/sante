"""Rappels SMS : date d'entrée dans le statut actuel (reprise de l'historique pour les
commandes existantes) et nombre de rappels envoyés depuis.

Révision : 0012
Précédente : 0011
Créée le : 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "commandes",
        sa.Column(
            "statut_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "commandes", sa.Column("relances", sa.Integer(), server_default="0", nullable=False)
    )
    # Commandes existantes : depuis le dernier passage dans leur statut actuel.
    op.execute(
        """
        UPDATE commandes AS c SET statut_le = COALESCE(
            (SELECT max(e.cree_le) FROM evenements_commande AS e
             WHERE e.commande_id = c.id AND e.statut = c.statut),
            c.modifie_le)
        """
    )


def downgrade() -> None:
    op.drop_column("commandes", "relances")
    op.drop_column("commandes", "statut_le")
