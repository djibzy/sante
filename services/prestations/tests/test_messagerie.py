"""Le fil d'un contrat : lien de suivi, messages, SMS sans insistance, retrait, conservation."""

from datetime import timedelta

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, update

from prestations import calendrier
from prestations.conservation import conserver
from prestations.models import Contrat, JournalAudit, Message

from .aides import GESTION, contrat, journal, sms

EQUIPE = "+22376000099"


async def _lien(app: FastAPI, client: AsyncClient) -> tuple[str, str]:
    app.state.parametres.url_publique = "https://prestations.exemple.ml"
    app.state.parametres.telephones_equipe = [EQUIPE]
    ct = await contrat(client)
    reponse = await client.post(
        f"/api/v1/admin/contrats/{ct['reference']}/lien-de-suivi", headers=GESTION
    )
    assert reponse.status_code == 200, reponse.text
    lien = reponse.json()["lien"]
    cle = lien.split("cle=")[1]
    return ct["reference"], cle


async def test_lien_de_suivi_et_acces(app: FastAPI, client: AsyncClient) -> None:
    reference, cle = await _lien(app, client)
    envoyes = await sms(app)
    assert envoyes[-1].destinataire == "+22376000001"
    assert f"https://prestations.exemple.ml/contrat/{reference}?cle={cle}" in envoyes[-1].message

    base = f"/api/v1/contrat/{reference}"
    assert (await client.get(f"{base}/fil", params={"cle": cle})).status_code == 200
    assert (await client.get(f"{base}/fil")).status_code == 404
    assert (await client.get(f"{base}/fil", params={"cle": "mauvaise"})).status_code == 404
    # Un nouveau lien remplace l'ancien.
    await client.post(f"/api/v1/admin/contrats/{reference}/lien-de-suivi", headers=GESTION)
    assert (await client.get(f"{base}/fil", params={"cle": cle})).status_code == 404
    # La clé n'est jamais gardée en clair.
    async with app.state.sessions() as session:
        empreinte = await session.scalar(select(Contrat.empreinte_cle_suivi))
    assert empreinte and cle not in empreinte
    assert "contrat.lien_suivi" in await journal(app)


async def test_echange_et_sms(app: FastAPI, client: AsyncClient) -> None:
    reference, cle = await _lien(app, client)
    base, gestion = f"/api/v1/contrat/{reference}", f"/api/v1/admin/contrats/{reference}"
    avant = len(await sms(app))

    envoi = await client.post(
        f"{base}/messages", params={"cle": cle}, json={"texte": "  Bonjour  "}
    )
    assert envoi.status_code == 201
    assert envoi.json()["texte"] == "Bonjour"
    notifies = (await sms(app))[avant:]
    assert [n.destinataire for n in notifies] == [EQUIPE]
    assert "Bonjour" not in notifies[0].message  # jamais le texte dans un SMS

    # Un second message sans réponse : pas de second SMS.
    await client.post(f"{base}/messages", params={"cle": cle}, json={"texte": "Un autre"})
    assert len((await sms(app))[avant:]) == 1

    liste = await client.get("/api/v1/admin/contrats", headers=GESTION)
    assert liste.json()[0]["messages_a_lire"] == 2
    fil = (await client.get(f"{gestion}/fil", headers=GESTION)).json()
    assert fil["a_lire"] == 2
    await client.post(f"{gestion}/messages/lecture", headers=GESTION)
    assert (await client.get("/api/v1/admin/contrats", headers=GESTION)).json()[0][
        "messages_a_lire"
    ] == 0

    reponse = await client.post(f"{gestion}/messages", headers=GESTION, json={"texte": "Reçu"})
    assert reponse.json()["nom_auteur"] == "Gestion"
    vu_par_la_structure = (await client.get(f"{base}/fil", params={"cle": cle})).json()
    assert vu_par_la_structure["a_lire"] == 1
    assert vu_par_la_structure["entrees"][-1]["nom_auteur"] == ""  # le nom reste à l'équipe
    assert (await sms(app))[-1].destinataire == "+22376000001"
    await client.post(f"{base}/messages/lecture", params={"cle": cle})
    lu = (await client.get(f"{gestion}/fil", headers=GESTION)).json()
    assert lu["entrees"][-1]["lu_le"] is not None
    assert lu["entrees"][0]["lu_le"] is not None


async def test_retrait_et_limites(app: FastAPI, client: AsyncClient) -> None:
    reference, cle = await _lien(app, client)
    base, gestion = f"/api/v1/contrat/{reference}", f"/api/v1/admin/contrats/{reference}"
    vide = await client.post(f"{base}/messages", params={"cle": cle}, json={"texte": "   "})
    assert vide.status_code == 422
    envoi = await client.post(
        f"{base}/messages", params={"cle": cle}, json={"texte": "Le patient X a le paludisme"}
    )
    identifiant = envoi.json()["id"]
    sans_motif = await client.post(
        f"{gestion}/messages/{identifiant}/retrait", headers=GESTION, json={"motif": "x"}
    )
    assert sans_motif.status_code == 422
    retrait = await client.post(
        f"{gestion}/messages/{identifiant}/retrait",
        headers=GESTION,
        json={"motif": "Information de santé"},
    )
    assert retrait.status_code == 200
    assert retrait.json()["texte"] == "" and retrait.json()["retire"]
    deux = await client.post(
        f"{gestion}/messages/{identifiant}/retrait", headers=GESTION, json={"motif": "encore"}
    )
    assert deux.status_code == 409
    fil = (await client.get(f"{base}/fil", params={"cle": cle})).json()
    assert fil["entrees"][0]["retire"] and fil["entrees"][0]["motif_retrait"] == ""
    assert fil["a_lire"] == 0
    assert "message.retire" in await journal(app)
    async with app.state.sessions() as session:
        assert await session.scalar(select(Message.texte)) == ""

    for numero in range(19):  # 20 messages par jour au plus
        await client.post(f"{base}/messages", params={"cle": cle}, json={"texte": f"m{numero}"})
    trop = await client.post(f"{base}/messages", params={"cle": cle}, json={"texte": "de trop"})
    assert trop.status_code == 429

    sans_role = await client.get(f"{gestion}/fil")
    assert sans_role.status_code == 401


async def test_contrat_termine_et_conservation(app: FastAPI, client: AsyncClient) -> None:
    reference, cle = await _lien(app, client)
    base, gestion = f"/api/v1/contrat/{reference}", f"/api/v1/admin/contrats/{reference}"
    await client.post(f"{base}/messages", params={"cle": cle}, json={"texte": "Bonjour"})
    await client.patch(gestion, headers=GESTION, json={"statut": "termine", "fin_le": "2026-11-20"})
    ferme = await client.post(f"{base}/messages", params={"cle": cle}, json={"texte": "Encore"})
    assert ferme.status_code == 409
    assert (await client.get(f"{base}/fil", params={"cle": cle})).json()["ouvert"] is False

    bilan = await conserver(app.state.sessions)
    assert bilan.messages == 0  # fini depuis moins de 3 ans
    async with app.state.sessions() as session:
        ancien = calendrier.maintenant().date() - timedelta(days=3 * 365 + 10)
        await session.execute(update(Contrat).values(fin_le=ancien, debut_le=ancien))
        await session.commit()
    bilan = await conserver(app.state.sessions)
    assert bilan.messages == 1
    async with app.state.sessions() as session:
        assert await session.scalar(select(Message.id)) is None
        assert await session.scalar(select(JournalAudit.id)) is not None
