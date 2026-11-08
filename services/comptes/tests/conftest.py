import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from comptes.config import ParametresComptes
from comptes.main import creer_app

URL = os.environ.get(
    "COMPTES_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/comptes_test"
)
RACINE = Path(__file__).resolve().parents[1]
MOT_DE_PASSE = "un-mot-de-passe-solide"


async def _vider_schema() -> None:
    moteur = create_async_engine(URL, poolclass=NullPool)
    async with moteur.begin() as connexion:
        await connexion.execute(text("DROP SCHEMA public CASCADE"))
        await connexion.execute(text("CREATE SCHEMA public"))
    await moteur.dispose()


@pytest.fixture(scope="session", autouse=True)
def base_de_test() -> Iterator[None]:
    """Base vide, puis toutes les migrations : on teste aussi les migrations."""
    asyncio.run(_vider_schema())
    configuration = Config(str(RACINE / "alembic.ini"))
    configuration.set_main_option("sqlalchemy.url", URL)
    command.upgrade(configuration, "head")
    yield


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    parametres = ParametresComptes(
        database_url=URL, environnement="test", db_pool=False, cookie_securise=False
    )
    application = creer_app(parametres)
    yield application
    async with application.state.moteur.begin() as connexion:
        await connexion.execute(
            text("TRUNCATE utilisateurs, organisations, journal_audit RESTART IDENTITY CASCADE")
        )
    await application.state.moteur.dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def inscrire(
    client: AsyncClient, telephone: str = "76 12 34 56", nom: str = "Awa Traoré"
) -> dict[str, Any]:
    reponse = await client.post(
        "/api/v1/auth/inscription",
        json={
            "telephone": telephone,
            "nom": nom,
            "mot_de_passe": MOT_DE_PASSE,
            "accepte_conditions": True,
        },
    )
    assert reponse.status_code == 201, reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees


def entete(jetons: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {jetons['jeton_acces']}"}
