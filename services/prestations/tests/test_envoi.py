"""Processus d'envoi des SMS et durées de conservation."""

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, update

from prestations.conservation import conserver
from prestations.envoi import tour
from prestations.models import Demande, JournalAudit, Notification

from .aides import GESTION, sms


class Expediteur:
    def __init__(self, echec: bool = False) -> None:
        self.envoyes: list[tuple[str, str]] = []
        self.echec = echec

    async def envoyer(self, destinataire: str, message: str) -> str | None:
        if self.echec:
            raise RuntimeError("Réseau indisponible")
        self.envoyes.append((destinataire, message))
        return f"sms-{len(self.envoyes)}"


DEMANDE = {
    "structure": "Clinique du Fleuve",
    "type_structure": "clinique",
    "contact": "Awa Traoré",
    "telephone": "76 12 34 56",
    "quartier": "Badalabougou",
}


async def test_envoi_et_reprises(app: FastAPI, client: AsyncClient) -> None:
    await client.post("/api/v1/demandes", json=DEMANDE)
    en_panne = Expediteur(echec=True)
    assert await tour(app.state.sessions, en_panne) == 1
    notification = (await sms(app))[0]
    assert (notification.etat, notification.tentatives) == ("a_envoyer", 1)
    assert notification.derniere_erreur == "RuntimeError: Réseau indisponible"
    assert await tour(app.state.sessions, Expediteur()) == 0  # reprise dans deux minutes

    async with app.state.sessions() as session:
        await session.execute(update(Notification).values(prochain_essai=datetime.now(UTC)))
        await session.commit()
    expediteur = Expediteur()
    assert await tour(app.state.sessions, expediteur) == 1
    assert expediteur.envoyes[0][0] == "+22376123456"
    envoye = (await sms(app))[0]
    assert (envoye.etat, envoye.identifiant_fournisseur) == ("envoyee", "sms-1")


async def test_durees_de_conservation(app: FastAPI, client: AsyncClient) -> None:
    await client.post("/api/v1/demandes", json=DEMANDE)
    await client.post("/api/v1/demandes", json={**DEMANDE, "structure": "Cabinet Sourire"})
    await client.patch(
        "/api/v1/admin/demandes/DE-101", json={"statut": "sans_suite"}, headers=GESTION
    )
    await client.patch(
        "/api/v1/admin/demandes/DE-102", json={"notes_equipe": "À rappeler"}, headers=GESTION
    )
    il_y_a_deux_ans = datetime.now(UTC) - timedelta(days=730)
    async with app.state.sessions() as session:
        await session.execute(update(Demande).values(modifie_le=il_y_a_deux_ans))
        await session.execute(update(Notification).values(cree_le=il_y_a_deux_ans))
        await session.execute(update(JournalAudit).values(cree_le=il_y_a_deux_ans))
        await session.commit()

    bilan = await conserver(app.state.sessions)
    assert (bilan.demandes, bilan.sms, bilan.adresses_ip) == (1, 2, 4)
    async with app.state.sessions() as session:
        restantes = list(await session.scalars(select(Demande.structure)))
        adresses = set(await session.scalars(select(JournalAudit.adresse_ip)))
    assert restantes == ["Cabinet Sourire"]  # en cours : gardée
    assert adresses == {None}
