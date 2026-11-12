from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select, text

from comptes.entretien import entretenir
from comptes.models import CodeVerification, JetonRafraichissement, JournalAudit

from .conftest import inscrire


async def sql(app: FastAPI, requete: str) -> None:
    async with app.state.sessions() as session:
        await session.execute(text(requete))
        await session.commit()


async def compter(app: FastAPI, modele: type) -> int:
    async with app.state.sessions() as session:
        return int(await session.scalar(select(func.count()).select_from(modele)) or 0)


async def test_durees_de_conservation(app: FastAPI, client: AsyncClient) -> None:
    await inscrire(client)
    await inscrire(client, telephone="66 12 34 57", nom="Moussa Keïta")
    await client.post("/api/v1/auth/mot-de-passe-oublie", json={"telephone": "76 12 34 56"})
    await client.post("/api/v1/auth/mot-de-passe-oublie", json={"telephone": "66 12 34 57"})
    # Un code d'avant-hier, une session expirée depuis 40 jours, un journal de 2 ans.
    await sql(
        app,
        "UPDATE codes_verification SET cree_le = now() - interval '2 days' "
        "WHERE utilisateur_id = (SELECT id FROM utilisateurs WHERE telephone = '+22376123456')",
    )
    await sql(
        app,
        "UPDATE jetons_rafraichissement SET expire_le = now() - interval '40 days' "
        "WHERE utilisateur_id = (SELECT id FROM utilisateurs WHERE telephone = '+22376123456')",
    )
    await sql(
        app,
        "UPDATE journal_audit SET adresse_ip = '196.200.1.1', cree_le = now() - interval '2 years' "
        "WHERE action = 'compte.cree'",
    )

    bilan = await entretenir(app.state.sessions)
    assert (bilan.codes, bilan.sessions, bilan.adresses_ip) == (1, 1, 2)
    assert await compter(app, CodeVerification) == 1
    assert await compter(app, JetonRafraichissement) == 1
    async with app.state.sessions() as session:
        ips = set(
            await session.scalars(
                select(JournalAudit.adresse_ip).where(JournalAudit.action == "compte.cree")
            )
        )
    assert ips == {None}
    assert (await entretenir(app.state.sessions)).codes == 0  # rien de plus le lendemain
