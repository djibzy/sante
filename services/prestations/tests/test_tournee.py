"""La tournée d'un jour se lit dans le calendrier des contrats, sans planification en base."""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from httpx import AsyncClient

from .aides import GESTION, LUNDI, TERRAIN, action, contrat, enlever, partenaire


async def tournee(client: AsyncClient, jour: date) -> Any:
    reponse = await client.get(
        "/api/v1/tournee", params={"jour": jour.isoformat()}, headers=TERRAIN
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def test_les_passages_suivent_le_calendrier(client: AsyncClient) -> None:
    pressing = await partenaire(client)
    lundi_jeudi = await contrat(client, partenaire_id=pressing["id"])
    await contrat(client, structure="Maternité Kalaban", jours_collecte=[2, 5])
    await contrat(client, structure="Cabinet fermé", fin_le="2026-11-13")
    await contrat(client, structure="Clinique pas encore ouverte", debut_le="2026-11-20")
    suspendu = await contrat(client, structure="Clinique en travaux")
    await client.patch(
        f"/api/v1/admin/contrats/{suspendu['reference']}",
        json={"statut": "suspendu"},
        headers=GESTION,
    )

    du_lundi = await tournee(client, LUNDI)
    assert du_lundi["libelle_jour"] == "Lundi 16/11/2026"
    assert [p["contrat"]["structure"] for p in du_lundi["passages"]] == ["Clinique Pasteur"]
    passage = du_lundi["passages"][0]
    assert passage["collecte"] is None and passage["au_calendrier"] is True
    assert passage["contrat"]["adresse"] == "Badalabougou, rue 100, porte 10"
    assert "tarifs" not in passage["contrat"]  # pas de prix sur la tournée
    du_mardi = await tournee(client, LUNDI + timedelta(days=1))
    assert [p["contrat"]["structure"] for p in du_mardi["passages"]] == ["Maternité Kalaban"]

    await enlever(client, lundi_jeudi["id"], blouse=6)
    du_lundi = await tournee(client, LUNDI)
    assert du_lundi["passages"][0]["collecte"]["reference"] == "BC-1001"
    assert [c["reference"] for c in du_lundi["a_deposer"]] == ["BC-1001"]
    assert du_lundi["a_rendre"] == []

    await action(client, "BC-1001", "depot")
    mercredi = await tournee(client, LUNDI + timedelta(days=2))
    assert mercredi["a_deposer"] == []
    a_rendre = mercredi["a_rendre"][0]
    assert a_rendre["reference"] == "BC-1001" and a_rendre["en_retard"] is False
    jeudi = await tournee(client, LUNDI + timedelta(days=3))
    assert jeudi["a_rendre"][0]["en_retard"] is True  # promis mercredi
    assert [p["contrat"]["structure"] for p in jeudi["passages"]] == ["Clinique Pasteur"]
    assert jeudi["passages"][0]["collecte"] is None  # le passage du jeudi reste à faire


async def test_collecte_ponctuelle_et_passage_annule(client: AsyncClient) -> None:
    sur_appel = await contrat(client, structure="Cabinet Sourire", jours_collecte=[])
    lundi_jeudi = await contrat(client)
    await client.post(
        "/api/v1/collectes/ponctuelles",
        json={"contrat_id": sur_appel["id"], "prevue_le": LUNDI.isoformat()},
        headers=GESTION,
    )
    await client.post(
        "/api/v1/tournee/annulations",
        json={"contrat_id": lundi_jeudi["id"], "jour": LUNDI.isoformat(), "motif": "Fermé"},
        headers=TERRAIN,
    )
    passages = {p["contrat"]["structure"]: p for p in (await tournee(client, LUNDI))["passages"]}
    assert passages["Cabinet Sourire"]["au_calendrier"] is False
    assert passages["Cabinet Sourire"]["collecte"]["statut"] == "prevue"
    assert passages["Clinique Pasteur"]["collecte"]["statut"] == "annulee"
    # Enlevé malgré tout : la collecte comptée passe devant l'annulation.
    await enlever(client, lundi_jeudi["id"], drap=2)
    passages = {p["contrat"]["structure"]: p for p in (await tournee(client, LUNDI))["passages"]}
    assert passages["Clinique Pasteur"]["collecte"]["statut"] == "enlevee"


async def test_tournee_du_jour_par_defaut(client: AsyncClient) -> None:
    reponse = await client.get("/api/v1/tournee", headers=TERRAIN)
    assert reponse.status_code == 200
    assert reponse.json()["jour"] == datetime.now(UTC).date().isoformat()
