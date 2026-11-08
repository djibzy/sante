import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from boutique.config import ParametresBoutique
from boutique.donnees_demo import charger
from boutique.main import creer_app

URL = os.environ.get(
    "BOUTIQUE_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/boutique_test"
)
RACINE = Path(__file__).resolve().parents[1]
CLE = Ed25519PrivateKey.generate()  # joue le rôle du service Comptes pendant les tests
CLE_PUBLIQUE = (
    CLE.public_key()
    .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    .decode()
)


def jeton(roles: list[str] | None = None, nom: str = "Équipe boutique") -> dict[str, str]:
    """En-tête d'autorisation avec un jeton signé comme le ferait le service Comptes."""
    maintenant = datetime.now(UTC)
    valeur = jwt.encode(
        {
            "iss": "comptes",
            "aud": "sante",
            "sub": str(uuid4()),
            "iat": maintenant,
            "exp": maintenant + timedelta(minutes=15),
            "name": nom,
            "lang": "fr",
            "roles": roles or [],
        },
        CLE,
        algorithm="EdDSA",
    )
    return {"Authorization": f"Bearer {valeur}"}


async def _executer(*requetes: str) -> None:
    moteur = create_async_engine(URL, poolclass=NullPool)
    async with moteur.begin() as connexion:
        for requete in requetes:
            await connexion.execute(text(requete))
    await moteur.dispose()


@pytest.fixture(scope="session", autouse=True)
def base_de_test() -> Iterator[None]:
    asyncio.run(_executer("DROP SCHEMA public CASCADE", "CREATE SCHEMA public"))
    configuration = Config(str(RACINE / "alembic.ini"))
    configuration.set_main_option("sqlalchemy.url", URL)
    command.upgrade(configuration, "head")
    yield


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    await charger(URL)
    parametres = ParametresBoutique(
        database_url=URL, environnement="test", db_pool=False, jwt_cle_publique=CLE_PUBLIQUE
    )
    application = creer_app(parametres)
    yield application
    await application.state.moteur.dispose()
    await _executer("TRUNCATE rayons, produits, journal_audit RESTART IDENTITY CASCADE")


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
