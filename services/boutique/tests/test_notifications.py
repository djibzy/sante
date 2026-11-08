import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import select, update

from boutique.config import ParametresBoutique
from boutique.envoi import ExpediteurJournal, ExpediteurOrange, tour
from boutique.models import Notification
from boutique.notifications.messages import gsm
from socle.limites import LimiteDebit

from .aides import ADRESSE, commander, ligne, zone
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "ÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)


async def sms(app: FastAPI) -> list[Notification]:
    async with app.state.sessions() as session:
        return list(await session.scalars(select(Notification).order_by(Notification.cree_le)))


async def statut(client: AsyncClient, reference: str, nouveau: str, **autres: Any) -> None:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut",
        json={"statut": nouveau, **autres},
        headers=ADMIN,
    )
    assert reponse.status_code == 200, reponse.text


async def test_un_sms_a_chaque_etape_utile(app: FastAPI, client: AsyncClient) -> None:
    app.state.parametres.url_publique = "https://boutique.exemple.ml/"
    livreur = await client.post(
        "/api/v1/admin/livreurs",
        json={"nom": "Moussa Konaté", "telephone": "76 55 44 33"},
        headers=ADMIN,
    )
    livraison = {"mode": "livraison", "zone_id": await zone(client), "adresse": ADRESSE}
    creee = await commander(client, [await ligne(client, "kit-hygiene")], livraison=livraison)
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    await statut(client, reference, "confirmee")
    await statut(client, reference, "prete", note="Rangée en réserve", visible_client=False)
    await statut(client, reference, "en_livraison", livreur_id=livreur.json()["id"])
    await statut(client, reference, "livree")

    messages = [n.message for n in await sms(app)]
    assert messages == [
        f"Bibou : commande {reference} recue (8 500 FCFA). Nous vous appelons pour la "
        f"confirmer. Suivi : https://boutique.exemple.ml/suivi/{reference}?cle={cle}",
        f"Bibou : commande {reference} confirmée, prete vers le "
        f"{(datetime.now(UTC).date() + timedelta(days=8)).strftime('%d/%m')}.",
        f"Bibou : commande {reference} en route avec Moussa Konaté (+223 76 55 44 33). "
        "A payer : 8 500 FCFA.",
        f"Bibou : commande {reference} remise. Merci de votre confiance !",
    ]
    assert all(set(m) <= GSM7 for m in messages)
    assert {n.destinataire for n in await sms(app)} == {"+22376123456"}


async def test_sms_d_un_devis_et_d_un_retrait(app: FastAPI, client: AsyncClient) -> None:
    demande = await client.post(
        "/api/v1/devis",
        json={
            "etablissement": "CSCom de Banconi",
            "client": {"nom": "Dr Sangaré", "telephone": "66 44 22 11"},
            "lignes": [await ligne(client, "affiche-a2", quantite=40)],
        },
    )
    reference = demande.json()["commande"]["reference"]
    await client.put(
        f"/api/v1/admin/commandes/{reference}/devis",
        json={"lignes": [await ligne(client, "affiche-a2", quantite=40)]},
        headers=ADMIN,
    )
    await statut(client, reference, "confirmee")
    await statut(client, reference, "prete")
    messages = [n.message for n in await sms(app)]
    assert messages[0] == f"Bibou : demande de devis {reference} recue. Nous vous appelons."
    assert messages[1].startswith(f"Bibou : votre devis {reference} est pret (60 000 FCFA).")
    assert messages[-1] == (
        f"Bibou : commande {reference} prete. Venez la retirer à la boutique. "
        "A payer : 60 000 FCFA."
    )


def test_alphabet_gsm() -> None:
    assert gsm("Prête, reçue, « fête » – œuvre…") == 'Prete, recue, " fete " - oeuvre...'


