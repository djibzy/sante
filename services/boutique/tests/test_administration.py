from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from boutique.models import JournalAudit

from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
NOUVEAU = {
    "slug": "gilet-relais",
    "nom": "Gilet du relais",
    "rayon_slug": "textiles-imprimes",
    "prix_public": 4000,
    "personnalisable": True,
    "variantes": [{"sku": "GILET-M", "libelle": "Taille M", "taille": "M"}],
}


async def test_administration_reservee(client: AsyncClient) -> None:
    sans_jeton = await client.post("/api/v1/admin/produits", json=NOUVEAU)
    assert sans_jeton.status_code == 401
    sans_role = await client.post("/api/v1/admin/produits", json=NOUVEAU, headers=jeton())
    assert sans_role.status_code == 403
    autre_role = await client.post(
        "/api/v1/admin/produits", json=NOUVEAU, headers=jeton(["studio:editeur"])
    )
    assert autre_role.status_code == 403


async def test_creer_un_produit_et_le_retrouver(client: AsyncClient, app: FastAPI) -> None:
    reponse = await client.post("/api/v1/admin/produits", json=NOUVEAU, headers=ADMIN)

    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["variantes"][0]["prix"] == 4000
    fiche = await client.get("/api/v1/produits/gilet-relais")
    assert fiche.status_code == 200
    async with app.state.sessions() as session:
        actions = (await session.execute(select(JournalAudit.action))).scalars().all()
    assert actions == ["produit.cree"]


async def test_un_administrateur_general_peut_tout_faire(client: AsyncClient) -> None:
    reponse = await client.post("/api/v1/admin/produits", json=NOUVEAU, headers=jeton(["admin"]))
    assert reponse.status_code == 201


async def test_prix_obligatoire_pour_un_produit_libre(client: AsyncClient) -> None:
    sans_prix = {**NOUVEAU, "prix_public": None, "slug": "sans-prix", "variantes": []}
    reponse = await client.post("/api/v1/admin/produits", json=sans_prix, headers=ADMIN)
    assert reponse.status_code == 422


async def test_slug_deja_utilise(client: AsyncClient) -> None:
    doublon = {**NOUVEAU, "slug": "calot-brode", "variantes": []}
    reponse = await client.post("/api/v1/admin/produits", json=doublon, headers=ADMIN)
    assert reponse.status_code == 409


async def test_rayon_inconnu(client: AsyncClient) -> None:
    reponse = await client.post(
        "/api/v1/admin/produits", json={**NOUVEAU, "rayon_slug": "inconnu"}, headers=ADMIN
    )
    assert reponse.status_code == 422


async def test_desactiver_un_produit_le_retire_du_catalogue(client: AsyncClient) -> None:
    fiche = (await client.get("/api/v1/produits/calot-brode")).json()
    reponse = await client.patch(
        f"/api/v1/admin/produits/{fiche['id']}", json={"est_actif": False}, headers=ADMIN
    )
    assert reponse.status_code == 200
    assert (await client.get("/api/v1/produits/calot-brode")).status_code == 404


async def test_ajouter_une_variante(client: AsyncClient) -> None:
    fiche = (await client.get("/api/v1/produits/calot-brode")).json()
    reponse = await client.post(
        f"/api/v1/admin/produits/{fiche['id']}/variantes",
        json={"sku": "CALOT-BLEU", "libelle": "Bleu", "couleur": "Bleu", "prix": 3500},
        headers=ADMIN,
    )
    assert reponse.status_code == 201
    assert [v["prix"] for v in reponse.json()["variantes"]] == [3500]

    doublon = await client.post(
        f"/api/v1/admin/produits/{fiche['id']}/variantes",
        json={"sku": "CALOT-BLEU", "libelle": "Bleu"},
        headers=ADMIN,
    )
    assert doublon.status_code == 409


async def test_creer_et_modifier_un_rayon(client: AsyncClient) -> None:
    cree = await client.post(
        "/api/v1/admin/rayons", json={"slug": "librairie", "nom": "Librairie"}, headers=ADMIN
    )
    assert cree.status_code == 201
    modifie = await client.patch(
        f"/api/v1/admin/rayons/{cree.json()['id']}",
        json={"est_actif": False},
        headers=ADMIN,
    )
    assert modifie.status_code == 200
    slugs = [r["slug"] for r in (await client.get("/api/v1/rayons")).json()]
    assert "librairie" not in slugs
