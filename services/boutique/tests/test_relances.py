"""Rappels SMS : acompte attendu (deux paliers), devis bientôt expiré, en journée seulement."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, text

from boutique.models import JournalAudit, Notification
from boutique.relances import relancer

from .aides import commander, ligne
from .conftest import jeton
from .test_notifications import GSM7

ADMIN = jeton(["boutique:admin"])
MIDI = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)


@pytest.fixture(autouse=True)
def avec_acompte(app: FastAPI) -> None:
    app.state.parametres.acompte_pourcent = 50


async def statut(client: AsyncClient, reference: str, nouveau: str) -> Any:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": nouveau}, headers=ADMIN
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def vieillir(app: FastAPI, reference: str, jours: int) -> None:
    async with app.state.sessions() as session:
        await session.execute(
            text("UPDATE commandes SET statut_le = :quand WHERE numero = :n"),
            {"quand": MIDI - timedelta(days=jours), "n": int(reference.removeprefix("BB-"))},
        )
        await session.commit()


async def sms(app: FastAPI) -> list[str]:
    async with app.state.sessions() as session:
        return list(
            await session.scalars(
                select(Notification.message).order_by(Notification.cree_le, Notification.id)
            )
        )


async def test_rappels_de_l_acompte(app: FastAPI, client: AsyncClient) -> None:
    reference = (await commander(client, [await ligne(client, "blouse-medicale-brodee", "M")]))[
        "commande"
    ]["reference"]
    await statut(client, reference, "confirmee")  # en attente de l'acompte (6 300 FCFA)
    parametres = app.state.parametres

    assert (await relancer(app.state.sessions, parametres, MIDI)).acomptes == 0  # trop tôt
    await vieillir(app, reference, 3)
    nuit = MIDI.replace(hour=22)
    assert (await relancer(app.state.sessions, parametres, nuit)).acomptes == 0  # pas la nuit
    assert (await relancer(app.state.sessions, parametres, MIDI)).acomptes == 1
    assert (await relancer(app.state.sessions, parametres, MIDI)).acomptes == 0  # une fois
    rappel = (await sms(app))[-1]
    assert rappel == (
        f"Bibou : rappel, l'acompte de 6 300 FCFA de la commande {reference} est attendu pour "
        "lancer la fabrication. En ligne depuis votre lien de suivi, ou à la boutique."
    )
    assert set(rappel) <= GSM7 and len(rappel) <= 160

    await vieillir(app, reference, 8)  # second palier
    assert (await relancer(app.state.sessions, parametres, MIDI)).acomptes == 1
    assert (await relancer(app.state.sessions, parametres, MIDI)).acomptes == 0  # plus rien
    commande = (await client.get(f"/api/v1/admin/commandes/{reference}", headers=ADMIN)).json()
    notes = [e["note"] for e in commande["historique_complet"] if not e["visible_client"]]
    assert notes[-2:] == ["Rappel SMS de l'acompte (1)", "Rappel SMS de l'acompte (2)"]
    assert commande["statut"] == "acompte_attendu"
    async with app.state.sessions() as session:
        traces = list(
            await session.scalars(
                select(JournalAudit.action).where(JournalAudit.action == "commande.relance")
            )
        )
    assert len(traces) == 2


async def test_acompte_paye_plus_de_rappel(app: FastAPI, client: AsyncClient) -> None:
    reference = (await commander(client, [await ligne(client, "blouse-medicale-brodee", "M")]))[
        "commande"
    ]["reference"]
    await statut(client, reference, "confirmee")
    encaissement = await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": 6_300, "moyen": "especes"},
        headers=ADMIN,
    )
    assert encaissement.json()["statut"] == "confirmee"
    await vieillir(app, reference, 10)
    bilan = await relancer(app.state.sessions, app.state.parametres, MIDI)
    assert (bilan.acomptes, bilan.devis) == (0, 0)


async def test_rappel_du_devis(app: FastAPI, client: AsyncClient) -> None:
    affiches = await ligne(client, "affiche-a2", quantite=20)
    demande = await client.post(
        "/api/v1/devis",
        json={
            "etablissement": "CSCom de Banconi",
            "client": {"nom": "Dr Oumar Sangaré", "telephone": "66 44 22 11"},
            "lignes": [affiches],
        },
    )
    reference = demande.json()["commande"]["reference"]
    url = f"/api/v1/admin/commandes/{reference}/devis"
    emis = await client.put(url, json={"lignes": [affiches], "validite_jours": 10}, headers=ADMIN)
    assert emis.status_code == 200, emis.text
    parametres = app.state.parametres
    assert (await relancer(app.state.sessions, parametres, MIDI)).devis == 0  # expire dans 10 j
    plus_tard = MIDI + timedelta(days=8)
    assert (await relancer(app.state.sessions, parametres, plus_tard)).devis == 1
    assert (await relancer(app.state.sessions, parametres, plus_tard)).devis == 0
    fin = (MIDI.date() + timedelta(days=10)).strftime("%d/%m")
    assert (await sms(app))[-1] == (
        f"Bibou : votre devis {reference} (30 000 FCFA) est valable jusqu'au {fin}. "
        "Acceptez-le depuis le lien recu, ou appelez-nous."
    )
    # Accepté ensuite : en attente de l'acompte, les rappels repartent de zéro.
    accepte = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": "confirmee"}, headers=ADMIN
    )
    assert accepte.json()["statut"] == "acompte_attendu"
    await vieillir(app, reference, 3)
    assert (await relancer(app.state.sessions, parametres, MIDI)).acomptes == 1
