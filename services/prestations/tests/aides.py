"""Raccourcis pour créer partenaires, contrats et collectes dans les tests."""

from datetime import date
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from prestations.models import JournalAudit, Notification

from .conftest import jeton

GESTION = jeton(["prestations:admin"], nom="Gestion")
TERRAIN = jeton(["prestations:terrain"], nom="Agent de collecte")
LUNDI = date(2026, 11, 16)


async def partenaire(client: AsyncClient, **autres: Any) -> dict[str, Any]:
    donnees = {
        "nom": "Pressing du Fleuve",
        "type": "pressing",
        "telephone": "76 11 22 33",
        "quartier": "Hamdallaye",
        "tarifs": {"blouse": 300, "drap": 400, "taie": 150},
        **autres,
    }
    reponse = await client.post("/api/v1/admin/partenaires", json=donnees, headers=GESTION)
    assert reponse.status_code == 201, reponse.text
    resultat: dict[str, Any] = reponse.json()
    return resultat


async def contrat(client: AsyncClient, **autres: Any) -> dict[str, Any]:
    donnees = {
        "structure": "Clinique Pasteur",
        "type_structure": "clinique",
        "contact": "Awa Traoré, surveillante",
        "telephone": "76 00 00 01",
        "adresse": "Badalabougou, rue 100, porte 10",
        "jours_collecte": [1, 4],
        "delai_retour_jours": 2,
        "formule": "piece",
        "tarifs": {"blouse": 500, "drap": 700, "taie": 250},
        "debut_le": "2026-11-02",
        **autres,
    }
    reponse = await client.post("/api/v1/admin/contrats", json=donnees, headers=GESTION)
    assert reponse.status_code == 201, reponse.text
    resultat: dict[str, Any] = reponse.json()
    return resultat


def lignes(**quantites: int) -> list[dict[str, Any]]:
    return [{"article": article, "quantite": n} for article, n in quantites.items()]


async def enlever(
    client: AsyncClient,
    contrat_id: str,
    jour: date = LUNDI,
    entetes: dict[str, str] = TERRAIN,
    **quantites: int,
) -> dict[str, Any]:
    reponse = await client.post(
        "/api/v1/collectes",
        json={
            "contrat_id": contrat_id,
            "jour": jour.isoformat(),
            "lignes": lignes(**quantites),
            "sacs": 2,
            "remis_par": "Awa, surveillante",
        },
        headers=entetes,
    )
    assert reponse.status_code == 201, reponse.text
    resultat: dict[str, Any] = reponse.json()
    return resultat


async def action(
    client: AsyncClient,
    reference: str,
    quoi: str,
    corps: dict[str, Any] | None = None,
    entetes: dict[str, str] = TERRAIN,
) -> dict[str, Any]:
    reponse = await client.post(
        f"/api/v1/collectes/{reference}/{quoi}", json=corps or {}, headers=entetes
    )
    assert reponse.status_code == 200, reponse.text
    resultat: dict[str, Any] = reponse.json()
    return resultat


async def rendre(client: AsyncClient, reference: str, **quantites: int) -> dict[str, Any]:
    return await action(
        client, reference, "retour", {"lignes": lignes(**quantites), "recu_par": "Mariam, lingère"}
    )


async def sms(app: FastAPI) -> list[Notification]:
    async with app.state.sessions() as session:
        return list(await session.scalars(select(Notification).order_by(Notification.cree_le)))


async def journal(app: FastAPI) -> list[str]:
    async with app.state.sessions() as session:
        return list(
            await session.scalars(select(JournalAudit.action).order_by(JournalAudit.cree_le))
        )
