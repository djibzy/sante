from httpx import AsyncClient

from boutique.donnees_demo import PRODUITS

from .aides import fiche, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])


async def test_reserve_a_l_equipe(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/admin/produits")).status_code == 401
    assert (await client.get("/api/v1/admin/produits", headers=jeton())).status_code == 403


async def test_produits_inactifs_visibles_par_l_equipe_seule(client: AsyncClient) -> None:
    affiche = await fiche(client, "affiche-a2")
    retrait = await client.patch(
        f"/api/v1/admin/produits/{affiche['id']}", json={"est_actif": False}, headers=ADMIN
    )
    assert retrait.status_code == 200
    assert (await client.get("/api/v1/produits/affiche-a2")).status_code == 404
    tous = (await client.get("/api/v1/admin/produits", headers=ADMIN)).json()
    retire = next(p for p in tous if p["slug"] == "affiche-a2")
    assert retire["est_actif"] is False and retire["poste_atelier"] == "impression"
    assert len(tous) == len(PRODUITS)
    kits = await client.get("/api/v1/admin/produits", params={"rayon": "kits"}, headers=ADMIN)
    assert {p["slug"] for p in kits.json()} == {
        "kit-hygiene",
        "kit-du-relais",
        "kit-premiers-secours",
    }
    recherche = await client.get("/api/v1/admin/produits", params={"q": "SABOTS"}, headers=ADMIN)
    assert [p["slug"] for p in recherche.json()] == ["sabots-de-travail"]
    gants = await client.get(
        f"/api/v1/admin/produits/{(await fiche(client, 'gants-steriles'))['id']}", headers=ADMIN
    )
    assert gants.json()["categorie_reglementaire"] == "pharmaceutique"
    rayons = (await client.get("/api/v1/admin/rayons", headers=ADMIN)).json()
    assert [r["slug"] for r in rayons][0] == "blouses-medicales"


async def test_variantes_prix_et_retrait(client: AsyncClient) -> None:
    sabots = await fiche(client, "sabots-de-travail")
    pointure = {v["taille"]: v["id"] for v in sabots["variantes"]}
    retiree = await client.patch(
        f"/api/v1/admin/variantes/{pointure['37']}", json={"est_active": False}, headers=ADMIN
    )
    assert (
        next(v for v in retiree.json()["variantes"] if v["taille"] == "37")["est_active"] is False
    )
    assert "37" not in [
        v["taille"] for v in (await fiche(client, "sabots-de-travail"))["variantes"]
    ]
    await client.patch(
        f"/api/v1/admin/variantes/{pointure['44']}", json={"prix": 9_500}, headers=ADMIN
    )
    corps = {"lignes": [await ligne(client, "sabots-de-travail", "44")]}
    assert (await client.post("/api/v1/panier/chiffrage", json=corps)).json()["total"] == 9_500


async def test_photos_du_produit(client: AsyncClient) -> None:
    blouse = await fiche(client, "blouse-medicale-brodee")
    photos = {
        "images": [
            {
                "url": "https://cdn.exemple.ml/blouse-face.jpg",
                "texte_alternatif": "Blouse blanche, de face",
            },
            {"url": "/photos/blouse-dos.jpg", "texte_alternatif": "Broderie au dos"},
        ]
    }
    reponse = await client.put(
        f"/api/v1/admin/produits/{blouse['id']}/images", json=photos, headers=ADMIN
    )
    assert reponse.status_code == 200
    publique = await fiche(client, "blouse-medicale-brodee")
    assert [i["url"] for i in publique["images"]] == [
        "https://cdn.exemple.ml/blouse-face.jpg",
        "/photos/blouse-dos.jpg",
    ]
    for adresse in ("javascript:alert(1)", "http://non-chiffre.ml/a.jpg", "https://a.ml/x y.jpg"):
        refus = await client.put(
            f"/api/v1/admin/produits/{blouse['id']}/images",
            json={"images": [{"url": adresse, "texte_alternatif": "Photo"}]},
            headers=ADMIN,
        )
        assert refus.status_code == 422, adresse
