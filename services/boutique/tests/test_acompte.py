"""Acompte des articles faits à la demande : demandé à la confirmation, il lance la fabrication
et reste acquis si le client annule ensuite ; tout est rendu si l'annulation vient de la
boutique."""

from datetime import date
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select

from boutique.commandes.acompte import calculer
from boutique.models import Notification, OrdreFabrication

from .aides import commander, fiche, ligne
from .conftest import jeton
from .test_notifications import GSM7

ADMIN = jeton(["boutique:admin"])
CLIENTE = "+22376123456"


@pytest.fixture(autouse=True)
def avec_acompte(app: FastAPI) -> None:
    app.state.parametres.acompte_pourcent = 50


async def statut(client: AsyncClient, reference: str, nouveau: str, **autres: Any) -> Any:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut",
        json={"statut": nouveau, **autres},
        headers=ADMIN,
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def encaisser(client: AsyncClient, reference: str, montant: int) -> Any:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": montant, "moyen": "especes"},
        headers=ADMIN,
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def sms(app: FastAPI, destinataire: str = CLIENTE) -> list[str]:
    async with app.state.sessions() as session:
        return list(
            await session.scalars(
                select(Notification.message)
                .where(Notification.destinataire == destinataire)
                .order_by(Notification.cree_le, Notification.id)
            )
        )


async def ordres(app: FastAPI) -> int:
    async with app.state.sessions() as session:
        return await session.scalar(select(func.count()).select_from(OrdreFabrication)) or 0


def notes(commande: dict[str, Any]) -> list[str]:
    return [e["note"] for e in commande["historique_complet"]]


def test_calcul_arrondi_a_la_centaine() -> None:
    assert calculer(12_500, 12_500, 50) == 6_300  # 6 250, arrondi à la centaine supérieure
    assert calculer(15_000, 22_500, 50) == 7_500
    assert calculer(0, 7_500, 50) == 0
    assert calculer(12_500, 12_500, 0) == 0  # acompte désactivé
    assert calculer(12_500, 5_000, 100) == 5_000  # jamais plus que le total


async def chiffrer(client: AsyncClient, lignes: list[dict[str, Any]]) -> Any:
    reponse = await client.post("/api/v1/panier/chiffrage", json={"lignes": lignes})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def test_articles_faits_a_la_demande(app: FastAPI, client: AsyncClient) -> None:
    # Brodé ou imprimé : toujours fait à la demande. Kit assemblé à partir du stock : jamais.
    blouse = await fiche(client, "blouse-medicale-brodee")
    assert (blouse["acompte_pourcent"], blouse["acompte_toujours"]) == (50, True)
    kit = await fiche(client, "kit-hygiene")
    assert (kit["acompte_pourcent"], kit["acompte_toujours"]) == (None, False)

    lignes = [
        await ligne(client, "blouse-medicale-brodee", "M"),  # 12 500
        await ligne(client, "kit-hygiene"),  # 7 500
        await ligne(client, "affiche-a2", quantite=2),  # 3 000
    ]
    chiffrage = await chiffrer(client, lignes)
    assert [ligne["a_la_demande"] for ligne in chiffrage["lignes"]] == [True, False, True]
    assert (chiffrage["total"], chiffrage["acompte"]) == (23_000, 7_800)  # 7 750 arrondi

    creee = (await commander(client, lignes))["commande"]
    assert (creee["acompte"], creee["acompte_restant"], creee["acompte_garde"]) == (7_800, 7_800, 0)
    sans = (await commander(client, [lignes[1]], telephone="66 12 34 57"))["commande"]
    assert sans["acompte"] == 0
    assert (await statut(client, sans["reference"], "confirmee"))["statut"] == "confirmee"

    conditions = await client.get("/api/v1/conditions-de-vente")
    assert conditions.json() == {"acompte_pourcent": 50, "validite_devis_jours": 30}

    # Réglage de la boutique : la broderie ne demande d'acompte que si elle est personnalisée.
    app.state.parametres.acompte_postes = ["impression"]
    blouse = await fiche(client, "blouse-medicale-brodee")
    assert (blouse["acompte_pourcent"], blouse["acompte_toujours"]) == (50, False)
    simple = await chiffrer(client, [lignes[0]])
    assert (simple["lignes"][0]["a_la_demande"], simple["acompte"]) == (False, 0)
    brodee = await ligne(client, "blouse-medicale-brodee", "M", personnalisation="A. Traoré")
    assert (await chiffrer(client, [brodee]))["acompte"] == 6_300


