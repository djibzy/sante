"""Tarif professionnel retenu par chaque commande, repris quand l'équipe corrige les articles.

Les commandes déjà passées restent au tarif public (aucune n'est encore en production).

Révision : 0014
Précédente : 0013
Créée le : 2026-11-13 16:37:10.415492
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "commandes",
        sa.Column(
            "tarif_professionnel", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("commandes", "tarif_professionnel")
