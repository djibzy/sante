import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import select

from boutique.commandes.cycle import Moyen
from boutique.config import ParametresBoutique
from boutique.models import JournalAudit, Notification
from boutique.paiements import fournisseurs
from boutique.paiements.fournisseurs import CinetPay
from boutique.paiements.service import moyen_de, rapprocher

from .aides import commander, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
PUBLIQUE = "https://boutique.exemple.ml"


class FauxCinetPay:
    """Joue l'API de CinetPay : ouverture des paiements, puis statut à la vérification."""

    def __init__(self) -> None:
        self.requetes: list[tuple[str, dict[str, Any]]] = []
        self.statuts: dict[str, dict[str, Any]] = {}
        self.ouverture: dict[str, Any] = {"code": "201", "message": "CREATED"}
        self.panne = False

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        if self.panne:
            raise httpx.ConnectError("injoignable", request=requete)
        assert requete.headers["user-agent"].startswith("Bibou/")
        corps = json.loads(requete.content)
        self.requetes.append((requete.url.path, corps))
        if requete.url.path == "/v2/payment":
            if self.ouverture["code"] != "201":
                return httpx.Response(200, json=self.ouverture)
            page = f"https://checkout.cinetpay.com/payment/{corps['transaction_id']}"
            return httpx.Response(
                200, json={**self.ouverture, "data": {"payment_token": "j", "payment_url": page}}
            )
        attente = {
            "code": "662",
            "message": "WAITING_CUSTOMER_PAYMENT",
            "data": {"status": "WAITING_FOR_CUSTOMER", "amount": "0", "currency": "XOF"},
        }
        return httpx.Response(200, json=self.statuts.get(corps["transaction_id"], attente))

    def accepter(self, transaction_id: str, montant: int, methode: str = "OMML") -> None:
        self.statuts[transaction_id] = {
            "code": "00",
            "message": "SUCCES",
            "data": {
                "amount": str(montant),
                "currency": "XOF",
                "status": "ACCEPTED",
                "payment_method": methode,
                "operator_id": "MP261112.2301.A71234",
                "payment_date": "2026-11-12 23:01:00",
            },
        }

    def refuser(self, transaction_id: str) -> None:
        self.statuts[transaction_id] = {
            "code": "627",
            "message": "TRANSACTION_CANCEL",
            "data": {"status": "REFUSED", "amount": "8500", "currency": "XOF"},
        }

    def ouvertures(self) -> list[dict[str, Any]]:
        return [corps for chemin, corps in self.requetes if chemin == "/v2/payment"]

    def verifications(self) -> int:
        return sum(chemin == "/v2/payment/check" for chemin, _ in self.requetes)


@pytest.fixture
def cinetpay(app: FastAPI) -> FauxCinetPay:
    faux = FauxCinetPay()
    parametres = app.state.parametres
    parametres.paiement_mobile = "cinetpay"
    parametres.cinetpay_apikey = SecretStr("cle-api-test")
    parametres.cinetpay_site_id = "105900"
    parametres.url_publique = PUBLIQUE
    app.state.transport_paiement = httpx.MockTransport(faux)
    return faux


async def commande(
    client: AsyncClient, confirmer: bool = True, entetes: dict[str, str] | None = None
) -> tuple[str, str, int]:
    creee = await commander(client, [await ligne(client, "kit-hygiene")], entetes=entetes)
    reference = creee["commande"]["reference"]
    if confirmer:
        reponse = await client.post(
            f"/api/v1/admin/commandes/{reference}/statut",
            json={"statut": "confirmee"},
            headers=ADMIN,
        )
        assert reponse.status_code == 200, reponse.text
    return reference, creee["cle_suivi"], creee["commande"]["total"]


async def payer(client: AsyncClient, reference: str, cle: str) -> httpx.Response:
    return await client.post(f"/api/v1/suivi/{reference}/paiement-mobile", params={"cle": cle})


async def etat(client: AsyncClient, reference: str, cle: str) -> dict[str, Any]:
    reponse = await client.get(f"/api/v1/suivi/{reference}/paiement-mobile", params={"cle": cle})
    assert reponse.status_code == 200, reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees


