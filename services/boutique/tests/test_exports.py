"""Exports CSV pour la comptabilité : lisibles par Excel, sans formule injectée, tracés."""

import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from boutique.models import JournalAudit

from .aides import commander, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
AUJOURD_HUI = datetime.now(UTC).date()
PERIODE = {"du": str(AUJOURD_HUI - timedelta(days=7)), "au": str(AUJOURD_HUI)}


def lire(contenu: bytes) -> list[list[str]]:
    texte = contenu.decode("utf-8")
    assert texte.startswith("﻿")  # Excel reconnaît l'UTF-8
    return list(csv.reader(io.StringIO(texte.removeprefix("﻿")), delimiter=";"))


async def test_exports_comptables(app: FastAPI, client: AsyncClient) -> None:
    creee = await commander(
        client, [await ligne(client, "kit-hygiene")], nom='=HYPERLINK("http://x")'
    )
    reference = creee["commande"]["reference"]
    for etape in ("confirmee", "prete", "livree"):
        reponse = await client.post(
            f"/api/v1/admin/commandes/{reference}/statut", json={"statut": etape}, headers=ADMIN
        )
        assert reponse.status_code == 200, reponse.text
    await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": 7_500, "moyen": "orange_money", "reference": "OM123"},
        headers=ADMIN,
    )

    factures = await client.get("/api/v1/admin/exports/factures.csv", params=PERIODE, headers=ADMIN)
    assert factures.status_code == 200
    assert factures.headers["content-type"] == "text/csv; charset=utf-8"
    assert "bibou-factures-" in factures.headers["content-disposition"]
    entete, facture = lire(factures.content)
    assert entete[:4] == ["Facture", "Date", "Commande", "Client"]
    assert facture[0].startswith(f"F{AUJOURD_HUI.year}-")
    assert facture[1] == f"{AUJOURD_HUI:%d/%m/%Y}"
    assert facture[2:4] == [reference, '\'=HYPERLINK("http://x")']  # formule neutralisée
    assert facture[-3:] == ["7500", "7500", "0"]

    encaissements = lire(
        (
            await client.get(
                "/api/v1/admin/exports/encaissements.csv", params=PERIODE, headers=ADMIN
            )
        ).content
    )
    assert encaissements[0][:2] == ["Date", "Opération"]
    assert encaissements[1][1:] == [
        "Encaissement",
        reference,
        facture[0],
        "Orange Money",
        "7500",
        "OM123",
    ]

    commandes = lire(
        (
            await client.get("/api/v1/admin/exports/commandes.csv", params=PERIODE, headers=ADMIN)
        ).content
    )
    assert commandes[1][:3] == [reference, f"{AUJOURD_HUI:%d/%m/%Y}", "Livrée"]

    hier = {"du": str(AUJOURD_HUI - timedelta(days=9)), "au": str(AUJOURD_HUI - timedelta(days=8))}
    vide = await client.get("/api/v1/admin/exports/commandes.csv", params=hier, headers=ADMIN)
    assert len(lire(vide.content)) == 1  # l'en-tête seul

    async with app.state.sessions() as session:
        actions = list(
            await session.scalars(
                select(JournalAudit.action).where(JournalAudit.objet_type == "export")
            )
        )
    assert actions == [
        "export.factures",
        "export.encaissements",
        "export.commandes",
        "export.commandes",
    ]


async def test_exports_reserves_et_bornes(client: AsyncClient) -> None:
    url = "/api/v1/admin/exports/factures.csv"
    assert (await client.get(url, params=PERIODE)).status_code == 401
    assert (
        await client.get(url, params=PERIODE, headers=jeton(["boutique:atelier"]))
    ).status_code == 403
    inverse = {"du": PERIODE["au"], "au": PERIODE["du"]}
    assert (await client.get(url, params=inverse, headers=ADMIN)).status_code == 422
    long = {"du": str(AUJOURD_HUI - timedelta(days=400)), "au": str(AUJOURD_HUI)}
    assert (await client.get(url, params=long, headers=ADMIN)).status_code == 422
    inconnu = "/api/v1/admin/exports/clients.csv"
    assert (await client.get(inconnu, params=PERIODE, headers=ADMIN)).status_code == 422
