"""Couleur de l'article sur chaque photo : la photo suit la couleur choisie sur la fiche, et
illustre cette couleur sur la page « Explorer ».

Révision : 0010
Précédente : 0009
Créée le : 2026-11-13 08:25:16.496226
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("images_produits", sa.Column("couleur", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("images_produits", "couleur")