async def test_le_processus_d_envoi_vide_la_boite(app: FastAPI, client: AsyncClient) -> None:
    await commander(client, [await ligne(client, "affiche-a2")])
    await commander(client, [await ligne(client, "affiche-a2")], telephone="65 00 11 22")
    assert await tour(app.state.sessions, ExpediteurJournal()) == 2
    assert {n.etat for n in await sms(app)} == {"envoyee"}
    assert await tour(app.state.sessions, ExpediteurJournal()) == 0


async def test_envoi_par_orange_avec_reprises(app: FastAPI, client: AsyncClient) -> None:
    await commander(client, [await ligne(client, "affiche-a2")])
    appels: list[httpx.Request] = []
    reponses_envoi = [
        httpx.Response(503),
        httpx.Response(
            201, json={"outboundSMSMessageRequest": {"resourceURL": "https://api/sms/42"}}
        ),
    ]

    def orange(requete: httpx.Request) -> httpx.Response:
        appels.append(requete)
        if requete.url.path == "/oauth/v3/token":
            return httpx.Response(200, json={"access_token": "jeton-orange", "expires_in": 3600})
        return reponses_envoi.pop(0)

    parametres = ParametresBoutique(
        sms_fournisseur="orange",
        sms_expediteur="+22370000000",
        sms_nom_expediteur="Bibou",
        orange_client_id="identifiant",
        orange_client_secret=SecretStr("secret"),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(orange)) as http:
        expediteur = ExpediteurOrange(parametres, http)
        await tour(app.state.sessions, expediteur)
        [notification] = await sms(app)
        assert (notification.etat, notification.tentatives) == ("a_envoyer", 1)
        assert notification.prochain_essai > datetime.now(UTC)
        assert "503" in (notification.derniere_erreur or "")

        assert await tour(app.state.sessions, expediteur) == 0  # pas avant le délai de reprise
        async with app.state.sessions() as session:
            await session.execute(update(Notification).values(prochain_essai=datetime.now(UTC)))
            await session.commit()
        await tour(app.state.sessions, expediteur)

    [notification] = await sms(app)
    assert (notification.etat, notification.identifiant_fournisseur) == (
        "envoyee",
        "https://api/sms/42",
    )
    jetons = [a for a in appels if a.url.path == "/oauth/v3/token"]
    envois = [a for a in appels if a.url.path != "/oauth/v3/token"]
    assert len(jetons) == 1  # jeton gardé entre deux envois
    assert envois[0].url.raw_path == b"/smsmessaging/v1/outbound/tel%3A%2B22370000000/requests"
    assert envois[0].headers["Authorization"] == "Bearer jeton-orange"
    corps = json.loads(envois[0].content)["outboundSMSMessageRequest"]
    assert (corps["address"], corps["senderName"]) == ("tel:+22376123456", "Bibou")


async def test_abandon_apres_cinq_echecs(app: FastAPI, client: AsyncClient) -> None:
    await commander(client, [await ligne(client, "affiche-a2")])

    class EnPanne:
        async def envoyer(self, destinataire: str, message: str) -> str | None:
            raise ConnectionError("réseau coupé")

    async with app.state.sessions() as session:
        await session.execute(update(Notification).values(tentatives=4))
        await session.commit()
    await tour(app.state.sessions, EnPanne())
    [notification] = await sms(app)
    assert (notification.etat, notification.tentatives) == ("echec", 5)


def test_limite_de_debit_par_adresse() -> None:
    limite = LimiteDebit("essai", nombre=3, secondes=60)
    application = SimpleNamespace(state=SimpleNamespace())

    def requete(adresse: str) -> Any:
        return SimpleNamespace(app=application, client=SimpleNamespace(host=adresse))

    for _ in range(3):
        limite(requete("41.73.10.1"))
    with pytest.raises(HTTPException) as refus:
        limite(requete("41.73.10.1"))
    assert refus.value.status_code == 429
    assert refus.value.headers == {"Retry-After": "60"}
    limite(requete("41.73.10.2"))  # une autre adresse n'est pas touchée
