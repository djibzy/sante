"""Partenaires blanchisseurs et contrats des structures : saisie, contrôles, accès."""

from fastapi import FastAPI
from httpx import AsyncClient

from .aides import GESTION, TERRAIN, contrat, journal, partenaire


async def test_partenaires_a_la_piece_ou_au_kilo(app: FastAPI, client: AsyncClient) -> None:
    pressing = await partenaire(client)
    assert pressing["telephone"] == "+22376112233"
    assert pressing["tarifs"] == {"blouse": 300, "drap": 400, "taie": 150}
    sans_prix = await client.post(
        "/api/v1/admin/partenaires",
        json={"nom": "Blanchisserie Djoliba", "telephone": "76 44 55 66", "mode_tarif": "kg"},
        headers=GESTION,
    )
    assert sans_prix.status_code == 422
    blanchisserie = await partenaire(
        client, nom="Blanchisserie Djoliba", type="blanchisserie", mode_tarif="kg", tarif_kg=600
    )
    meme_nom = await client.post(
        "/api/v1/admin/partenaires",
        json={"nom": "Pressing du Fleuve", "telephone": "76 11 22 34"},
        headers=GESTION,
    )
    assert meme_nom.status_code == 409

    vers_kilo = await client.patch(
        f"/api/v1/admin/partenaires/{pressing['id']}", json={"mode_tarif": "kg"}, headers=GESTION
    )
    assert vers_kilo.status_code == 422
    modifie = await client.patch(
        f"/api/v1/admin/partenaires/{pressing['id']}",
        json={"tarifs": {"blouse": 350}, "hygiene_verifiee_le": "2026-11-10", "est_actif": False},
        headers=GESTION,
    )
    assert modifie.status_code == 200, modifie.text
    assert modifie.json()["tarifs"] == {"blouse": 350}

    # L'équipe de terrain voit où déposer le linge, sans les tarifs.
    terrain = await client.get("/api/v1/partenaires", headers=TERRAIN)
    assert [p["nom"] for p in terrain.json()] == ["Blanchisserie Djoliba"]
    assert terrain.json()[0]["pesee_requise"] is True
    assert "tarifs" not in terrain.json()[0]
    assert (await client.get("/api/v1/admin/partenaires", headers=TERRAIN)).status_code == 403
    tous = (await client.get("/api/v1/admin/partenaires", headers=GESTION)).json()
    assert [p["nom"] for p in tous] == [blanchisserie["nom"], pressing["nom"]]  # actifs d'abord
    assert await journal(app) == ["partenaire.ajoute", "partenaire.ajoute", "partenaire.modifie"]


async def test_contrat_jours_formule_et_dates(app: FastAPI, client: AsyncClient) -> None:
    pressing = await partenaire(client)
    signe = await contrat(client, partenaire_id=pressing["id"], jours_collecte=[4, 1, 1])
    assert signe["reference"] == "CT-101"
    assert signe["jours_collecte"] == [1, 4]
    assert signe["libelle_jours"] == "lundi et jeudi"
    assert signe["partenaire"]["nom"] == "Pressing du Fleuve"
    assert signe["telephone"] == "+22376000001"
    sur_appel = await contrat(client, structure="Cabinet Sourire", jours_collecte=[])
    assert sur_appel["libelle_jours"] == "sur appel"

    for erreur in (
        {"formule": "forfait"},  # sans montant
        {"debut_le": "2026-11-10", "fin_le": "2026-11-01"},
        {"jours_collecte": [0, 3]},
        {"tarifs": {"drap": -5}},
    ):
        reponse = await client.post(
            "/api/v1/admin/contrats",
            json={**signe, "telephone": "76 00 00 01", **erreur},
            headers=GESTION,
        )
        assert reponse.status_code == 422, erreur

    await client.patch(
        f"/api/v1/admin/partenaires/{pressing['id']}", json={"est_actif": False}, headers=GESTION
    )
    vers_inactif = await client.post(
        "/api/v1/admin/contrats",
        json={
            **signe,
            "telephone": "76 00 00 01",
            "structure": "Autre",
            "partenaire_id": pressing["id"],
        },
        headers=GESTION,
    )
    assert vers_inactif.status_code == 422
    assert vers_inactif.json()["detail"] == "Pressing du Fleuve ne reçoit plus de linge"

    forfait_vide = await client.patch(
        "/api/v1/admin/contrats/ct-101", json={"formule": "forfait"}, headers=GESTION
    )
    assert forfait_vide.status_code == 422
    assert forfait_vide.json()["detail"] == "Indiquez le montant du forfait mensuel"
    forfait = await client.patch(
        "/api/v1/admin/contrats/CT-101",
        json={
            "formule": "forfait",
            "forfait_mensuel": 150_000,
            "pieces_incluses": 600,
            "prix_piece_supplementaire": 300,
            "jours_collecte": [2, 5],
        },
        headers=GESTION,
    )
    assert forfait.status_code == 200, forfait.text
    assert forfait.json()["libelle_jours"] == "mardi et vendredi"
    termine = await client.patch(
        "/api/v1/admin/contrats/101", json={"statut": "termine"}, headers=GESTION
    )
    assert termine.json()["statut"] == "termine"
    assert termine.json()["fin_le"] is not None  # le contrat se termine aujourd'hui

    liste = (await client.get("/api/v1/admin/contrats", headers=GESTION)).json()
    assert [c["reference"] for c in liste] == ["CT-102", "CT-101"]  # actifs d'abord
    assert (await client.get("/api/v1/admin/contrats", headers=TERRAIN)).status_code == 403
    assert (await client.get("/api/v1/admin/contrats/CT-999", headers=GESTION)).status_code == 404
    assert (
        await client.get("/api/v1/admin/contrats/n-importe-quoi", headers=GESTION)
    ).status_code == 404
    assert await journal(app) == [
        "partenaire.ajoute",
        "contrat.cree",
        "contrat.cree",
        "partenaire.modifie",
        "contrat.modifie",
        "contrat.modifie",
    ]
