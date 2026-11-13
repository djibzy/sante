"""Découverte visuelle : mur de couleurs, familles, filtres, couleurs proches, photos par
couleur."""

from typing import Any

import pytest
from httpx import AsyncClient

from boutique import couleurs

from .aides import fiche
from .conftest import jeton
from .test_photos import photo

ADMIN = jeton(["boutique:admin"])


async def explorer(client: AsyncClient, **filtres: str) -> Any:
    reponse = await client.get("/api/v1/explorer", params=filtres)
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


@pytest.mark.parametrize(
    ("hexa", "famille"),
    [
        ("#ffffff", "blanc"),
        ("#f3ecd9", "blanc"),  # écru
        ("#1d1d1f", "gris"),  # noir
        ("#5b6770", "gris"),  # gris ardoise, à peine bleuté
        ("#1c2a4a", "bleu"),  # bleu marine
        ("#9fc9ea", "bleu"),  # bleu ciel
        ("#2e8b6e", "vert"),  # vert bloc
        ("#1aa6a6", "vert"),  # turquoise
        ("#e8b4b8", "rose"),  # rose poudré
        ("#7a1f35", "rouge"),  # bordeaux
        ("#6b2d5c", "violet"),  # prune
        ("#e07b1f", "orange"),  # wax orange
    ],
)
def test_familles_de_couleurs(hexa: str, famille: str) -> None:
    assert couleurs.famille(hexa) == famille


def test_distance_percue() -> None:
    assert couleurs.distance("#1f4fa8", "#1f4fa8") == 0
    assert round(couleurs.distance("#000000", "#ffffff")) == 100
    # Le bleu roi est plus proche du wax bleu que du bleu marine.
    assert couleurs.distance("#1f4fa8", "#2b5fb3") < couleurs.distance("#1f4fa8", "#1c2a4a")


async def test_mur_de_couleurs(client: AsyncClient) -> None:
    mur = await explorer(client)
    assert [f["code"] for f in mur["familles"]] == list(couleurs.CODES)
    tuiles = mur["tuiles"]
    assert sum(f["nombre"] for f in mur["familles"]) == len(tuiles)
    # Une tuile par article et par couleur, rangées par famille puis du clair au foncé.
    tunique = {t["couleur"]: t for t in tuiles if t["produit_slug"] == "tunique-col-v"}
    assert set(tunique) == {"Bleu roi", "Bordeaux", "Gris ardoise", "Vert bloc"}
    assert tunique["Bordeaux"] == {
        "produit_slug": "tunique-col-v",
        "nom": "Tunique col V unisexe",
        "rayon_slug": "tuniques",
        "genre": "mixte",
        "couleur": "Bordeaux",
        "hex": "#7a1f35",
        "famille": "rouge",
        "prix": 9_500,
        "image": None,
        "distance": None,
    }
    rangs = [couleurs.rang(t["hex"]) for t in tuiles]
    assert rangs == sorted(rangs)
    assert tuiles[0]["famille"] == "blanc"
    # Seulement des tenues : ni affiches, ni kits, ni articles du pharmacien.
    rayons = {t["rayon_slug"] for t in tuiles}
    assert rayons <= {
        "blouses-medicales",
        "tuniques",
        "pantalons",
        "tenues-de-bloc",
        "chaussures",
        "gilets-polos",
        "accessoires",
    }


async def test_filtres(client: AsyncClient) -> None:
    tout = await explorer(client)
    bleus = await explorer(client, famille="bleu")
    assert bleus["tuiles"] and {t["famille"] for t in bleus["tuiles"]} == {"bleu"}
    assert bleus["familles"] == tout["familles"]  # les nombres ignorent la famille choisie

    sages_femmes = await explorer(client, metier="sage-femme", genre="femme")
    produits = {t["produit_slug"] for t in sages_femmes["tuiles"]}
    assert "tunique-sage-femme" in produits
    assert all(t["genre"] in ("femme", "mixte") for t in sages_femmes["tuiles"])
    pantalons = await explorer(client, rayon="pantalons")
    assert {t["rayon_slug"] for t in pantalons["tuiles"]} == {"pantalons"}
    assert (await client.get("/api/v1/explorer", params={"famille": "fuchsia"})).status_code == 422
    nuancier = await explorer(client, familles_seulement="true")
    assert (nuancier["familles"], nuancier["tuiles"]) == (tout["familles"], [])


async def test_couleurs_proches(client: AsyncClient) -> None:
    proches = (await explorer(client, proche="#1F4FA8"))["tuiles"]
    assert proches[0]["couleur"] == "Bleu roi" and proches[0]["distance"] == 0
    distances = [t["distance"] for t in proches]
    assert distances == sorted(distances) and max(distances) <= 30
    assert "Wax bleu" in {t["couleur"] for t in proches}
    assert "Blanc" not in {t["couleur"] for t in proches}
    refus = await client.get("/api/v1/explorer", params={"proche": "bleu"})
    assert refus.status_code == 422


async def test_photos_par_couleur(client: AsyncClient) -> None:
    tunique = await fiche(client, "tunique-col-v")
    photos = {
        "images": [
            {"url": "/photos/tunique-bordeaux.jpg", "texte_alternatif": "Tunique bordeaux"},
            {
                "url": "/photos/tunique-bleu.jpg",
                "texte_alternatif": "Tunique bleu roi, de face",
                "couleur": "Bleu roi",
            },
        ]
    }
    url = f"/api/v1/admin/produits/{tunique['id']}/images"
    assert (await client.put(url, json=photos, headers=ADMIN)).status_code == 200
    publique = await fiche(client, "tunique-col-v")
    assert [i["couleur"] for i in publique["images"]] == [None, "Bleu roi"]
    tuiles = {
        t["couleur"]: t["image"]
        for t in (await explorer(client))["tuiles"]
        if t["produit_slug"] == "tunique-col-v"
    }
    assert tuiles["Bleu roi"]["url"] == "/photos/tunique-bleu.jpg"
    assert tuiles["Bordeaux"] is None  # photo sans couleur : l'article en a plusieurs

    # Article d'une seule couleur : sa photo l'illustre, même sans couleur indiquée.
    stage = await fiche(client, "blouse-de-stage")
    seule = {"images": [{"url": "/photos/stage.jpg", "texte_alternatif": "Blouse de stage"}]}
    url_stage = f"/api/v1/admin/produits/{stage['id']}/images"
    assert (await client.put(url_stage, json=seule, headers=ADMIN)).status_code == 200
    [tuile] = [
        t for t in (await explorer(client))["tuiles"] if t["produit_slug"] == "blouse-de-stage"
    ]
    assert tuile["image"]["url"] == "/photos/stage.jpg"

    inconnue = {"images": [{**photos["images"][1], "couleur": "Jaune"}]}
    refus = await client.put(url, json=inconnue, headers=ADMIN)
    assert refus.status_code == 422 and "Jaune" in refus.json()["detail"]
    envoi = await client.post(
        f"/api/v1/admin/produits/{tunique['id']}/photos",
        files={"fichier": ("p.jpg", photo(), "image/jpeg")},
        data={"texte_alternatif": "Tunique vert bloc, de face", "couleur": "Vert bloc"},
        headers=ADMIN,
    )
    assert envoi.status_code == 201, envoi.text
    assert envoi.json()["images"][-1]["couleur"] == "Vert bloc"
