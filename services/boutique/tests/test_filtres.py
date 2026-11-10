from typing import Any

from httpx import AsyncClient

from .aides import fiche
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])


async def liste(client: AsyncClient, **params: Any) -> dict[str, Any]:
    reponse = await client.get("/api/v1/produits", params={"par_page": 60, **params})
    assert reponse.status_code == 200, reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees


def slugs(page: dict[str, Any]) -> set[str]:
    return {p["slug"] for p in page["elements"]}


async def test_par_metier_genre_couleur_et_taille(client: AsyncClient) -> None:
    sages_femmes = await liste(client, metier="sage-femme")
    assert {"tunique-sage-femme", "blouse-femme-cintree", "tunique-wax"} <= slugs(sages_femmes)
    assert "blouse-homme-col-officier" not in slugs(sages_femmes)

    femmes = await liste(client, rayon="blouses-medicales", genre="femme")
    assert slugs(femmes) == {"blouse-femme-cintree"}
    roses = await liste(client, couleur="Rose poudré")
    assert slugs(roses) == {"blouse-femme-cintree", "montre-infirmiere"}
    xxxl = await liste(client, rayon="blouses-medicales", taille="XXXL")
    assert slugs(xxxl) == {"blouse-homme-col-officier"}
    wax = await liste(client, collection="Wax")
    assert slugs(wax) == {"tunique-wax", "calot-wax"}
    assert (await client.get("/api/v1/produits", params={"metier": "plombier"})).status_code == 422


async def test_nouveautes_promotions_et_tri(client: AsyncClient) -> None:
    nouveautes = await liste(client, nouveau="true")
    assert all(p["est_nouveau"] for p in nouveautes["elements"]) and nouveautes["total"] >= 5
    promos = await liste(client, promo="true")
    [promo] = promos["elements"]
    assert (promo["slug"], promo["prix_public"], promo["prix_avant_promo"]) == (
        "blouse-pharmacie-zippee",
        13_000,
        15_000,
    )
    prix = [
        p["prix_public"]
        for p in (await liste(client, rayon="pantalons", tri="prix_croissant"))["elements"]
    ]
    assert prix == sorted(prix)
    prix = [
        p["prix_public"]
        for p in (await liste(client, rayon="pantalons", tri="prix_decroissant"))["elements"]
    ]
    assert prix == sorted(prix, reverse=True)


async def test_facettes_du_rayon(client: AsyncClient) -> None:
    page = await liste(client, rayon="tuniques", genre="femme")
    facettes = page["facettes"]
    assert [f["valeur"] for f in facettes["genres"]] == ["femme", "mixte"]  # tout le rayon
    couleurs = {f["valeur"]: f for f in facettes["couleurs"]}
    assert couleurs["Bleu roi"]["hex"] == "#1f4fa8" and couleurs["Bleu roi"]["nombre"] == 1
    assert [f["valeur"] for f in facettes["tailles"]] == ["XS", "S", "M", "L", "XL", "XXL"]
    assert {f["valeur"] for f in facettes["collections"]} == {
        "Essentielle",
        "Confort stretch",
        "Wax",
    }
    assert facettes["metiers"][0]["valeur"] == "infirmier"


async def test_fiche_avec_pastilles_matiere_et_metiers(client: AsyncClient) -> None:
    tunique = await fiche(client, "tunique-col-v")
    assert [c["nom"] for c in tunique["couleurs"]] == [
        "Bleu roi",
        "Vert bloc",
        "Bordeaux",
        "Gris ardoise",
    ]
    assert tunique["tailles"] == ["XS", "S", "M", "L", "XL", "XXL"]
    assert len(tunique["variantes"]) == 24
    assert {v["couleur_hex"] for v in tunique["variantes"]} == {
        "#1f4fa8",
        "#2e8b6e",
        "#7a1f35",
        "#5b6770",
    }
    assert tunique["matiere"].startswith("Polycoton") and tunique["fabrique_sur_commande"] is True
    assert "infirmier" in tunique["metiers"] and tunique["manches"] == "courtes"
    gants = await fiche(client, "gants-steriles")
    assert gants["prix_avant_promo"] is None and gants["prix_public"] is None


async def test_metiers_avec_nombre_de_produits(client: AsyncClient) -> None:
    metiers = {m["slug"]: m for m in (await client.get("/api/v1/metiers")).json()}
    assert metiers["sage-femme"]["nom"] == "Sages-femmes"
    assert metiers["infirmier"]["nombre_produits"] > metiers["dentiste"]["nombre_produits"] > 0


async def test_prix_barre_controle(client: AsyncClient) -> None:
    pantalon = await fiche(client, "pantalon-unisexe")
    refus = await client.patch(
        f"/api/v1/admin/produits/{pantalon['id']}", json={"prix_avant_promo": 7_000}, headers=ADMIN
    )
    assert refus.status_code == 422
    promo = await client.patch(
        f"/api/v1/admin/produits/{pantalon['id']}",
        json={"prix_avant_promo": 9_000, "metiers": ["infirmier", "etudiant"], "est_nouveau": True},
        headers=ADMIN,
    )
    assert promo.status_code == 200, promo.text
    apres = await fiche(client, "pantalon-unisexe")
    assert (apres["prix_avant_promo"], apres["metiers"], apres["est_nouveau"]) == (
        9_000,
        ["infirmier", "etudiant"],
        True,
    )