async def notifier(client: AsyncClient, transaction_id: str, site: str = "105900") -> None:
    # Montant et statut faux dans la notification : ils ne doivent jamais être lus.
    reponse = await client.post(
        "/api/v1/paiements/cinetpay/notification",
        data={
            "cpm_site_id": site,
            "cpm_trans_id": transaction_id,
            "cpm_amount": "5",
            "cpm_error_message": "SUCCES",
        },
    )
    assert reponse.status_code == 200


async def suivi(client: AsyncClient, reference: str, cle: str) -> dict[str, Any]:
    donnees: dict[str, Any] = (
        await client.get(f"/api/v1/suivi/{reference}", params={"cle": cle})
    ).json()
    return donnees


async def gestion(client: AsyncClient, reference: str) -> dict[str, Any]:
    donnees: dict[str, Any] = (
        await client.get(f"/api/v1/admin/commandes/{reference}", headers=ADMIN)
    ).json()
    return donnees


async def test_eteint_par_defaut(client: AsyncClient) -> None:
    disponibilite = await client.get("/api/v1/paiements/disponibilite")
    assert disponibilite.json() == {"disponible": False, "moyens": []}
    reference, cle, total = await commande(client)
    assert await etat(client, reference, cle) == {
        "disponible": False,
        "possible": False,
        "montant": total,
        "raison": None,
        "moyens": [],
        "dernier": None,
    }
    refus = await payer(client, reference, cle)
    assert refus.status_code == 409
    assert "à la livraison" in refus.json()["detail"]


async def test_seulement_une_fois_la_commande_confirmee(
    client: AsyncClient, cinetpay: FauxCinetPay
) -> None:
    disponibilite = (await client.get("/api/v1/paiements/disponibilite")).json()
    assert disponibilite == {"disponible": True, "moyens": ["Orange Money", "Moov Money"]}
    reference, cle, _ = await commande(client, confirmer=False)
    attente = await etat(client, reference, cle)
    assert (attente["disponible"], attente["possible"]) == (True, False)
    assert "confirmé votre commande" in attente["raison"]
    assert (await payer(client, reference, cle)).status_code == 409
    assert cinetpay.requetes == []
    inconnue = await client.get("/api/v1/suivi/BB-1/paiement-mobile", params={"cle": "x" * 24})
    assert inconnue.status_code == 404


async def test_paiement_credite_une_seule_fois(
    app: FastAPI, client: AsyncClient, cinetpay: FauxCinetPay
) -> None:
    reference, cle, total = await commande(client)
    ouvert = await payer(client, reference, cle)
    assert ouvert.status_code == 200, ouvert.text
    [demande] = cinetpay.ouvertures()
    transaction = demande["transaction_id"]
    assert ouvert.json() == {"adresse": f"https://checkout.cinetpay.com/payment/{transaction}"}
    assert demande == {
        "apikey": "cle-api-test",
        "site_id": "105900",
        "transaction_id": transaction,
        "amount": total,
        "currency": "XOF",
        "description": f"Commande {reference} Bibou",
        "notify_url": f"{PUBLIQUE}/api/v1/paiements/cinetpay/notification",
        "return_url": f"{PUBLIQUE}/api/v1/paiements/retour/{reference}",
        "channels": "MOBILE_MONEY",
        "lang": "fr",
        "metadata": reference,
    }  # ni nom ni téléphone du client
    assert not set("#/$_&") & set(demande["description"])
    assert (await etat(client, reference, cle))["dernier"]["statut"] == "en_cours"

    # Le client n'a pas encore validé sur son téléphone : rien n'est crédité.
    await notifier(client, transaction)
    assert (await suivi(client, reference, cle))["montant_paye"] == 0
    assert (await etat(client, reference, cle))["dernier"]["statut"] == "en_cours"

    cinetpay.accepter(transaction, total)
    await notifier(client, transaction)
    await notifier(client, transaction)  # CinetPay peut notifier plusieurs fois
    assert cinetpay.verifications() == 2  # une fois traitée, la tentative n'est plus relue
    commande_suivie = await suivi(client, reference, cle)
    assert (commande_suivie["montant_paye"], commande_suivie["reste_a_payer"]) == (total, 0)
    [paiement] = (await gestion(client, reference))["paiements"]
    assert (paiement["montant"], paiement["moyen"]) == (total, "orange_money")
    assert (paiement["reference"], paiement["encaisse_par"]) == ("MP261112.2301.A71234", None)

    fin = await etat(client, reference, cle)
    assert (fin["possible"], fin["dernier"]["statut"]) == (False, "acceptee")
    assert "entièrement payée" in fin["raison"]
    assert (await payer(client, reference, cle)).status_code == 409

    async with app.state.sessions() as session:
        messages = list(
            await session.scalars(select(Notification.message).order_by(Notification.cree_le))
        )
        actions = list(await session.scalars(select(JournalAudit.action)))
    assert messages[-1] == (
        f"Bibou : paiement de 7 500 FCFA recu pour la commande {reference}. "
        "Commande entièrement payée, merci !"
    )
    assert actions.count("paiement.ouvert") == 1
    assert actions.count("paiement.en_ligne") == 1


