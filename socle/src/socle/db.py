"""Accès à PostgreSQL : conventions de nommage, colonnes communes, sessions."""

from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.pool import NullPool

from socle.ids import uuid7

# Noms stables pour les contraintes : les migrations restent lisibles et reproductibles.
CONVENTION_NOMMAGE = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class IdMixin:
    """Clé primaire UUID v7, générée par l'application (ou l'appareil).

    eager_defaults : les valeurs calculées par la base (dates) sont relues dès l'écriture,
    ce qui évite tout chargement implicite en mode asynchrone.
    """

    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)


class HorodatageMixin:
    """Dates de création et de dernière modification."""

    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def creer_moteur(url: str, *, pool: bool = True) -> AsyncEngine:
    if pool:
        return create_async_engine(url, pool_pre_ping=True)
    return create_async_engine(url, poolclass=NullPool)


def fabrique_sessions(moteur: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(moteur, expire_on_commit=False)


async def session_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Dépendance FastAPI : une session par requête, fermée à la fin."""
    sessions: async_sessionmaker[AsyncSession] = request.app.state.sessions
    async with sessions() as session:
        yield session
