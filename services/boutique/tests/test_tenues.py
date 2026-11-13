"""Tenues proposées : composées par l'équipe, montrées aux clients avec leurs pièces du moment."""

from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from boutique.models import JournalAudit

from .aides import fiche
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
BASE = "/api/v1/admin/tenues-proposees"


async def proposees(client: AsyncClient, **filtres: str) -> Any:
    reponse = await client.get("/api/v1/tenues-proposees", params=filtres)
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def piece(client: AsyncClient, place: str, slug: str, couleur: str | None) -> dict[str, Any]:
    return {"piece": place, "produit_id": (await fiche(client, slug))["id"], "couleur": couleur}


async def test_tenues_de_demonstration(client: AsyncClient) -> None:
    tenues = await proposees(client)
    assert [t["nom"] for t in tenues] == [
        "La tenue du bloc",
        "La tenue de la maternité",
        "La tenue des urgences",
        "La tenue de l'officine",
    ]
    bloc = tenues[0]
    assert [(p["piece"], p["produit_slug"], p["couleur"], p["hex"]) for p in bloc["pieces"]] == [
        ("haut", "tunique-col-v", "Vert bloc", "#2e8b6e"),
        ("bas", "pantalon-unisexe", "Vert bloc", "#2e8b6e"),
        ("chaussures", "sabots-de-travail", None, None),
        ("calot", "calot-wax", "Wax bleu", "#2b5fb3"),
    ]
    assert bloc["total"] == sum(p["prix"] for p in bloc["pieces"]) == 9_500 + 7_500 + 9_000 + 2_500
    maternite = await proposees(client, metier="sage-femme")
    assert [t["nom"] for t in maternite] == ["La tenue de la maternité"]


async def test_l_equipe_propose_une_tenue(app: FastAPI, client: AsyncClient) -> None:
    pieces = [
        await piece(client, "bas", "pantalon-unisexe", "Bleu roi"),
        await piece(client, "haut", "tunique-col-v", "Bleu roi"),
    ]
    corps = {"nom": "La tenue du laboratoire", "metier": "laboratoire", "pieces": pieces}
    creee = await client.post(BASE, json=corps, headers=ADMIN)
    assert creee.status_code == 201, creee.text
    tenue = creee.json()
    assert [p["piece"] for p in tenue["pieces"]] == ["haut", "bas"]  # rangées par place
    assert (tenue["total"], tenue["est_active"], tenue["incomplete"]) == (17_000, True, False)
    assert [t["nom"] for t in await proposees(client)][-1] == "La tenue du laboratoire"

    # Masquée : plus montrée aux clients, toujours visible par l'équipe.
    masquee = await client.patch(
        f"{BASE}/{tenue['id']}", json={"est_active": False, "nom": "Labo, en bleu"}, headers=ADMIN
    )
    assert masquee.json()["nom"] == "Labo, en bleu"
    assert "Labo, en bleu" not in [t["nom"] for t in await proposees(client)]
    toutes = (await client.get(BASE, headers=ADMIN)).json()
    assert "Labo, en bleu" in [t["nom"] for t in toutes]

    assert (await client.delete(f"{BASE}/{tenue['id']}", headers=ADMIN)).status_code == 204
    assert (await client.delete(f"{BASE}/{tenue['id']}", headers=ADMIN)).status_code == 404
    async with app.state.sessions() as session:
        actions = list(
            await session.scalars(
                select(JournalAudit.action).where(JournalAudit.objet_type == "tenue_proposee")
            )
        )
    assert actions == ["tenue.proposee", "tenue.modifiee", "tenue.retiree"]


async def test_pieces_verifiees(client: AsyncClient) -> None:
    haut = await piece(client, "haut", "tunique-col-v", "Bleu roi")

    async def refus(pieces: list[dict[str, Any]]) -> str:
        reponse = await client.post(BASE, json={"nom": "Essai", "pieces": pieces}, headers=ADMIN)
        assert reponse.status_code == 422, reponse.text
        detail = reponse.json()["detail"]
        return detail if isinstance(detail, str) else str(detail)

    assert "Jaune" in await refus([{**haut, "couleur": "Jaune"}, haut | {"piece": "dessus"}])
    assert "Une seule pièce" in await refus([haut, haut])
    kit = await piece(client, "kit-hygiene", "kit-hygiene", None)
    assert await refus([haut, {**kit, "piece": "bas"}])  # pas une tenue
    gants = await piece(client, "bas", "gants-steriles", None)
    assert await refus([haut, gants])  # article du pharmacien
    assert await refus([haut])  # deux pièces au moins

    assert (await client.post(BASE, json={"nom": "Essai", "pieces": [haut]})).status_code == 401
    atelier = jeton(["boutique:atelier"])
    assert (await client.get(BASE, headers=atelier)).status_code == 403


async def test_piece_retiree_de_la_vente(client: AsyncClient) -> None:
    urgences = (await proposees(client, metier="infirmier"))[0]
    baskets = await fiche(client, "baskets-soignant")
    pantalon = await fiche(client, "pantalon-stretch-femme")
    for produit in (baskets, pantalon):
        retrait = await client.patch(
            f"/api/v1/admin/produits/{produit['id']}", json={"est_actif": False}, headers=ADMIN
        )
        assert retrait.status_code == 200, retrait.text
    # Une seule pièce restante : la tenue n'est plus montrée, l'équipe la voit incomplète.
    assert urgences["nom"] not in [t["nom"] for t in await proposees(client)]
    [vue] = [t for t in (await client.get(BASE, headers=ADMIN)).json() if t["id"] == urgences["id"]]
    assert (vue["incomplete"], len(vue["pieces"])) == (True, 1)