async def test_refus_puis_montant_suspect(client: AsyncClient, cinetpay: FauxCinetPay) -> None:
    reference, cle, total = await commande(client)
    await payer(client, reference, cle)
    cinetpay.refuser(cinetpay.ouvertures()[-1]["transaction_id"])
    await notifier(client, cinetpay.ouvertures()[-1]["transaction_id"])
    refus = await etat(client, reference, cle)
    assert (refus["possible"], refus["dernier"]["statut"]) == (True, "refusee")

    await payer(client, reference, cle)
    transaction = cinetpay.ouvertures()[-1]["transaction_id"]
    cinetpay.accepter(transaction, total - 100)  # pas le montant demandé
    await notifier(client, transaction)
    assert (await etat(client, reference, cle))["dernier"]["statut"] == "a_verifier"
    assert (await suivi(client, reference, cle))["montant_paye"] == 0
    equipe = await gestion(client, reference)
    assert equipe["paiements"] == []
    [note] = [e for e in equipe["historique_complet"] if "à vérifier" in e["note"]]
    assert note["visible_client"] is False
    client_voit = (await suivi(client, reference, cle))["historique"]
    assert all("vérifier" not in e["note"] for e in client_voit)


async def test_retour_du_client_sans_notification(
    client: AsyncClient, cinetpay: FauxCinetPay
) -> None:
    reference, cle, total = await commande(client)
    await payer(client, reference, cle)
    cinetpay.accepter(cinetpay.ouvertures()[-1]["transaction_id"], total, methode="MOOVML")
    for methode in ("GET", "POST"):  # CinetPay renvoie parfois le client en POST
        retour = await client.request(methode, f"/api/v1/paiements/retour/{reference.lower()}")
        assert retour.status_code == 303
        assert retour.headers["location"] == f"{PUBLIQUE}/suivi/{reference}?paiement=retour"
    assert (await client.get("/api/v1/paiements/retour/exemple.com")).status_code == 404

    verifie = await client.post(
        f"/api/v1/suivi/{reference}/paiement-mobile/verification", params={"cle": cle}
    )
    assert verifie.status_code == 200
    assert verifie.json()["dernier"]["statut"] == "acceptee"
    [paiement] = (await gestion(client, reference))["paiements"]
    assert paiement["moyen"] == "moov_money"


async def test_agregateur_injoignable(client: AsyncClient, cinetpay: FauxCinetPay) -> None:
    reference, cle, _ = await commande(client)
    cinetpay.panne = True
    panne = await payer(client, reference, cle)
    assert panne.status_code == 502
    assert "à la livraison" in panne.json()["detail"]
    cinetpay.panne = False
    cinetpay.ouverture = {"code": "608", "message": "MINIMUM_REQUIRED_FIELDS"}
    assert (await payer(client, reference, cle)).status_code == 502
    assert (await etat(client, reference, cle))["dernier"] is None  # rien n'a été gardé


async def test_rapprochement_des_notifications_perdues(
    app: FastAPI, client: AsyncClient, cinetpay: FauxCinetPay
) -> None:
    reference, cle, total = await commande(client)
    await payer(client, reference, cle)
    cinetpay.accepter(cinetpay.ouvertures()[-1]["transaction_id"], total)
    plus_tard = datetime.now(UTC) + timedelta(minutes=5)
    async with httpx.AsyncClient(transport=httpx.MockTransport(cinetpay)) as http:
        agregateur = CinetPay(app.state.parametres, http)
        assert await rapprocher(app.state.sessions, agregateur, plus_tard + timedelta(days=1)) == 0
        assert await rapprocher(app.state.sessions, agregateur, plus_tard) == 1
        assert await rapprocher(app.state.sessions, agregateur, plus_tard) == 0
    assert (await suivi(client, reference, cle))["reste_a_payer"] == 0


