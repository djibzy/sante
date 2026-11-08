import jwt
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from comptes.models import Consentement, JournalAudit

from .conftest import MOT_DE_PASSE, entete, inscrire


async def test_inscription_donne_un_compte_et_des_jetons(client: AsyncClient) -> None:
    jetons = await inscrire(client)

    assert jetons["utilisateur"]["telephone"] == "+22376123456"
    assert jetons["utilisateur"]["langue"] == "fr"
    assert jetons["expire_dans"] == 900
    moi = await client.get("/api/v1/auth/moi", headers=entete(jetons))
    assert moi.status_code == 200
    assert moi.json()["nom"] == "Awa Traoré"


async def test_inscription_enregistre_le_consentement_et_le_journal(
    client: AsyncClient, app: FastAPI
) -> None:
    jetons = await inscrire(client)

    async with app.state.sessions() as session:
        consentement = (await session.execute(select(Consentement))).scalar_one()
        actions = (await session.execute(select(JournalAudit.action))).scalars().all()
    assert str(consentement.utilisateur_id) == jetons["utilisateur"]["id"]
    assert consentement.version == "2026-11"
    assert "compte.cree" in actions


async def test_les_conditions_doivent_etre_acceptees(client: AsyncClient) -> None:
    reponse = await client.post(
        "/api/v1/auth/inscription",
        json={
            "telephone": "76123456",
            "nom": "Awa",
            "mot_de_passe": MOT_DE_PASSE,
            "accepte_conditions": False,
        },
    )
    assert reponse.status_code == 422


async def test_numero_invalide_refuse(client: AsyncClient) -> None:
    reponse = await client.post(
        "/api/v1/auth/inscription",
        json={
            "telephone": "123",
            "nom": "Awa",
            "mot_de_passe": MOT_DE_PASSE,
            "accepte_conditions": True,
        },
    )
    assert reponse.status_code == 422


async def test_un_seul_compte_par_numero(client: AsyncClient) -> None:
    await inscrire(client, telephone="76123456")
    reponse = await client.post(
        "/api/v1/auth/inscription",
        json={
            "telephone": "+223 76 12 34 56",
            "nom": "Autre",
            "mot_de_passe": MOT_DE_PASSE,
            "accepte_conditions": True,
        },
    )
    assert reponse.status_code == 409


async def test_connexion_avec_le_numero_dans_un_autre_format(client: AsyncClient) -> None:
    await inscrire(client, telephone="76 12 34 56")
    reponse = await client.post(
        "/api/v1/auth/connexion",
        json={"telephone": "+22376123456", "mot_de_passe": MOT_DE_PASSE},
    )
    assert reponse.status_code == 200
    assert "sante_rafraichissement" in reponse.cookies


async def test_mauvais_mot_de_passe_puis_verrouillage(client: AsyncClient) -> None:
    await inscrire(client)
    for _ in range(5):
        reponse = await client.post(
            "/api/v1/auth/connexion", json={"telephone": "76123456", "mot_de_passe": "faux"}
        )
        assert reponse.status_code == 401
    bloque = await client.post(
        "/api/v1/auth/connexion", json={"telephone": "76123456", "mot_de_passe": MOT_DE_PASSE}
    )
    assert bloque.status_code == 429


async def test_compte_inconnu_meme_message_que_mauvais_mot_de_passe(client: AsyncClient) -> None:
    reponse = await client.post(
        "/api/v1/auth/connexion", json={"telephone": "66000000", "mot_de_passe": "x"}
    )
    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Numéro ou mot de passe incorrect"


async def test_rafraichissement_avec_rotation(client: AsyncClient) -> None:
    jetons = await inscrire(client)
    premier = jetons["jeton_rafraichissement"]

    reponse = await client.post("/api/v1/auth/rafraichir", json={"jeton_rafraichissement": premier})
    assert reponse.status_code == 200
    second = reponse.json()["jeton_rafraichissement"]
    assert second != premier

    moi = await client.get("/api/v1/auth/moi", headers=entete(reponse.json()))
    assert moi.status_code == 200


async def test_reutiliser_un_jeton_remplace_coupe_toutes_les_sessions(client: AsyncClient) -> None:
    jetons = await inscrire(client)
    premier = jetons["jeton_rafraichissement"]
    second = (
        await client.post("/api/v1/auth/rafraichir", json={"jeton_rafraichissement": premier})
    ).json()["jeton_rafraichissement"]

    vol = await client.post("/api/v1/auth/rafraichir", json={"jeton_rafraichissement": premier})
    assert vol.status_code == 401
    apres = await client.post("/api/v1/auth/rafraichir", json={"jeton_rafraichissement": second})
    assert apres.status_code == 401


async def test_rafraichissement_par_cookie(client: AsyncClient) -> None:
    await inscrire(client)
    reponse = await client.post("/api/v1/auth/rafraichir")  # le cookie suit automatiquement
    assert reponse.status_code == 200


async def test_deconnexion(client: AsyncClient) -> None:
    jetons = await inscrire(client)
    jeton = jetons["jeton_rafraichissement"]
    reponse = await client.post("/api/v1/auth/deconnexion", json={"jeton_rafraichissement": jeton})
    assert reponse.status_code == 204
    apres = await client.post("/api/v1/auth/rafraichir", json={"jeton_rafraichissement": jeton})
    assert apres.status_code == 401


async def test_jeton_signe_et_cle_publiee(client: AsyncClient) -> None:
    jetons = await inscrire(client)
    cles = (await client.get("/.well-known/jwks.json")).json()["keys"]
    en_tete = jwt.get_unverified_header(jetons["jeton_acces"])

    assert en_tete["alg"] == "EdDSA"
    assert en_tete["kid"] == cles[0]["kid"]
    assert cles[0]["kty"] == "OKP"


async def test_moi_sans_jeton(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/moi")).status_code == 401
    faux = await client.get("/api/v1/auth/moi", headers={"Authorization": "Bearer abc"})
    assert faux.status_code == 401


async def test_sante(client: AsyncClient) -> None:
    reponse = await client.get("/sante")
    assert reponse.json() == {"statut": "ok", "service": "comptes"}
    assert reponse.headers["x-content-type-options"] == "nosniff"
