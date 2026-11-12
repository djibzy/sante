import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, update

from comptes.models import CodeVerification, JournalAudit, Utilisateur

from .conftest import MOT_DE_PASSE, entete, inscrire

NOUVEAU = "un-tout-nouveau-mot-de-passe"


class FauxSms:
    """Remplace l'opérateur : garde les SMS au lieu de les envoyer."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def envoyer(self, destinataire: str, message: str) -> str | None:
        self.messages.append((destinataire, message))
        return None

    def dernier_code(self) -> str:
        trouve = re.search(r"\b(\d{6})\b", self.messages[-1][1])
        assert trouve is not None
        return trouve.group(1)


@pytest.fixture
def sms(app: FastAPI) -> FauxSms:
    faux = FauxSms()
    app.state.expediteur_sms = faux
    return faux


async def demander_code(client: AsyncClient, telephone: str = "76 12 34 56") -> Any:
    reponse = await client.post("/api/v1/auth/mot-de-passe-oublie", json={"telephone": telephone})
    assert reponse.status_code == 202, reponse.text
    return reponse.json()


async def reinitialiser(
    client: AsyncClient, code: str, mot_de_passe: str = NOUVEAU, telephone: str = "76 12 34 56"
) -> Any:
    return await client.post(
        "/api/v1/auth/reinitialisation",
        json={"telephone": telephone, "code": code, "mot_de_passe": mot_de_passe},
    )


async def connexion(client: AsyncClient, mot_de_passe: str) -> int:
    reponse = await client.post(
        "/api/v1/auth/connexion", json={"telephone": "76 12 34 56", "mot_de_passe": mot_de_passe}
    )
    return reponse.status_code


async def test_code_par_sms_puis_nouveau_mot_de_passe(
    app: FastAPI, client: AsyncClient, sms: FauxSms
) -> None:
    compte = await inscrire(client)
    ancienne_session = compte["jeton_rafraichissement"]
    assert "un code vient d'être envoyé" in (await demander_code(client))["message"]
    [(destinataire, texte)] = sms.messages
    assert destinataire == "+22376123456"
    assert "expire dans 10 minutes" in texte and "Ne le donnez à personne" in texte
    code = sms.dernier_code()

    faux = "000000" if code != "000000" else "111111"
    assert (await reinitialiser(client, faux)).status_code == 400
    reussi = await reinitialiser(client, code)
    assert reussi.status_code == 200, reussi.text
    assert reussi.json()["utilisateur"]["telephone"] == "+22376123456"  # connecté d'office
    assert (await reinitialiser(client, code, "encore-un-autre")).status_code == 400  # usé

    assert await connexion(client, MOT_DE_PASSE) == 401
    assert await connexion(client, NOUVEAU) == 200
    # Les sessions ouvertes avant la réinitialisation sont coupées.
    vieille = await client.post(
        "/api/v1/auth/rafraichir", json={"jeton_rafraichissement": ancienne_session}
    )
    assert vieille.status_code == 401
    async with app.state.sessions() as session:
        actions = list(await session.scalars(select(JournalAudit.action)))
        empreintes = list(await session.scalars(select(CodeVerification.empreinte)))
    assert {"mot_de_passe.code_envoye", "mot_de_passe.reinitialise"} <= set(actions)
    assert code not in str(empreintes)  # seule l'empreinte du code est gardée


async def test_meme_reponse_sans_compte(client: AsyncClient, sms: FauxSms) -> None:
    inconnu = await demander_code(client, "66 00 00 01")
    await inscrire(client)
    assert await demander_code(client) == inconnu
    assert len(sms.messages) == 1  # aucun SMS vers un numéro sans compte
    invalide = await client.post("/api/v1/auth/mot-de-passe-oublie", json={"telephone": "12 34 56"})
    assert invalide.status_code == 422
    assert (await reinitialiser(client, "123456", telephone="66 00 00 01")).status_code == 400


async def test_trois_codes_par_heure_au_plus(client: AsyncClient, sms: FauxSms) -> None:
    await inscrire(client)
    for _ in range(4):
        await demander_code(client)
    assert len(sms.messages) == 3


async def test_nouveau_code_annule_le_precedent(client: AsyncClient, sms: FauxSms) -> None:
    await inscrire(client)
    await demander_code(client)
    premier = sms.dernier_code()
    await demander_code(client)
    second = sms.dernier_code()
    if premier != second:
        assert (await reinitialiser(client, premier)).status_code == 400
    assert (await reinitialiser(client, second)).status_code == 200


async def test_code_brule_apres_cinq_erreurs(client: AsyncClient, sms: FauxSms) -> None:
    await inscrire(client)
    await demander_code(client)
    code = sms.dernier_code()
    faux = [f"{(int(code) + i) % 10**6:06d}" for i in range(1, 6)]
    for essai in faux:
        assert (await reinitialiser(client, essai)).status_code == 400
    assert (await reinitialiser(client, code)).status_code == 400  # trop tard
    assert await connexion(client, MOT_DE_PASSE) == 200


async def test_code_expire(app: FastAPI, client: AsyncClient, sms: FauxSms) -> None:
    await inscrire(client)
    await demander_code(client)
    async with app.state.sessions() as session:
        passe = datetime.now(UTC) - timedelta(seconds=1)
        await session.execute(update(CodeVerification).values(expire_le=passe))
        await session.commit()
    assert (await reinitialiser(client, sms.dernier_code())).status_code == 400


async def test_compte_de_l_equipe_douze_caracteres(
    app: FastAPI, client: AsyncClient, sms: FauxSms
) -> None:
    await inscrire(client)
    async with app.state.sessions() as session:
        await session.execute(update(Utilisateur).values(roles=["boutique:admin"]))
        await session.commit()
    await demander_code(client)
    code = sms.dernier_code()
    court = await reinitialiser(client, code, "onze-carac")
    assert court.status_code == 422
    assert "12 caractères" in court.json()["detail"]
    assert (await reinitialiser(client, code, "douze-caract")).status_code == 200  # code intact


async def test_changer_son_mot_de_passe(app: FastAPI, client: AsyncClient) -> None:
    compte = await inscrire(client)
    chemin = "/api/v1/auth/mot-de-passe"
    sans_session = await client.post(chemin, json={"actuel": MOT_DE_PASSE, "nouveau": NOUVEAU})
    assert sans_session.status_code == 401
    faux = await client.post(
        chemin, json={"actuel": "pas-le-bon", "nouveau": NOUVEAU}, headers=entete(compte)
    )
    assert faux.status_code == 400
    court = await client.post(
        chemin, json={"actuel": MOT_DE_PASSE, "nouveau": "court"}, headers=entete(compte)
    )
    assert court.status_code == 422
    change = await client.post(
        chemin, json={"actuel": MOT_DE_PASSE, "nouveau": NOUVEAU}, headers=entete(compte)
    )
    assert change.status_code == 200, change.text
    assert await connexion(client, NOUVEAU) == 200
    assert await connexion(client, MOT_DE_PASSE) == 401
    async with app.state.sessions() as session:
        actions = list(await session.scalars(select(JournalAudit.action)))
    assert "mot_de_passe.change" in actions
