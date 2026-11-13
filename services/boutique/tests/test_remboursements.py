"""Argent rendu au client : annulation, acompte gardé, trop-perçu ; suivi et comptabilité."""

import csv
import io
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from boutique.models import JournalAudit, Notification

from .aides import commander, fiche, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
AUJOURD_HUI = str(datetime.now(UTC).date())


@pytest.fixture(autouse=True)
def avec_acompte(app: FastAPI) -> None:
    app.state.parametres.acompte_pourcent = 50


async def action(client: AsyncClient, reference: str, chemin: str, corps: dict[str, Any]) -> Any:
    return await client.post(
        f"/api/v1/admin/commandes/{reference}/{chemin}", json=corps, headers=ADMIN
    )


async def rendre(client: AsyncClient, commande: str, montant: int, **autres: Any) -> Any:
    return await action(
        client, commande, "remboursements", {"montant": montant, "moyen": "especes", **autres}
    )


async def vue(client: AsyncClient, reference: str) -> Any:
    return (await client.get(f"/api/v1/admin/commandes/{reference}", headers=ADMIN)).json()


async def a_rembourser(client: AsyncClient) -> list[tuple[str, int]]:
    reponse = await client.get(
        "/api/v1/admin/commandes", params={"a_rembourser": True}, headers=ADMIN
    )
    return [(c["reference"], c["du_au_client"]) for c in reponse.json()["elements"]]


async def alertes(client: AsyncClient) -> Any:
    periode = {"du": AUJOURD_HUI, "au": AUJOURD_HUI}
    reponse = await client.get("/api/v1/admin/tableau-de-bord", params=periode, headers=ADMIN)
    return reponse.json()


def lire(contenu: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(contenu.decode("utf-8").removeprefix("﻿")), delimiter=";"))


async def test_annulation_par_la_boutique_tout_est_rendu(app: FastAPI, client: AsyncClient) -> None:
    creee = await commander(client, [await ligne(client, "blouse-medicale-brodee", "M")])
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    assert (await action(client, reference, "statut", {"statut": "confirmee"})).status_code == 200
    await action(client, reference, "paiements", {"montant": 6_300, "moyen": "especes"})
    annulee = await action(
        client, reference, "statut", {"statut": "annulee", "garder_acompte": False}
    )
    assert annulee.json()["du_au_client"] == 6_300
    assert await a_rembourser(client) == [(reference, 6_300)]
    tableau = await alertes(client)
    assert (tableau["alertes"]["a_rembourser"], tableau["alertes"]["montant_a_rembourser"]) == (
        1,
        6_300,
    )

    trop = await rendre(client, reference, 7_000)
    assert trop.status_code == 422
    assert trop.json()["detail"] == "Le montant dépasse ce qui est dû au client (6 300 FCFA)"
    premiere = await rendre(client, reference, 4_000, moyen="orange_money", reference="OM-R1")
    assert premiere.status_code == 201, premiere.text
    commande = premiere.json()
    assert (commande["du_au_client"], commande["montant_paye"]) == (2_300, 2_300)
    assert [(r["montant"], r["moyen"], r["reference"]) for r in commande["remboursements"]] == [
        (4_000, "orange_money", "OM-R1")
    ]
    dernier = commande["historique_complet"][-1]
    assert dernier["note"] == "Remboursement de 4 000 FCFA (Orange Money)"
    assert dernier["visible_client"] is True

    # Le reste en espèces, client prévenu de vive voix : pas de SMS.
    seconde = await rendre(client, reference, 2_300, prevenir_client=False)
    assert seconde.json()["du_au_client"] == 0
    assert (await rendre(client, reference, 100)).status_code == 409
    assert await a_rembourser(client) == []

    async with app.state.sessions() as session:
        textes = list(
            await session.scalars(
                select(Notification.message).where(Notification.message.contains("rendus"))
            )
        )
        actions = list(
            await session.scalars(
                select(JournalAudit.details).where(JournalAudit.action == "commande.remboursement")
            )
        )
    assert textes == [
        f"Bibou : 4 000 FCFA vous ont été rendus (Orange Money) pour la commande {reference}."
    ]
    assert actions == [
        {"montant": 4_000, "moyen": "orange_money"},
        {"montant": 2_300, "moyen": "especes"},
    ]

    suivi = (await client.get(f"/api/v1/suivi/{reference}", params={"cle": cle})).json()
    assert (suivi["montant_paye"], suivi["rembourse"]) == (0, 6_300)

    # Comptabilité : sorties de caisse en négatif, payé et remboursé par commande.
    periode = {"du": AUJOURD_HUI, "au": AUJOURD_HUI}
    caisse = lire(
        (
            await client.get(
                "/api/v1/admin/exports/encaissements.csv", params=periode, headers=ADMIN
            )
        ).content
    )
    assert [(ligne[1], ligne[5]) for ligne in caisse[1:]] == [
        ("Encaissement", "6300"),
        ("Remboursement", "-4000"),
        ("Remboursement", "-2300"),
    ]
    commandes = lire(
        (
            await client.get("/api/v1/admin/exports/commandes.csv", params=periode, headers=ADMIN)
        ).content
    )
    colonnes = dict(zip(commandes[0], commandes[1], strict=True))
    assert (colonnes["Payé"], colonnes["Remboursé"], colonnes["Reste à payer"]) == (
        "6300",
        "6300",
        "0",
    )
    tableau = await alertes(client)
    assert (tableau["ventes"]["encaisse"], tableau["ventes"]["rembourse"]) == (6_300, 6_300)
    assert tableau["alertes"]["a_rembourser"] == 0


