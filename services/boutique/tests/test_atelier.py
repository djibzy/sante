from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient

from .aides import commander, fiche, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
ATELIER = jeton(["boutique:atelier"], nom="Atelier Bibou")


def dans(jours: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=jours)).isoformat()


async def statut(client: AsyncClient, reference: str, nouveau: str) -> dict[str, Any]:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": nouveau}, headers=ADMIN
    )
    assert reponse.status_code == 200, reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees


async def file(client: AsyncClient, **params: Any) -> list[dict[str, Any]]:
    reponse = await client.get("/api/v1/atelier/ordres", params=params, headers=ATELIER)
    assert reponse.status_code == 200, reponse.text
    donnees: list[dict[str, Any]] = reponse.json()
    return donnees


async def avancer(client: AsyncClient, ordre_id: str, *etats: str) -> dict[str, Any]:
    vue: dict[str, Any] = {}
    for etat in etats:
        reponse = await client.post(
            f"/api/v1/atelier/ordres/{ordre_id}/etat", json={"etat": etat}, headers=ATELIER
        )
        assert reponse.status_code == 200, reponse.text
        vue = reponse.json()
    return vue


async def stock(client: AsyncClient, slug: str) -> dict[str, Any]:
    lignes = (await client.get("/api/v1/admin/stock", headers=ADMIN)).json()
    return next(ligne for ligne in lignes if ligne["produit_slug"] == slug)


async def recevoir(client: AsyncClient, slug: str, quantite: int) -> None:
    produit = await fiche(client, slug)
    reponse = await client.post(
        "/api/v1/admin/stock/mouvements",
        json={"produit_id": produit["id"], "quantite": quantite, "motif": "reception"},
        headers=ADMIN,
    )
    assert reponse.status_code == 201, reponse.text


async def test_l_atelier_fabrique_puis_la_commande_est_prete(client: AsyncClient) -> None:
    await recevoir(client, "thermometre-digital", 10)
    lignes = [
        await ligne(client, "blouse-medicale-brodee", "L", 2, "A. Traoré, sage-femme"),
        await ligne(client, "kit-hygiene"),
        await ligne(client, "thermometre-digital"),
    ]
    creee = await commander(client, lignes)
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    assert await file(client) == []  # rien à fabriquer avant la confirmation

    await statut(client, reference, "confirmee")
    ordres = await file(client)
    assert [(o["poste"], o["quantite"], o["personnalisation"]) for o in ordres] == [
        ("broderie", 2, "A. Traoré, sage-femme"),
        ("assemblage", 1, None),
    ]
    assert ordres[0]["client"] == "Aminata Traoré" and ordres[0]["reference"] == reference
    assert "telephone" not in ordres[0]
    assert [o["poste"] for o in await file(client, poste="assemblage")] == ["assemblage"]

    saut = await client.post(
        f"/api/v1/atelier/ordres/{ordres[0]['id']}/etat", json={"etat": "termine"}, headers=ATELIER
    )
    assert saut.status_code == 409
    vue = await avancer(client, ordres[0]["id"], "en_cours")
    assert vue["passages_possibles"] == ["a_faire", "controle"]
    suivi = (await client.get(f"/api/v1/suivi/{reference}", params={"cle": cle})).json()
    assert suivi["statut"] == "en_preparation"
    assert suivi["historique"][-1]["note"] == "Fabrication commencée"

    await avancer(client, ordres[0]["id"], "controle", "termine")
    await avancer(client, ordres[1]["id"], "en_cours", "controle", "termine")
    assert await file(client) == []
    detail = (await client.get(f"/api/v1/admin/commandes/{reference}", headers=ADMIN)).json()
    assert detail["statut"] == "en_preparation"  # le thermomètre reste à préparer
    assert detail["historique_complet"][-1]["visible_client"] is False
    assert (await stock(client, "thermometre-digital"))["reserve"] == 1

    await statut(client, reference, "prete")
    thermometre = await stock(client, "thermometre-digital")
    assert (thermometre["niveau"], thermometre["reserve"]) == (9, 0)
    await statut(client, reference, "annulee")
    assert (await stock(client, "thermometre-digital"))["niveau"] == 10
    termines = await file(client, etat="termine")
    assert len(termines) == 2  # le travail fait reste enregistré


async def test_une_commande_toute_fabriquee_devient_prete_seule(client: AsyncClient) -> None:
    creee = await commander(client, [await ligne(client, "calot-brode", quantite=3)])
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    await statut(client, reference, "confirmee")
    [ordre] = await file(client)
    await avancer(client, ordre["id"], "en_cours", "controle", "en_cours", "controle", "termine")
    suivi = (await client.get(f"/api/v1/suivi/{reference}", params={"cle": cle})).json()
    assert suivi["statut"] == "prete"
    assert [e["note"] for e in suivi["historique"][-2:]] == [
        "Fabrication commencée",
        "Fabrication terminée",
    ]


async def test_l_annulation_retire_les_pieces_de_la_file(client: AsyncClient) -> None:
    creee = await commander(client, [await ligne(client, "tunique-sage-femme", "M")])
    reference = creee["commande"]["reference"]
    await statut(client, reference, "confirmee")
    assert len(await file(client)) == 1
    await statut(client, reference, "annulee")
    assert await file(client) == []
    assert [o["etat"] for o in await file(client, etat="annule")] == ["annule"]


