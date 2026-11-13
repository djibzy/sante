"""Lien de paiement envoyé à un proche : il voit le montant dû et paie, rien d'autre."""

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import select

from boutique.models import JournalAudit

from .conftest import jeton
from .test_paiements import PUBLIQUE, FauxCinetPay, commande


@pytest.fixture
def faux(app: FastAPI) -> FauxCinetPay:
    agregateur = FauxCinetPay()
    parametres = app.state.parametres
    parametres.paiement_mobile = "cinetpay"
    parametres.cinetpay_apikey = SecretStr("cle-api-test")
    parametres.cinetpay_site_id = "105900"
    parametres.url_publique = PUBLIQUE
    app.state.transport_paiement = httpx.MockTransport(agregateur)
    return agregateur


async def test_un_proche_paie_avec_le_lien(
    app: FastAPI, client: AsyncClient, faux: FauxCinetPay
) -> None:
    reference, cle, total = await commande(client)
    cree = await client.post(f"/api/v1/suivi/{reference}/lien-de-paiement", params={"cle": cle})
    assert cree.status_code == 201, cree.text
    lien = cree.json()
    assert lien["adresse"] == f"{PUBLIQUE}/payer/{reference}?cle={lien['cle']}"
    assert lien["cle"] != cle

    vue = await client.get(f"/api/v1/payer/{reference}", params={"cle": lien["cle"]})
    assert vue.status_code == 200, vue.text
    assert vue.json() == {
        "reference": reference,
        "statut_libelle": "Confirmée",
        "pour": "Aminata T.",  # ni nom complet, ni téléphone, ni adresse
        "articles": [{"libelle": "Kit hygiène et lavage des mains", "quantite": 1}],
        "total": total,
        "montant_paye": 0,
        "reste_a_payer": total,
        "acompte_restant": 0,
    }
    # Chaque clé n'ouvre que sa porte : le lien de paiement ne donne pas le suivi (annuler…).
    assert (await client.get(f"/api/v1/payer/{reference}", params={"cle": cle})).status_code == 404
    suivi = await client.get(f"/api/v1/suivi/{reference}", params={"cle": lien["cle"]})
    assert suivi.status_code == 404

    base = f"/api/v1/payer/{reference}/paiement-mobile"
    etat = (await client.get(base, params={"cle": lien["cle"]})).json()
    assert (etat["possible"], etat["montant"]) == (True, total)
    ouvert = await client.post(base, params={"cle": lien["cle"]})
    assert ouvert.status_code == 200, ouvert.text
    ouverture = faux.ouvertures()[-1]
    assert ouverture["return_url"] == f"{PUBLIQUE}/api/v1/paiements/retour/{reference}?vers=payer"
    faux.accepter(ouverture["transaction_id"], total)
    verifie = (await client.post(f"{base}/verification", params={"cle": lien["cle"]})).json()
    assert verifie["dernier"]["statut"] == "acceptee"
    client_voit = await client.get(f"/api/v1/suivi/{reference}", params={"cle": cle})
    assert client_voit.json()["montant_paye"] == total

    # Un nouveau lien remplace l'ancien… mais la commande est payée : plus rien à payer.
    refuse = await client.post(f"/api/v1/suivi/{reference}/lien-de-paiement", params={"cle": cle})
    assert refuse.status_code == 409
    assert refuse.json()["detail"] == "Cette commande est entièrement payée. Merci !"
    async with app.state.sessions() as session:
        actions = list(
            await session.scalars(
                select(JournalAudit.action).where(JournalAudit.objet_id == reference)
            )
        )
    assert actions.count("commande.lien_de_paiement") == 1


async def test_un_nouveau_lien_remplace_l_ancien(client: AsyncClient, faux: FauxCinetPay) -> None:
    aminata = jeton(nom="Aminata Traoré")
    reference, _, _ = await commande(client, entetes=aminata)
    chemin = f"/api/v1/mes-commandes/{reference}/lien-de-paiement"
    assert (await client.post(chemin, headers=jeton(nom="Autre client"))).status_code == 404
    premier = (await client.post(chemin, headers=aminata)).json()
    second = (await client.post(chemin, headers=aminata)).json()
    ancien = await client.get(f"/api/v1/payer/{reference}", params={"cle": premier["cle"]})
    assert ancien.status_code == 404
    nouveau = await client.get(f"/api/v1/payer/{reference}", params={"cle": second["cle"]})
    assert nouveau.status_code == 200


async def test_pas_de_lien_sans_paiement_possible(client: AsyncClient) -> None:
    reference, cle, _ = await commande(client, confirmer=False)
    chemin = f"/api/v1/suivi/{reference}/lien-de-paiement"
    eteint = await client.post(chemin, params={"cle": cle})  # paiement en ligne pas ouvert
    assert eteint.status_code == 409
    assert "pas encore ouvert" in eteint.json()["detail"]
    assert (await client.get(f"/api/v1/payer/{reference}")).status_code == 404


async def test_attente_de_confirmation(client: AsyncClient, faux: FauxCinetPay) -> None:
    reference, cle, _ = await commande(client, confirmer=False)
    reponse = await client.post(f"/api/v1/suivi/{reference}/lien-de-paiement", params={"cle": cle})
    assert reponse.status_code == 409
    assert reponse.json()["detail"].startswith("Le paiement en ligne s'ouvre dès que")


async def test_simulation_ramene_le_proche_sur_sa_page(app: FastAPI, client: AsyncClient) -> None:
    app.state.parametres.paiement_mobile = "simulation"
    reference, cle, total = await commande(client)
    lien = (
        await client.post(f"/api/v1/suivi/{reference}/lien-de-paiement", params={"cle": cle})
    ).json()
    base = f"/api/v1/payer/{reference}/paiement-mobile"
    ouvert = await client.post(base, params={"cle": lien["cle"]})
    assert ouvert.json() == {"adresse": f"/payer/{reference}?paiement=retour"}
    await client.post(f"{base}/verification", params={"cle": lien["cle"]})
    vue = await client.get(f"/api/v1/payer/{reference}", params={"cle": lien["cle"]})
    assert (vue.json()["montant_paye"], vue.json()["reste_a_payer"]) == (total, 0)


async def test_retour_vers_la_page_du_proche(client: AsyncClient, faux: FauxCinetPay) -> None:
    retour = await client.get("/api/v1/paiements/retour/BB-1001", params={"vers": "payer"})
    assert retour.status_code == 303
    assert retour.headers["location"] == f"{PUBLIQUE}/payer/BB-1001?paiement=retour"
    suivi = await client.get("/api/v1/paiements/retour/BB-1001")
    assert suivi.headers["location"] == f"{PUBLIQUE}/suivi/BB-1001?paiement=retour"
    ailleurs = await client.get("/api/v1/paiements/retour/BB-1001", params={"vers": "//evil"})
    assert ailleurs.status_code == 422