async def test_acompte_garde_quand_le_client_annule(client: AsyncClient) -> None:
    reference = (await commander(client, [await ligne(client, "blouse-medicale-brodee", "M")]))[
        "commande"
    ]["reference"]
    await action(client, reference, "statut", {"statut": "confirmee"})
    await action(client, reference, "paiements", {"montant": 12_500, "moyen": "especes"})
    annulee = (await action(client, reference, "statut", {"statut": "annulee"})).json()
    assert (annulee["acompte_garde"], annulee["du_au_client"]) == (6_300, 6_200)
    assert (await rendre(client, reference, 6_300)).status_code == 422  # l'acompte reste gardé
    commande = (await rendre(client, reference, 6_200)).json()
    assert (commande["du_au_client"], commande["montant_paye"]) == (0, 6_300)
    assert commande["reste_a_payer"] == 0  # annulée : le client ne doit plus rien


async def test_trop_percu_apres_une_correction(client: AsyncClient) -> None:
    kit = await fiche(client, "kit-hygiene")
    reference = (await commander(client, [{"produit_id": kit["id"], "quantite": 2}]))["commande"][
        "reference"
    ]
    await action(client, reference, "paiements", {"montant": 15_000, "moyen": "moov_money"})
    assert (await rendre(client, reference, 1_000)).status_code == 409  # rien de trop payé
    corrigee = await client.put(
        f"/api/v1/admin/commandes/{reference}/articles",
        json={"lignes": [{"produit_id": kit["id"], "quantite": 1}]},
        headers=ADMIN,
    )
    assert corrigee.json()["du_au_client"] == 7_500
    commande = (await rendre(client, reference, 7_500, moyen="moov_money")).json()
    assert (commande["du_au_client"], commande["reste_a_payer"]) == (0, 0)
    assert commande["montant_paye"] == commande["total"] == 7_500


async def test_droits_et_moyens(client: AsyncClient) -> None:
    reference = (await commander(client, [await ligne(client, "kit-hygiene")]))["commande"][
        "reference"
    ]
    chemin = f"/api/v1/admin/commandes/{reference}/remboursements"
    corps = {"montant": 500, "moyen": "especes"}
    assert (await client.post(chemin, json=corps)).status_code == 401
    atelier = jeton(["boutique:atelier"])
    assert (await client.post(chemin, json=corps, headers=atelier)).status_code == 403
    mobile = await client.post(chemin, json={**corps, "moyen": "mobile_money"}, headers=ADMIN)
    assert mobile.status_code == 422
