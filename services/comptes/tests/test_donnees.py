from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from comptes.models import JournalAudit, Utilisateur

from .conftest import MOT_DE_PASSE, entete, inscrire


async def test_telecharger_mes_donnees(client: AsyncClient) -> None:
    compte = await inscrire(client)
    assert (await client.get("/api/v1/auth/mes-donnees")).status_code == 401
    reponse = await client.get("/api/v1/auth/mes-donnees", headers=entete(compte))
    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees["service"] == "comptes"
    assert (donnees["compte"]["telephone"], donnees["compte"]["nom"]) == (
        "+22376123456",
        "Awa Traoré",
    )
    assert [c["objet"] for c in donnees["consentements"]] == ["conditions_utilisation"]
    assert "compte.cree" in [j["action"] for j in donnees["journal"]]
    assert len(donnees["sessions_ouvertes"]) == 1
    assert "mot_de_passe_hash" not in str(donnees)


async def test_supprimer_mon_compte(app: FastAPI, client: AsyncClient) -> None:
    compte = await inscrire(client)
    chemin = "/api/v1/auth/suppression"
    faux = await client.post(chemin, json={"mot_de_passe": "pas-le-bon"}, headers=entete(compte))
    assert faux.status_code == 400
    supprime = await client.post(
        chemin, json={"mot_de_passe": MOT_DE_PASSE}, headers=entete(compte)
    )
    assert supprime.status_code == 204
    assert (await client.get("/api/v1/auth/moi", headers=entete(compte))).status_code == 404
    connexion = await client.post(
        "/api/v1/auth/connexion", json={"telephone": "76 12 34 56", "mot_de_passe": MOT_DE_PASSE}
    )
    assert connexion.status_code == 401
    session_avant = await client.post(
        "/api/v1/auth/rafraichir", json={"jeton_rafraichissement": compte["jeton_rafraichissement"]}
    )
    assert session_avant.status_code == 401
    nouveau = await inscrire(client)  # le numéro est libre pour un nouveau compte
    assert nouveau["utilisateur"]["id"] != compte["utilisateur"]["id"]
    async with app.state.sessions() as session:
        ancien = await session.get(Utilisateur, compte["utilisateur"]["id"])
        actions = list(await session.scalars(select(JournalAudit.action)))
    assert ancien is not None
    assert (ancien.nom, ancien.est_actif, ancien.roles) == ("Compte supprimé", False, [])
    assert ancien.telephone.startswith("supprime-")
    assert "compte.supprime" in actions