async def test_la_fabrication_attend_l_acompte(app: FastAPI, client: AsyncClient) -> None:
    brodee = await ligne(client, "blouse-medicale-brodee", "M", personnalisation="A. Traoré")
    creee = await commander(client, [brodee])
    reference = creee["commande"]["reference"]
    assert creee["commande"]["acompte"] == 6_300

    attente = await statut(client, reference, "confirmee")
    assert (attente["statut"], attente["date_promise"]) == ("acompte_attendu", None)
    assert attente["statut_libelle"] == "En attente de l'acompte"
    assert attente["passages_possibles"] == ["confirmee", "annulee"]
    assert attente["peut_annuler"] is True
    assert await ordres(app) == 0  # rien n'est fabriqué avant l'acompte

    partiel = await encaisser(client, reference, 3_000)
    assert (partiel["statut"], partiel["acompte_restant"]) == ("acompte_attendu", 3_300)
    assert await ordres(app) == 0
    lancee = await encaisser(client, reference, 3_300)
    assert (lancee["statut"], lancee["acompte_restant"]) == ("confirmee", 0)
    assert lancee["date_promise"] is not None
    assert "Acompte reçu : fabrication lancée" in notes(lancee)
    assert await ordres(app) == 1

    prete_vers = date.fromisoformat(lancee["date_promise"]).strftime("%d/%m")
    assert (await sms(app))[1:] == [
        f"Bibou : commande {reference} confirmée. Acompte à régler pour lancer la fabrication : "
        "6 300 FCFA (non remboursable), en ligne ou à la boutique.",
        # Reçu écrit de l'argent remis à la boutique ; le second versement lance la fabrication.
        f"Bibou : paiement de 3 000 FCFA (espèces) recu pour la commande {reference}. "
        "Reste à payer : 9 500 FCFA.",
        f"Bibou : acompte recu, la fabrication de la commande {reference} commence, prete vers "
        f"le {prete_vers}.",
    ]
    assert all(set(message) <= GSM7 for message in await sms(app))
    tableau = await client.get("/api/v1/admin/tableau-de-bord", headers=ADMIN)
    assert tableau.json()["alertes"]["acomptes_attendus"] == 0


async def test_l_equipe_peut_lancer_sans_attendre(app: FastAPI, client: AsyncClient) -> None:
    creee = await commander(client, [await ligne(client, "affiche-a2", quantite=10)])
    reference = creee["commande"]["reference"]
    await statut(client, reference, "confirmee")
    tableau = await client.get("/api/v1/admin/tableau-de-bord", headers=ADMIN)
    assert tableau.json()["alertes"]["acomptes_attendus"] == 1

    lancee = await statut(client, reference, "confirmee")  # client connu, commande urgente
    assert (lancee["statut"], lancee["acompte_restant"]) == ("confirmee", 7_500)
    assert "Fabrication lancée sans attendre l'acompte" in notes(lancee)
    assert await ordres(app) == 1
    assert (await sms(app))[-1].startswith(f"Bibou : commande {reference} confirmée, prete vers")


async def test_annulation_acompte_garde_ou_rendu(app: FastAPI, client: AsyncClient) -> None:
    blouse = await ligne(client, "blouse-medicale-brodee", "M")
    reference = (await commander(client, [blouse]))["commande"]["reference"]
    await statut(client, reference, "confirmee")
    await encaisser(client, reference, 10_000)  # l'acompte (6 300) et une avance de 3 700
    annulee = await statut(client, reference, "annulee", note="La cliente change de service")
    assert (annulee["statut"], annulee["acompte_garde"]) == ("annulee", 6_300)
    assert "Acompte gardé (non remboursable) : 6 300 FCFA. À rendre au client : 3 700 FCFA." in (
        notes(annulee)
    )
    assert (await sms(app))[-1] == (
        f"Bibou : commande {reference} annulée. L'acompte de 6 300 FCFA reste acquis (article "
        "fait à la demande). Nous vous rendons 3 700 FCFA."
    )

    # Annulation de la boutique (tissu en rupture) : tout est rendu au client.
    autre = (await commander(client, [blouse], telephone="66 12 34 57"))["commande"]["reference"]
    await statut(client, autre, "confirmee")
    await encaisser(client, autre, 6_300)
    rendue = await statut(client, autre, "annulee", garder_acompte=False, note="Tissu en rupture")
    assert rendue["acompte_garde"] == 0
    assert "À rendre au client : 6 300 FCFA." in notes(rendue)
    assert (await sms(app, "+22366123457"))[-1] == (
        f"Bibou : commande {autre} annulée. Nous vous rendons 6 300 FCFA."
    )


