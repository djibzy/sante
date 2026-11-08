from httpx import AsyncClient

from .conftest import entete, inscrire

CSCOM = {"nom": "CSCom de Banconi", "type": "cscom", "commune": "Commune I, Bamako"}


async def test_creer_une_organisation_rend_gestionnaire(client: AsyncClient) -> None:
    jetons = await inscrire(client)
    reponse = await client.post("/api/v1/organisations", json=CSCOM, headers=entete(jetons))

    assert reponse.status_code == 201
    assert reponse.json()["mon_role"] == "gestionnaire"
    mes = await client.get("/api/v1/organisations", headers=entete(jetons))
    assert [o["nom"] for o in mes.json()] == ["CSCom de Banconi"]


async def test_type_inconnu_refuse(client: AsyncClient) -> None:
    jetons = await inscrire(client)
    reponse = await client.post(
        "/api/v1/organisations", json={"nom": "X", "type": "cafe"}, headers=entete(jetons)
    )
    assert reponse.status_code == 422


async def test_ajouter_un_membre_par_son_numero(client: AsyncClient) -> None:
    gestionnaire = await inscrire(client, telephone="76123456", nom="Awa Traoré")
    await inscrire(client, telephone="66123456", nom="Moussa Keïta")
    org = (
        await client.post("/api/v1/organisations", json=CSCOM, headers=entete(gestionnaire))
    ).json()

    ajout = await client.post(
        f"/api/v1/organisations/{org['id']}/membres",
        json={"telephone": "66 12 34 56", "role": "acheteur"},
        headers=entete(gestionnaire),
    )
    assert ajout.status_code == 201
    membres = await client.get(
        f"/api/v1/organisations/{org['id']}/membres", headers=entete(gestionnaire)
    )
    assert {(m["nom"], m["role"]) for m in membres.json()} == {
        ("Awa Traoré", "gestionnaire"),
        ("Moussa Keïta", "acheteur"),
    }

    doublon = await client.post(
        f"/api/v1/organisations/{org['id']}/membres",
        json={"telephone": "66123456"},
        headers=entete(gestionnaire),
    )
    assert doublon.status_code == 409


async def test_seul_un_gestionnaire_ajoute_des_membres(client: AsyncClient) -> None:
    gestionnaire = await inscrire(client, telephone="76123456")
    acheteur = await inscrire(client, telephone="66123456", nom="Moussa Keïta")
    await inscrire(client, telephone="70123456", nom="Fanta Diallo")
    org = (
        await client.post("/api/v1/organisations", json=CSCOM, headers=entete(gestionnaire))
    ).json()
    await client.post(
        f"/api/v1/organisations/{org['id']}/membres",
        json={"telephone": "66123456", "role": "acheteur"},
        headers=entete(gestionnaire),
    )

    refuse = await client.post(
        f"/api/v1/organisations/{org['id']}/membres",
        json={"telephone": "70123456"},
        headers=entete(acheteur),
    )
    assert refuse.status_code == 403


async def test_une_organisation_est_invisible_pour_les_non_membres(client: AsyncClient) -> None:
    gestionnaire = await inscrire(client, telephone="76123456")
    curieux = await inscrire(client, telephone="66123456", nom="Curieux")
    org = (
        await client.post("/api/v1/organisations", json=CSCOM, headers=entete(gestionnaire))
    ).json()

    assert (
        await client.get(f"/api/v1/organisations/{org['id']}", headers=entete(curieux))
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/organisations/{org['id']}/membres", headers=entete(curieux))
    ).status_code == 404


async def test_membre_inconnu(client: AsyncClient) -> None:
    gestionnaire = await inscrire(client)
    org = (
        await client.post("/api/v1/organisations", json=CSCOM, headers=entete(gestionnaire))
    ).json()
    reponse = await client.post(
        f"/api/v1/organisations/{org['id']}/membres",
        json={"telephone": "79000000"},
        headers=entete(gestionnaire),
    )
    assert reponse.status_code == 404
