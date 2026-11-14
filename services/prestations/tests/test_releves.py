"""Relevés du mois : montant dû par chaque structure, coût des partenaires, marge, PDF, CSV."""

import io
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy import update

from prestations.models import Collecte

from .aides import GESTION, TERRAIN, action, contrat, enlever, journal, partenaire, rendre


async def rendue_le(app: FastAPI, reference: str, quand: datetime) -> None:
    """Place le retour d'une collecte dans un mois donné (les tests ne dépendent pas du jour)."""
    async with app.state.sessions() as session:
        await session.execute(
            update(Collecte)
            .where(Collecte.numero == int(reference.removeprefix("BC-")))
            .values(rendue_le=quand)
        )
        await session.commit()


async def tour(
    client: AsyncClient, contrat_id: str, poids: float | None = None, **quantites: int
) -> str:
    """Enlève, dépose et rend ; les quantités rendues sont celles enlevées, moins un drap s'il
    y en a (une pièce manquante)."""
    jour = datetime(2026, 11, 16 + len(await _collectes(client)), tzinfo=UTC).date()
    enlevee = await enlever(client, contrat_id, jour=jour, **quantites)
    reference = str(enlevee["reference"])
    await action(client, reference, "depot", {"poids_kg": poids} if poids else {})
    rendues = {a: n - (1 if a == "drap" else 0) for a, n in quantites.items()}
    await rendre(client, reference, **rendues)
    return reference


async def _collectes(client: AsyncClient) -> list[Any]:
    page = (await client.get("/api/v1/admin/collectes", headers=GESTION)).json()
    return list(page["elements"])


async def test_releve_a_la_piece(app: FastAPI, client: AsyncClient) -> None:
    pressing = await partenaire(client, tarifs={"blouse": 300, "drap": 400})  # pas de taie
    signe = await contrat(client, partenaire_id=pressing["id"])
    premiere = await tour(client, signe["id"], blouse=10, drap=20)
    # Hausse du tarif du contrat : la collecte suivante est facturée au nouveau prix.
    await client.patch(
        "/api/v1/admin/contrats/CT-101",
        json={"tarifs": {"blouse": 600, "drap": 700, "taie": 250}},
        headers=GESTION,
    )
    seconde = await tour(client, signe["id"], blouse=5, taie=4)
    decembre = await tour(client, signe["id"], blouse=1)
    await rendue_le(app, premiere, datetime(2026, 11, 18, 10, tzinfo=UTC))
    await rendue_le(app, seconde, datetime(2026, 11, 30, 23, 59, tzinfo=UTC))
    await rendue_le(app, decembre, datetime(2026, 12, 1, 0, 0, tzinfo=UTC))

    releve = (
        await client.get("/api/v1/admin/contrats/CT-101/releves/2026-11", headers=GESTION)
    ).json()
    assert releve["libelle_mois"] == "novembre 2026"
    assert [c["reference"] for c in releve["collectes"]] == ["BC-1001", "BC-1002"]
    assert [
        (ligne["libelle"], ligne["prix_unitaire"], ligne["rendues"], ligne["montant"])
        for ligne in releve["lignes"]
    ] == [
        ("Blouse", 500, 10, 5_000),
        ("Blouse", 600, 5, 3_000),
        ("Drap", 700, 19, 13_300),  # la pièce manquante n'est pas facturée
        ("Taie d'oreiller", 250, 4, 1_000),
    ]
    assert releve["pieces_enlevees"] == 39 and releve["pieces_rendues"] == 38
    assert releve["pieces_manquantes"] == 1
    assert releve["forfait"] is None
    assert releve["total"] == 22_300
    # Le partenaire : 15 blouses à 300, 19 draps à 400 ; aucun tarif pour les taies.
    assert releve["cout_partenaires"] == 15 * 300 + 19 * 400
    assert releve["cout_incomplet"] is True

    synthese = (await client.get("/api/v1/admin/releves/2026-11", headers=GESTION)).json()
    ligne = synthese["contrats"][0]
    assert (ligne["chiffre"], ligne["cout"], ligne["marge"]) == (22_300, 12_100, 10_200)
    assert synthese["partenaires"] == [
        {
            "id": pressing["id"],
            "nom": "Pressing du Fleuve",
            "mode_tarif": "piece",
            "collectes": 2,
            "pieces": 38,
            "poids_kg": 0.0,
            "cout": 12_100,
            "cout_incomplet": True,
        }
    ]
    assert synthese["en_cours"] == 0
    assert (synthese["chiffre"], synthese["marge"]) == (22_300, 10_200)


