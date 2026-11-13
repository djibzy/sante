"""Lien de paiement à envoyer à un proche : empreinte de sa clé, unique, facultative.

Révision : 0016
Précédente : 0015
Créée le : 2026-11-13 17:52:12.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "commandes", sa.Column("empreinte_cle_paiement", sa.String(length=64), nullable=True)
    )
    op.create_unique_constraint(
        op.f("uq_commandes_empreinte_cle_paiement"), "commandes", ["empreinte_cle_paiement"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_commandes_empreinte_cle_paiement"), "commandes", type_="unique")
    op.drop_column("commandes", "empreinte_cle_paiement")