async def test_le_client_annule_en_attente_de_l_acompte(app: FastAPI, client: AsyncClient) -> None:
    creee = await commander(client, [await ligne(client, "blouse-medicale-brodee", "L")])
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    await statut(client, reference, "confirmee")
    await encaisser(client, reference, 2_000)  # une partie de l'acompte, à la boutique
    annulee = await client.post(f"/api/v1/suivi/{reference}/annulation", params={"cle": cle})
    assert annulee.status_code == 200, annulee.text
    assert (annulee.json()["statut"], annulee.json()["acompte_garde"]) == ("annulee", 2_000)
    assert (await sms(app))[-1] == (
        f"Bibou : commande {reference} annulée. L'acompte de 2 000 FCFA reste acquis (article "
        "fait à la demande). Une question ? Appelez-nous."
    )


async def test_acompte_paye_en_ligne(app: FastAPI, client: AsyncClient) -> None:
    app.state.parametres.paiement_mobile = "simulation"
    creee = await commander(client, [await ligne(client, "affiche-a2", quantite=10)])
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    suivi = f"/api/v1/suivi/{reference}"
    attente = (await client.get(f"{suivi}/paiement-mobile", params={"cle": cle})).json()
    assert (attente["possible"], attente["acompte"]) == (False, None)  # pas avant la confirmation
    await statut(client, reference, "confirmee")
    ouvert = (await client.get(f"{suivi}/paiement-mobile", params={"cle": cle})).json()
    assert (ouvert["possible"], ouvert["montant"], ouvert["acompte"]) == (True, 15_000, 7_500)

    paye = await client.post(
        f"{suivi}/paiement-mobile", params={"cle": cle}, json={"objet": "acompte"}
    )
    assert paye.status_code == 200, paye.text
    await client.post(f"{suivi}/paiement-mobile/verification", params={"cle": cle})
    commande = (await client.get(suivi, params={"cle": cle})).json()
    assert (commande["statut"], commande["montant_paye"], commande["reste_a_payer"]) == (
        "confirmee",
        7_500,
        7_500,
    )
    assert (await sms(app))[-1].startswith("Bibou : acompte recu, la fabrication de la commande")

    # L'acompte payé, seul le solde se paie encore en ligne.
    solde = (await client.get(f"{suivi}/paiement-mobile", params={"cle": cle})).json()
    assert (solde["montant"], solde["acompte"]) == (7_500, None)
    refus = await client.post(
        f"{suivi}/paiement-mobile", params={"cle": cle}, json={"objet": "acompte"}
    )
    assert refus.status_code == 409


async def test_devis_accepte_attend_l_acompte(client: AsyncClient) -> None:
    affiches = await ligne(client, "affiche-a2", quantite=40)
    demande = await client.post(
        "/api/v1/devis",
        json={
            "etablissement": "CSCom de Banconi",
            "client": {"nom": "Dr Oumar Sangaré", "telephone": "66 44 22 11"},
            "lignes": [affiches],
        },
    )
    reference, cle = demande.json()["commande"]["reference"], demande.json()["cle_suivi"]
    pose = {"libelle": "Pose des affiches dans le quartier", "quantite": 1, "prix_unitaire": 5_000}
    emis = await client.put(
        f"/api/v1/admin/commandes/{reference}/devis",
        json={"lignes": [affiches, pose]},
        headers=ADMIN,
    )
    assert emis.status_code == 200, emis.text
    assert (emis.json()["total"], emis.json()["acompte"]) == (65_000, 30_000)  # sans la pose
    accepte = await client.post(f"/api/v1/suivi/{reference}/acceptation", params={"cle": cle})
    assert accepte.status_code == 200, accepte.text
    assert (accepte.json()["statut"], accepte.json()["acompte_restant"]) == (
        "acompte_attendu",
        30_000,
    )
