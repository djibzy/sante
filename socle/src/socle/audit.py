"""Journal d'audit en ajout seul : qui a fait quoi, sur quel objet, quand, d'où.

Chaque service déclare sa propre table en héritant de JournalAuditMixin, dans sa propre base.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from socle.db import IdMixin


class JournalAuditMixin(IdMixin):
    acteur_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    objet_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    objet_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    adresse_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def journaliser(
    session: AsyncSession,
    modele: Callable[..., JournalAuditMixin],
    *,
    action: str,
    acteur_id: UUID | None = None,
    objet_type: str | None = None,
    objet_id: object | None = None,
    details: dict[str, Any] | None = None,
    adresse_ip: str | None = None,
) -> None:
    """Ajoute une entrée au journal, dans la même transaction que l'action journalisée."""
    session.add(
        modele(
            acteur_id=acteur_id,
            action=action,
            objet_type=objet_type,
            objet_id=str(objet_id) if objet_id is not None else None,
            details=details or {},
            adresse_ip=adresse_ip,
        )
    )