async def test_la_date_promise_suit_la_charge_de_l_atelier(client: AsyncClient) -> None:
    reponse = await client.patch(
        "/api/v1/admin/postes/broderie", json={"capacite_jour": 2}, headers=ADMIN
    )
    assert reponse.status_code == 200
    creee = await commander(client, [await ligne(client, "blouse-medicale-brodee", "M", 30)])
    assert creee["commande"]["date_promise"] == dans(15)  # 30 pièces à 2 par jour
    await statut(client, creee["commande"]["reference"], "confirmee")

    postes = (await client.get("/api/v1/atelier/postes", headers=ATELIER)).json()
    broderie = next(p for p in postes if p["code"] == "broderie")
    assert (broderie["charge"], broderie["jours_de_file"]) == (30, 15)
    corps = {"lignes": [await ligne(client, "blouse-medicale-brodee", "S", 2)]}
    chiffrage = (await client.post("/api/v1/panier/chiffrage", json=corps)).json()
    assert chiffrage["date_estimee"] == dans(16)
    petit = {"lignes": [await ligne(client, "affiche-a2")]}
    assert (await client.post("/api/v1/panier/chiffrage", json=petit)).json()[
        "date_estimee"
    ] == dans(7)  # impression : délai habituel, file vide


async def test_l_atelier_ne_voit_pas_la_gestion(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/admin/commandes", headers=ATELIER)).status_code == 403
    assert (await client.get("/api/v1/admin/stock", headers=ATELIER)).status_code == 403
    assert (await client.get("/api/v1/atelier/ordres", headers=jeton())).status_code == 403
    assert (await client.get("/api/v1/atelier/ordres", headers=ADMIN)).status_code == 200
    modification = await client.patch(
        "/api/v1/admin/postes/broderie", json={"capacite_jour": 1}, headers=ATELIER
    )
    assert modification.status_code == 403


async def test_stock_arrivages_alertes_et_inventaire(client: AsyncClient) -> None:
    thermometre = await fiche(client, "thermometre-digital")
    await recevoir(client, "thermometre-digital", 10)
    seuil = await client.patch(
        f"/api/v1/admin/produits/{thermometre['id']}", json={"seuil_alerte": 3}, headers=ADMIN
    )
    assert seuil.status_code == 200

    creee = await commander(client, [await ligne(client, "thermometre-digital", quantite=8)])
    assert creee["commande"]["date_promise"] == dans(1)  # en stock : prêt le lendemain
    await statut(client, creee["commande"]["reference"], "confirmee")
    article = await stock(client, "thermometre-digital")
    assert (article["niveau"], article["reserve"], article["disponible"]) == (10, 8, 2)
    alertes = (await client.get("/api/v1/admin/stock?alerte=true", headers=ADMIN)).json()
    slugs = [a["produit_slug"] for a in alertes]
    assert "thermometre-digital" in slugs  # disponible 2, seuil 3
    assert all(a["disponible"] <= a["seuil_alerte"] for a in alertes)

    perte = await client.post(
        "/api/v1/admin/stock/mouvements",
        json={
            "produit_id": thermometre["id"],
            "quantite": 1,
            "motif": "perte",
            "note": "Écran cassé",
        },
        headers=ADMIN,
    )
    assert perte.json()["quantite"] == -1
    comptage = {"produit_id": thermometre["id"], "quantite_comptee": 12}
    ecart = await client.post("/api/v1/admin/stock/inventaire", json=comptage, headers=ADMIN)
    assert ecart.json()["quantite"] == 3
    rien = await client.post("/api/v1/admin/stock/inventaire", json=comptage, headers=ADMIN)
    assert rien.json() is None
    historique = (
        await client.get(
            "/api/v1/admin/stock/mouvements",
            params={"produit_id": thermometre["id"]},
            headers=ADMIN,
        )
    ).json()
    assert [m["motif"] for m in historique] == ["inventaire", "perte", "reception"]

    tensiometre = {"lignes": [await ligne(client, "tensiometre-electronique")]}
    chiffrage = (await client.post("/api/v1/panier/chiffrage", json=tensiometre)).json()
    assert chiffrage["date_estimee"] == dans(7)  # rupture : délai de réapprovisionnement


async def test_mouvements_refuses(client: AsyncClient) -> None:
    blouse, sabots = (
        await fiche(client, "blouse-medicale-brodee"),
        await fiche(client, "sabots-de-travail"),
    )
    for corps, attendu in (
        ({"produit_id": blouse["id"], "quantite": 5, "motif": "reception"}, "fabriqué à l'atelier"),
        ({"produit_id": sabots["id"], "quantite": 5, "motif": "reception"}, "variante"),
    ):
        reponse = await client.post("/api/v1/admin/stock/mouvements", json=corps, headers=ADMIN)
        assert reponse.status_code == 422
        assert attendu in reponse.json()["detail"]
    vente = {"produit_id": sabots["id"], "quantite": 1, "motif": "vente"}
    reponse = await client.post("/api/v1/admin/stock/mouvements", json=vente, headers=ADMIN)
    assert reponse.status_code == 422  # les ventes viennent des commandes, jamais à la main
    inconnu = await client.patch(
        f"/api/v1/admin/produits/{blouse['id']}", json={"poste_atelier": "soudure"}, headers=ADMIN
    )
    assert inconnu.status_code == 422
