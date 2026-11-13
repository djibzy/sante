from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from boutique.entretien import ANONYME
from boutique.models import Commande

from .aides import commander, fiche, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])


async def statut(client: AsyncClient, reference: str, nouveau: str) -> None:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": nouveau}, headers=ADMIN
    )
    assert reponse.status_code == 200, reponse.text


async def test_telecharger_puis_oublier(app: FastAPI, client: AsyncClient) -> None:
    awa = jeton(nom="Awa Traoré")
    kit = await ligne(client, "kit-hygiene")
    livree = (await commander(client, [kit], entetes=awa))["commande"]["reference"]
    for etape in ("confirmee", "prete", "livree"):
        await statut(client, livree, etape)
    annulee = (await commander(client, [kit], entetes=awa))["commande"]["reference"]
    await statut(client, annulee, "annulee")
    produit = await fiche(client, "kit-hygiene")
    avis = await client.post(
        f"/api/v1/mes-commandes/{livree}/avis",
        json={"produit_id": produit["id"], "note": 5, "texte": "Très pratique, je recommande."},
        headers=awa,
    )
    assert avis.status_code == 201
    [a_relire] = (await client.get("/api/v1/admin/avis", headers=ADMIN)).json()["elements"]
    await client.post(
        f"/api/v1/admin/avis/{a_relire['id']}/moderation",
        json={"decision": "publier"},
        headers=ADMIN,
    )
    assert (await fiche(client, "kit-hygiene"))["nombre_avis"] == 1

    export = await client.get("/api/v1/mes-donnees", headers=awa)
    assert export.status_code == 200
    donnees = export.json()
    assert sorted(c["reference"] for c in donnees["commandes"]) == sorted([livree, annulee])
    assert [(a["produit"], a["note"]) for a in donnees["avis"]] == [(produit["nom"], 5)]
    autre = (await client.get("/api/v1/mes-donnees", headers=jeton(nom="Autre"))).json()
    assert (autre["commandes"], autre["avis"]) == ([], [])

    # Une commande encore attendue empêche l'oubli : on la livre ou on l'annule d'abord.
    attendue = (await commander(client, [kit], entetes=awa))["commande"]["reference"]
    verification = (await client.get("/api/v1/mes-donnees/oubli", headers=awa)).json()
    assert verification == {"possible": False, "en_cours": [attendue]}
    refus = await client.post("/api/v1/mes-donnees/oubli", headers=awa)
    assert refus.status_code == 409 and attendue in refus.json()["detail"]
    annulation = await client.post(f"/api/v1/mes-commandes/{attendue}/annulation", headers=awa)
    assert annulation.status_code == 200

    oubli = await client.post("/api/v1/mes-donnees/oubli", headers=awa)
    assert oubli.status_code == 200, oubli.text
    assert oubli.json() == {
        "commandes_anonymisees": 2,
        "commandes_detachees": 1,
        "avis_effaces": 1,
    }
    assert (await client.get("/api/v1/mes-commandes", headers=awa)).json() == []
    kit_apres = await fiche(client, "kit-hygiene")
    assert (kit_apres["nombre_avis"], kit_apres["note_moyenne"]) == (0, None)
    async with app.state.sessions() as session:
        commandes = {c.numero: c for c in await session.scalars(select(Commande))}
    facturee = commandes[int(livree[3:])]
    assert (facturee.client_id, facturee.nom_client) == (None, "Aminata Traoré")  # facture : 10 ans
    assert commandes[int(annulee[3:])].telephone == ANONYME
    assert commandes[int(attendue[3:])].telephone == ANONYME
