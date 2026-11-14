"""Page publique : l'offre, la demande d'une structure, et son suivi par l'équipe."""

from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient

from .aides import GESTION, TERRAIN, contrat, journal, sms
from .conftest import jeton

DEMANDE: dict[str, Any] = {
    "structure": "Clinique  du Fleuve",
    "type_structure": "clinique",
    "contact": "Awa Traoré, surveillante générale",
    "telephone": "76 12 34 56",
    "quartier": "Badalabougou, Bamako",
    "volumes": {"drap": 120, "blouse": 40, "taie": 0},
    "collectes_par_semaine": 2,
    "message": "Nous avons 20 lits.",
}


async def demander(client: AsyncClient, **autres: Any) -> Any:
    reponse = await client.post("/api/v1/demandes", json={**DEMANDE, **autres})
    assert reponse.status_code in (200, 201), reponse.text
    return reponse


async def test_l_offre_publique(client: AsyncClient) -> None:
    offre = (await client.get("/api/v1/offre")).json()
    assert offre["services"] == [{"code": "entretien_linge", "libelle": "Entretien du linge"}]
    codes = [a["code"] for a in offre["articles"]]
    assert codes[:5] == ["blouse", "tunique", "pantalon", "casaque", "drap"]
    champ = next(a for a in offre["articles"] if a["code"] == "champ")
    assert champ["libelle"] == "Champ opératoire"
    assert "stérilisation reste faite par la structure" in champ["note"]
    assert {"code": "cscom", "libelle": "CSCom ou CSRéf"} in offre["types_structure"]


async def test_une_structure_demande_et_l_equipe_est_prevenue(
    app: FastAPI, client: AsyncClient
) -> None:
    app.state.parametres.telephones_equipe = ["+22370000099"]
    reponse = await demander(client)
    assert reponse.status_code == 201
    assert reponse.json() == {
        "reference": "DE-101",
        "message": "Merci ! Nous vous rappelons pour convenir d'une visite.",
    }
    messages = [(n.destinataire, n.message) for n in await sms(app)]
    assert messages == [
        (
            "+22376123456",
            "Yasal Santé : demande DE-101 bien recue (entretien du linge). Nous vous rappelons "
            "pour convenir d'une visite.",
        ),
        (
            "+22370000099",
            "Nouvelle demande DE-101 : Clinique du Fleuve (Badalabougou, Bamako), Awa Traoré, "
            "surveillante générale, +223 76 12 34 56, 160 pièces/semaine.",
        ),
    ]
    assert await journal(app) == ["demande.creee"]

    liste = (await client.get("/api/v1/admin/demandes", headers=GESTION)).json()
    assert liste["total"] == 1 and liste["nouvelles"] == 1
    vue = liste["elements"][0]
    assert vue["structure"] == "Clinique du Fleuve"  # espaces superflus retirés
    assert vue["volumes"] == {"drap": 120, "blouse": 40}  # les zéros ne sont pas gardés
    assert vue["pieces_par_semaine"] == 160
    assert vue["libelle_type"] == "Clinique" and vue["libelle_statut"] == "Nouvelle"


async def test_doublon_et_limite_par_numero(app: FastAPI, client: AsyncClient) -> None:
    premiere = await demander(client)
    encore = await demander(client, structure="clinique du fleuve")
    assert encore.status_code == 200  # envoyée deux fois : la même demande, pas un second SMS
    assert encore.json()["reference"] == premiere.json()["reference"]
    assert len(await sms(app)) == 1
    await demander(client, structure="Cabinet Pasteur")
    await demander(client, structure="Maternité Kalaban")
    de_trop = await client.post("/api/v1/demandes", json={**DEMANDE, "structure": "Autre"})
    assert de_trop.status_code == 429
    assert "nous vous rappelons" in de_trop.json()["detail"]


async def test_demande_invalide(client: AsyncClient) -> None:
    faux = await client.post("/api/v1/demandes", json={**DEMANDE, "telephone": "12 34 56"})
    assert faux.status_code == 422
    assert faux.json()["detail"] == "Numéro de téléphone invalide"
    for champ, valeur in (
        ("volumes", {"tapis": 3}),
        ("volumes", {"drap": -1}),
        ("collectes_par_semaine", 9),
        ("type_structure", "hotel"),
    ):
        reponse = await client.post("/api/v1/demandes", json={**DEMANDE, champ: valeur})
        assert reponse.status_code == 422, (champ, valeur)


async def test_l_equipe_suit_les_demandes(app: FastAPI, client: AsyncClient) -> None:
    await demander(client)
    await demander(client, structure="Cabinet dentaire Sourire", telephone="66 77 88 99")
    assert (await client.get("/api/v1/admin/demandes")).status_code == 401
    assert (await client.get("/api/v1/admin/demandes", headers=TERRAIN)).status_code == 403
    assert (
        await client.get("/api/v1/admin/demandes", headers=jeton(["boutique:admin"]))
    ).status_code == 403

    trouvees = await client.get("/api/v1/admin/demandes", params={"q": "8899"}, headers=GESTION)
    assert [d["reference"] for d in trouvees.json()["elements"]] == ["DE-102"]

    appelee = await client.patch(
        "/api/v1/admin/demandes/de-101",
        json={"statut": "en_discussion", "notes_equipe": "Visite jeudi 10 h."},
        headers=GESTION,
    )
    assert appelee.status_code == 200, appelee.text
    assert appelee.json()["libelle_statut"] == "En discussion"
    assert appelee.json()["notes_equipe"] == "Visite jeudi 10 h."
    en_cours = await client.get(
        "/api/v1/admin/demandes", params={"statut": "en_discussion"}, headers=GESTION
    )
    assert [d["reference"] for d in en_cours.json()["elements"]] == ["DE-101"]
    assert en_cours.json()["nouvelles"] == 1

    a_la_main = await client.patch(
        "/api/v1/admin/demandes/DE-101", json={"statut": "signee"}, headers=GESTION
    )
    assert a_la_main.status_code == 422  # on signe en créant le contrat
    assert (
        await client.patch("/api/v1/admin/demandes/DE-999", json={}, headers=GESTION)
    ).status_code == 404
    assert await journal(app) == ["demande.creee", "demande.creee", "demande.modifiee"]


async def test_signer_une_demande_cree_son_contrat(client: AsyncClient) -> None:
    await demander(client)
    demande = (await client.get("/api/v1/admin/demandes/DE-101", headers=GESTION)).json()
    assert demande["contact"] == "Awa Traoré, surveillante générale"
    signe = await contrat(client, demande_id=demande["id"], structure=demande["structure"])
    assert signe["reference"] == "CT-101"
    assert signe["demande_reference"] == "DE-101"

    relue = (await client.get("/api/v1/admin/demandes", headers=GESTION)).json()["elements"][0]
    assert relue["statut"] == "signee" and relue["contrat_reference"] == "CT-101"
    deux_fois = await client.post(
        "/api/v1/admin/contrats",
        json={**signe, "demande_id": demande["id"], "telephone": "76 00 00 01"},
        headers=GESTION,
    )
    assert deux_fois.status_code == 409
    classee = await client.patch(
        "/api/v1/admin/demandes/DE-101", json={"statut": "sans_suite"}, headers=GESTION
    )
    assert classee.status_code == 409
