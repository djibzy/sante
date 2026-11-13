"""Codes de réduction : au panier, à la commande (une fois par client, nombre maximal), gérés
par l'équipe."""

from datetime import timedelta
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from boutique.commandes.tarifs import aujourd_hui
from boutique.models import JournalAudit

from .aides import ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
BASE = "/api/v1/admin/codes-promo"


async def nouveau_code(client: AsyncClient, **champs: Any) -> Any:
    corps = {
        "code": "bienvenue",
        "libelle": "Bienvenue chez Bibou",
        "nature": "pourcentage",
        "valeur": 10,
        **champs,
    }
    reponse = await client.post(BASE, json=corps, headers=ADMIN)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


async def chiffrer(client: AsyncClient, lignes: list[dict[str, Any]], code: str | None) -> Any:
    reponse = await client.post(
        "/api/v1/panier/chiffrage", json={"lignes": lignes, "code_promo": code}
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def commander(
    client: AsyncClient, lignes: list[dict[str, Any]], code: str | None, telephone: str
) -> Any:
    return await client.post(
        "/api/v1/commandes",
        json={
            "client": {"nom": "Aminata Traoré", "telephone": telephone},
            "livraison": {"mode": "retrait"},
            "lignes": lignes,
            "code_promo": code,
        },
    )


async def codes(client: AsyncClient) -> dict[str, Any]:
    return {c["code"]: c for c in (await client.get(BASE, headers=ADMIN)).json()}


async def test_reduction_au_panier_et_a_la_commande(app: FastAPI, client: AsyncClient) -> None:
    code = await nouveau_code(client)
    assert (code["code"], code["debut"], code["utilisations"]) == (
        "BIENVENUE",
        str(aujourd_hui()),
        0,
    )
    kit = [await ligne(client, "kit-hygiene")]  # 7 500
    chiffrage = await chiffrer(client, kit, " bienvenue ")
    assert (chiffrage["remise"], chiffrage["total"], chiffrage["code_promo"]) == (
        750,
        6_750,
        "BIENVENUE",
    )
    assert (chiffrage["libelle_promo"], chiffrage["code_refuse"]) == ("Bienvenue chez Bibou", None)

    premiere = await commander(client, kit, "Bienvenue", "76 12 34 56")
    assert premiere.status_code == 201, premiere.text
    commande = premiere.json()["commande"]
    assert (commande["remise"], commande["total"], commande["code_promo"]) == (
        750,
        6_750,
        "BIENVENUE",
    )
    # Une fois par client : refusé au même numéro, accepté à un autre.
    refus = await commander(client, kit, "BIENVENUE", "+223 76 12 34 56")
    assert refus.status_code == 422
    assert refus.json()["detail"] == "Code « BIENVENUE » : Vous avez déjà utilisé ce code."
    assert (await commander(client, kit, "BIENVENUE", "66 12 34 57")).status_code == 201
    assert (await codes(client))["BIENVENUE"]["utilisations"] == 2
    assert (await codes(client))["BIENVENUE"]["remises"] == 1_500

    # Commande annulée : le code est rendu, le client peut le réutiliser.
    reference = commande["reference"]
    annulation = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": "annulee"}, headers=ADMIN
    )
    assert annulation.status_code == 200
    assert (await codes(client))["BIENVENUE"]["utilisations"] == 1
    assert (await commander(client, kit, "BIENVENUE", "76 12 34 56")).status_code == 201

    async with app.state.sessions() as session:
        details = list(
            await session.scalars(
                select(JournalAudit.details).where(JournalAudit.action == "commande.creee")
            )
        )
    assert {d["code_promo"] for d in details} == {"BIENVENUE"}


async def test_conditions_du_code(client: AsyncClient) -> None:
    kit = await ligne(client, "kit-hygiene")  # 7 500
    await nouveau_code(client, code="DIXMILLE", nature="montant", valeur=1_000, minimum=10_000)
    petit = await chiffrer(client, [kit], "dixmille")
    assert (petit["remise"], petit["total"], petit["code_promo"]) == (0, 7_500, None)
    assert petit["code_refuse"] == "Ce code demande 10 000 FCFA d'articles au moins."
    assert (await chiffrer(client, [{**kit, "quantite": 2}], "dixmille"))["remise"] == 1_000

    await nouveau_code(client, code="TOUT", nature="montant", valeur=50_000)
    assert (await chiffrer(client, [kit], "tout"))["total"] == 0  # jamais plus que les articles

    hier = aujourd_hui() - timedelta(days=1)
    await nouveau_code(client, code="PASSE", debut=str(hier - timedelta(days=9)), fin=str(hier))
    assert (await chiffrer(client, [kit], "passe"))["code_refuse"] == "Ce code a expiré."
    demain = aujourd_hui() + timedelta(days=1)
    futur = await nouveau_code(client, code="BIENTOT", debut=str(demain))
    attente = await chiffrer(client, [kit], "bientot")
    assert attente["code_refuse"] == f"Ce code est valable à partir du {demain:%d/%m/%Y}."
    await client.patch(f"{BASE}/{futur['id']}", json={"est_actif": False}, headers=ADMIN)
    assert (await chiffrer(client, [kit], "bientot"))["code_refuse"] == "Ce code n'existe pas."
    assert (await chiffrer(client, [kit], "inconnu"))["code_refuse"] == "Ce code n'existe pas."

    # Nombre maximal d'utilisations, tous clients confondus.
    await nouveau_code(client, code="UNIQUE", utilisations_max=1, une_fois_par_client=False)
    assert (await commander(client, [kit], "unique", "76 12 34 56")).status_code == 201
    epuise = await commander(client, [kit], "unique", "66 12 34 57")
    assert epuise.status_code == 422
    assert (
        epuise.json()["detail"]
        == "Code « UNIQUE » : Ce code a déjà servi autant de fois que prévu."
    )


async def test_gestion_des_codes(app: FastAPI, client: AsyncClient) -> None:
    code = await nouveau_code(client, code="ouverture-2027")
    assert code["code"] == "OUVERTURE-2027"
    doublon = await client.post(
        BASE,
        json={"code": "Ouverture-2027", "libelle": "Encore", "nature": "montant", "valeur": 500},
        headers=ADMIN,
    )
    assert doublon.status_code == 409
    for invalide in (
        {"nature": "pourcentage", "valeur": 95},
        {"nature": "montant", "valeur": 0},
        {"code": "avec espace"},
        {"debut": str(aujourd_hui()), "fin": str(aujourd_hui() - timedelta(days=1))},
    ):
        corps = {"code": "AUTRE", "libelle": "Autre", "nature": "pourcentage", "valeur": 5}
        reponse = await client.post(BASE, json={**corps, **invalide}, headers=ADMIN)
        assert reponse.status_code == 422, invalide

    fin = str(aujourd_hui() + timedelta(days=30))
    modifie = await client.patch(
        f"{BASE}/{code['id']}", json={"fin": fin, "libelle": "Ouverture de Bibou"}, headers=ADMIN
    )
    assert (modifie.json()["fin"], modifie.json()["libelle"]) == (fin, "Ouverture de Bibou")
    async with app.state.sessions() as session:
        actions = list(
            await session.scalars(
                select(JournalAudit.action).where(JournalAudit.objet_type == "code_promo")
            )
        )
    assert actions == ["code_promo.cree", "code_promo.modifie"]

    assert (await client.get(BASE)).status_code == 401
    assert (await client.get(BASE, headers=jeton(["boutique:atelier"]))).status_code == 403