async def test_forfait_volume_compris_et_partenaire_au_kilo(
    app: FastAPI, client: AsyncClient
) -> None:
    kilo = await partenaire(client, nom="Blanchisserie Djoliba", mode_tarif="kg", tarif_kg=600)
    signe = await contrat(
        client,
        structure="Maternité Kalaban",
        partenaire_id=kilo["id"],
        formule="forfait",
        forfait_mensuel=150_000,
        pieces_incluses=30,
        prix_piece_supplementaire=300,
        tarifs={},
    )
    sans_linge = await contrat(
        client, structure="Cabinet Sourire", formule="forfait", forfait_mensuel=40_000
    )
    await contrat(
        client,
        structure="Ancien client",
        formule="forfait",
        forfait_mensuel=90_000,
        debut_le="2026-09-01",
        fin_le="2026-10-31",
    )
    reference = await tour(client, signe["id"], poids=12.3, drap=26, serviette=10)
    await rendue_le(app, reference, datetime(2026, 11, 20, tzinfo=UTC))
    # Du linge encore dehors, pas compté dans le mois.
    await enlever(client, signe["id"], jour=datetime(2026, 11, 28).date(), drap=7)

    releve = (
        await client.get(
            f"/api/v1/admin/contrats/{signe['reference']}/releves/2026-11", headers=GESTION
        )
    ).json()
    assert releve["pieces_rendues"] == 35
    assert releve["forfait"] == 150_000
    assert releve["pieces_supplementaires"] == 5
    assert releve["montant_supplement"] == 1_500
    assert releve["total"] == 151_500
    assert releve["cout_partenaires"] == 7_380  # 12,3 kg à 600 FCFA
    assert releve["cout_incomplet"] is False

    synthese = (await client.get("/api/v1/admin/releves/2026-11", headers=GESTION)).json()
    par_structure = {c["structure"]: c for c in synthese["contrats"]}
    assert set(par_structure) == {"Maternité Kalaban", "Cabinet Sourire"}  # l'ancien est fini
    assert par_structure["Cabinet Sourire"]["chiffre"] == 40_000  # forfait dû sans linge
    assert par_structure["Cabinet Sourire"]["collectes"] == 0
    assert synthese["chiffre"] == 191_500
    assert synthese["cout"] == 7_380
    assert synthese["partenaires"][0]["poids_kg"] == 12.3
    assert synthese["en_cours"] == 7
    vide = (
        await client.get(
            f"/api/v1/admin/contrats/{sans_linge['reference']}/releves/2026-11", headers=GESTION
        )
    ).json()
    assert vide["total"] == 40_000 and vide["lignes"] == []


async def test_pdf_et_csv_pour_la_structure_et_le_comptable(
    app: FastAPI, client: AsyncClient
) -> None:
    pressing = await partenaire(client)
    signe = await contrat(client, partenaire_id=pressing["id"])
    reference = await tour(client, signe["id"], blouse=10, drap=20)
    await rendue_le(app, reference, datetime(2026, 11, 18, tzinfo=UTC))

    pdf = await client.get("/api/v1/admin/contrats/CT-101/releves/2026-11.pdf", headers=GESTION)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert 'filename="releve-CT-101-2026-11.pdf"' in pdf.headers["content-disposition"]
    texte = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.content)).pages)
    for attendu in (
        "Relevé mensuel",
        "novembre 2026",
        "Clinique Pasteur",
        "BC-1001",
        "Total du mois",
        "18 300 FCFA",
        "1 pièce(s) manquante(s)",
        "Collectes : lundi et jeudi",
    ):
        assert attendu in texte, attendu
    assert "Coût" not in texte and "marge" not in texte.lower()  # jamais pour la structure

    tableur = await client.get("/api/v1/admin/releves/2026-11.csv", headers=GESTION)
    assert tableur.status_code == 200
    contenu = tableur.content.decode("utf-8")
    assert contenu.startswith("﻿Contrat;Structure;Formule;Collectes;Pièces rendues;")
    assert "CT-101;Clinique Pasteur;à la pièce;1;29;1;18300;" in contenu
    assert await journal(app) == [
        "partenaire.ajoute",
        "contrat.cree",
        "collecte.enlevee",
        "collecte.deposee",
        "collecte.rendue",
        "releve.pdf",
        "releve.csv",
    ]

    assert (await client.get("/api/v1/admin/releves/2026-13", headers=GESTION)).status_code == 422
    assert (await client.get("/api/v1/admin/releves/2026-11", headers=TERRAIN)).status_code == 403


async def test_prix_a_fixer_puis_tarifs_du_moment(app: FastAPI, client: AsyncClient) -> None:
    pressing = await partenaire(client, tarifs={"blouse": 300})
    signe = await contrat(client, partenaire_id=pressing["id"], tarifs={"blouse": 500})
    reference = await tour(client, signe["id"], blouse=2, serviette=3)
    await rendue_le(app, reference, datetime(2026, 11, 18, tzinfo=UTC))
    chemin = "/api/v1/admin/contrats/CT-101/releves/2026-11"

    releve = (await client.get(chemin, headers=GESTION)).json()
    assert releve["prix_manquants"] is True and releve["cout_incomplet"] is True
    serviette = next(ligne for ligne in releve["lignes"] if ligne["article"] == "serviette")
    assert (serviette["prix_unitaire"], serviette["montant"]) == (None, 0)
    assert releve["total"] == 1_000
    pdf = await client.get(f"{chemin}.pdf", headers=GESTION)
    texte = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "à fixer" in texte

    # Les tarifs manquants sont ajoutés : le relevé les prend, sans toucher aux prix relevés.
    await client.patch(
        "/api/v1/admin/contrats/CT-101",
        json={"tarifs": {"blouse": 650, "serviette": 200}},
        headers=GESTION,
    )
    await client.patch(
        f"/api/v1/admin/partenaires/{pressing['id']}",
        json={"tarifs": {"blouse": 300, "serviette": 100}},
        headers=GESTION,
    )
    releve = (await client.get(chemin, headers=GESTION)).json()
    assert releve["prix_manquants"] is False and releve["cout_incomplet"] is False
    assert [(ligne["article"], ligne["prix_unitaire"]) for ligne in releve["lignes"]] == [
        ("blouse", 500),  # relevé à l'enlèvement : la hausse ne s'applique pas
        ("serviette", 200),
    ]
    assert releve["total"] == 2 * 500 + 3 * 200
    assert releve["cout_partenaires"] == 2 * 300 + 3 * 100