async def test_compte_client_et_trop_percu(client: AsyncClient, cinetpay: FauxCinetPay) -> None:
    aminata = jeton(nom="Aminata Traoré")
    reference, _, total = await commande(client, entetes=aminata)
    base = f"/api/v1/mes-commandes/{reference}/paiement-mobile"
    assert (await client.post(base, headers=jeton(nom="Autre client"))).status_code == 404
    # Deux onglets ouverts, deux paiements validés : l'argent reçu est toujours enregistré.
    for _ in range(2):
        assert (await client.post(base, headers=aminata)).status_code == 200
        cinetpay.accepter(cinetpay.ouvertures()[-1]["transaction_id"], total)
    verifie = await client.post(f"{base}/verification", headers=aminata)
    assert verifie.json()["dernier"]["statut"] == "acceptee"
    equipe = await gestion(client, reference)
    assert (equipe["montant_paye"], equipe["reste_a_payer"]) == (2 * total, 0)
    assert any("Trop-perçu de 7 500 FCFA" in e["note"] for e in equipe["historique_complet"])


async def test_tentatives_limitees(client: AsyncClient, cinetpay: FauxCinetPay) -> None:
    reference, cle, _ = await commande(client)
    for _ in range(10):
        assert (await payer(client, reference, cle)).status_code == 200
    assert (await payer(client, reference, cle)).status_code == 429


async def test_notification_d_un_autre_site_ignoree(
    client: AsyncClient, cinetpay: FauxCinetPay
) -> None:
    reference, cle, total = await commande(client)
    await payer(client, reference, cle)
    transaction = cinetpay.ouvertures()[-1]["transaction_id"]
    cinetpay.accepter(transaction, total)
    await notifier(client, transaction, site="999999")
    await notifier(client, "BB1T0000")  # tentative inconnue
    assert cinetpay.verifications() == 0  # ni l'une ni l'autre ne déclenche de relecture
    assert (await suivi(client, reference, cle))["montant_paye"] == 0
    assert (await client.get("/api/v1/paiements/cinetpay/notification")).status_code == 200


async def test_montant_hors_multiple_de_cinq(client: AsyncClient, cinetpay: FauxCinetPay) -> None:
    reference, cle, total = await commande(client)
    encaissement = f"/api/v1/admin/commandes/{reference}/paiements"
    reserve = await client.post(
        encaissement, json={"montant": 3, "moyen": "mobile_money"}, headers=ADMIN
    )
    assert reserve.status_code == 422  # réservé aux paiements faits en ligne
    acompte = await client.post(
        encaissement, json={"montant": 3, "moyen": "especes"}, headers=ADMIN
    )
    assert acompte.status_code == 200
    reste = await etat(client, reference, cle)
    assert (reste["possible"], reste["montant"]) == (False, total - 3)
    assert "à la livraison" in reste["raison"]


async def test_simulation_pour_les_essais(app: FastAPI, client: AsyncClient) -> None:
    app.state.parametres.paiement_mobile = "simulation"
    reference, cle, total = await commande(client)
    ouvert = await payer(client, reference, cle)
    assert ouvert.json() == {"adresse": f"/suivi/{reference}?paiement=retour"}
    await client.post(
        f"/api/v1/suivi/{reference}/paiement-mobile/verification", params={"cle": cle}
    )
    assert (await suivi(client, reference, cle))["montant_paye"] == total

    production = ParametresBoutique(environnement="production", paiement_mobile="simulation")
    assert fournisseurs.configuration_incomplete(production) is not None
    assert not fournisseurs.est_ouvert(production)
    incomplet = ParametresBoutique(paiement_mobile="cinetpay", cinetpay_site_id="105900")
    manque = fournisseurs.configuration_incomplete(incomplet) or ""
    assert "BOUTIQUE_CINETPAY_APIKEY" in manque and "BOUTIQUE_URL_PUBLIQUE" in manque


def test_moyens_reconnus() -> None:
    assert moyen_de("OM") == moyen_de("OMML") == Moyen.ORANGE_MONEY
    assert moyen_de("MOOVML") == moyen_de("FLOOZ") == Moyen.MOOV_MONEY
    assert moyen_de("MOMO") == moyen_de(None) == Moyen.MOBILE_MONEY
