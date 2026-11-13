from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy import select, update

from boutique.models import Commande, JournalAudit, Notification

from .aides import ADRESSE, commander, ligne, zone
from .conftest import jeton

ADMIN = jeton(["boutique:admin"], nom="Équipe Bibou")


def dans(jours: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=jours)).isoformat()


async def statut(client: AsyncClient, reference: str, nouveau: str, **autres: Any) -> Any:
    return await client.post(
        f"/api/v1/admin/commandes/{reference}/statut",
        json={"statut": nouveau, **autres},
        headers=ADMIN,
    )


async def demander_devis(client: AsyncClient) -> dict[str, Any]:
    reponse = await client.post(
        "/api/v1/devis",
        json={
            "etablissement": "CSCom de Banconi",
            "client": {"nom": "Dr Oumar Sangaré", "telephone": "66 44 22 11"},
            "email": "cscom.banconi@exemple.ml",
            "lignes": [
                await ligne(client, "blouse-medicale-brodee", "M", 30, "CSCom de Banconi"),
                await ligne(client, "tshirt-de-campagne", "L", 100),
            ],
            "note": "Pour la campagne de vaccination de décembre",
        },
    )
    assert reponse.status_code == 201, reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees


async def test_gestion_reservee_a_l_equipe(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/admin/commandes")).status_code == 401
    assert (await client.get("/api/v1/admin/commandes", headers=jeton())).status_code == 403


async def test_file_des_commandes_et_recherche(client: AsyncClient) -> None:
    kit = [await ligne(client, "kit-hygiene")]
    await commander(client, kit, telephone="76 12 34 56")
    await commander(client, kit, telephone="65 11 22 33")
    await demander_devis(client)

    async def lister(**params: Any) -> list[str]:
        page = (await client.get("/api/v1/admin/commandes", params=params, headers=ADMIN)).json()
        return [c["reference"] for c in page["elements"]]

    assert await lister() == ["BB-1003", "BB-1002", "BB-1001"]
    assert await lister(statut="devis_demande") == ["BB-1003"]
    assert await lister(statut=["en_attente", "devis_demande"]) == ["BB-1003", "BB-1002", "BB-1001"]
    assert await lister(q="BB-1002") == ["BB-1002"]
    assert await lister(q="banconi") == ["BB-1003"]
    assert await lister(q="65 11 22 33") == ["BB-1002"]
    assert await lister(par_page=2, page=2) == ["BB-1001"]


async def test_cycle_complet_livraison_et_encaissement(app: FastAPI, client: AsyncClient) -> None:
    livraison = {"mode": "livraison", "zone_id": await zone(client), "adresse": ADRESSE}
    creee = await commander(client, [await ligne(client, "kit-hygiene")], livraison=livraison)
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]

    confirmee = (await statut(client, reference, "confirmee", note="Confirmée au téléphone")).json()
    assert confirmee["date_promise"] == dans(7 + 1)
    assert confirmee["passages_possibles"] == ["en_preparation", "prete", "annulee"]
    note = "Client injoignable ce matin"
    interne = await statut(client, reference, "en_preparation", note=note, visible_client=False)
    assert interne.status_code == 200
    for etape in ("prete", "en_livraison", "livree"):
        assert (await statut(client, reference, etape)).status_code == 200
    retour = await statut(client, reference, "confirmee")
    assert retour.status_code == 409

    vue_client = (await client.get(f"/api/v1/suivi/{reference}", params={"cle": cle})).json()
    assert [e["statut"] for e in vue_client["historique"]] == [
        "en_attente",
        "confirmee",
        "prete",
        "en_livraison",
        "livree",
    ]
    assert note not in str(vue_client)

    paiement = await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": 8_500, "moyen": "orange_money", "reference": "OM2611.1234.A5"},
        headers=ADMIN,
    )
    assert paiement.status_code == 200
    detail = paiement.json()
    assert (detail["montant_paye"], detail["reste_a_payer"]) == (8_500, 0)
    assert detail["paiements"][0]["moyen"] == "orange_money"
    assert len(detail["historique_complet"]) == 6
    trop = await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": 100, "moyen": "especes"},
        headers=ADMIN,
    )
    assert trop.status_code == 422

    async with app.state.sessions() as session:
        actions = (
            await session.execute(
                select(JournalAudit.action).where(JournalAudit.objet_id == reference)
            )
        ).scalars()
        assert sorted(actions) == sorted(
            ["commande.creee", "commande.encaissement", *["commande.statut"] * 5]
        )


async def test_une_commande_a_retirer_ne_part_pas_en_livraison(client: AsyncClient) -> None:
    reference = (await commander(client, [await ligne(client, "affiche-a2")]))["commande"][
        "reference"
    ]
    await statut(client, reference, "confirmee")
    await statut(client, reference, "prete")
    assert (await statut(client, reference, "en_livraison")).status_code == 409
    assert (await statut(client, reference, "livree")).status_code == 200


async def test_devis_de_la_demande_a_l_acceptation(client: AsyncClient) -> None:
    demande = await demander_devis(client)
    devis, cle = demande["commande"], demande["cle_suivi"]
    reference = devis["reference"]
    assert (devis["statut"], devis["est_devis"], devis["devis_disponible"]) == (
        "devis_demande",
        True,
        False,
    )
    assert devis["total"] == 30 * 12_500 + 100 * 3_500
    pas_encore = await client.get(f"/api/v1/suivi/{reference}/devis.pdf", params={"cle": cle})
    assert pas_encore.status_code == 409

    blouse = await ligne(client, "blouse-medicale-brodee", "M", 30, "CSCom de Banconi")
    tshirt = await ligne(client, "tshirt-de-campagne", "L", 100)
    emission = await client.put(
        f"/api/v1/admin/commandes/{reference}/devis",
        json={
            "lignes": [
                {**blouse, "prix_unitaire": 11_000},
                tshirt,
                {
                    "libelle": "Broderie du logo du CSCom (forfait)",
                    "quantite": 1,
                    "prix_unitaire": 25_000,
                },
            ],
            "remise": 5_000,
            "validite_jours": 15,
            "note": "Prix professionnel appliqué aux blouses",
        },
        headers=ADMIN,
    )
    assert emission.status_code == 200, emission.text
    envoye = emission.json()
    assert envoye["statut"] == "devis_envoye"
    assert envoye["total"] == 330_000 + 350_000 + 25_000 - 5_000
    assert envoye["devis_valable_jusqu_au"] == dans(15)
    assert envoye["peut_accepter"] is True

    pdf = await client.get(f"/api/v1/suivi/{reference}/devis.pdf", params={"cle": cle})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    texte = " ".join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    texte = texte.replace("\xa0", " ")
    for attendu in (
        reference,
        "CSCom de Banconi",
        "Broderie du logo",
        "700 000 FCFA",
        "sept cent mille francs CFA",
        "+223 66 44 22 11",
    ):
        assert attendu in texte, attendu
    admin_pdf = await client.get(f"/api/v1/admin/commandes/{reference}/devis.pdf", headers=ADMIN)
    assert admin_pdf.status_code == 200

    acceptation = await client.post(f"/api/v1/suivi/{reference}/acceptation", params={"cle": cle})
    assert acceptation.status_code == 200
    acceptee = acceptation.json()
    assert acceptee["statut"] == "confirmee" and acceptee["est_devis"] is False
    assert acceptee["date_promise"] == dans(14)  # t-shirts imprimés : 14 jours, retrait
    assert acceptee["historique"][-1]["note"] == "Devis accepté par le client"
    again = await client.post(f"/api/v1/suivi/{reference}/acceptation", params={"cle": cle})
    assert again.status_code == 409
    correction = await client.put(
        f"/api/v1/admin/commandes/{reference}/devis", json={"lignes": [tshirt]}, headers=ADMIN
    )
    assert correction.status_code == 409


async def test_un_devis_expire_ne_s_accepte_plus(app: FastAPI, client: AsyncClient) -> None:
    demande = await demander_devis(client)
    reference, cle = demande["commande"]["reference"], demande["cle_suivi"]
    tshirt = await ligne(client, "tshirt-de-campagne", "L", 100)
    await client.put(
        f"/api/v1/admin/commandes/{reference}/devis",
        json={"lignes": [tshirt], "validite_jours": 1},
        headers=ADMIN,
    )
    async with app.state.sessions() as session:
        hier = datetime.now(UTC).date() - timedelta(days=1)
        await session.execute(update(Commande).values(devis_valable_jusqu_au=hier))
        await session.commit()
    suivi = (await client.get(f"/api/v1/suivi/{reference}", params={"cle": cle})).json()
    assert suivi["peut_accepter"] is False
    refus = await client.post(f"/api/v1/suivi/{reference}/acceptation", params={"cle": cle})
    assert refus.status_code == 409
    assert "a expiré" in refus.json()["detail"]


async def test_un_devis_n_inclut_pas_d_article_pharmaceutique(client: AsyncClient) -> None:
    reference = (await demander_devis(client))["commande"]["reference"]
    reponse = await client.put(
        f"/api/v1/admin/commandes/{reference}/devis",
        json={"lignes": [await ligne(client, "gants-steriles", quantite=10)]},
        headers=ADMIN,
    )
    assert reponse.status_code == 422
    assert "pharmacien partenaire" in reponse.json()["detail"]
    libre = await client.put(
        f"/api/v1/admin/commandes/{reference}/devis",
        json={"lignes": [{"quantite": 1, "libelle": "Forfait"}]},
        headers=ADMIN,
    )
    assert libre.status_code == 422


async def test_zones_de_livraison(client: AsyncClient) -> None:
    nouvelle = await client.post(
        "/api/v1/admin/zones-livraison",
        json={"slug": "segou", "nom": "Ségou", "frais": 5_000, "delai_jours": 3, "position": 20},
        headers=ADMIN,
    )
    assert nouvelle.status_code == 201
    assert "segou" in [z["slug"] for z in (await client.get("/api/v1/zones-livraison")).json()]
    doublon = await client.post(
        "/api/v1/admin/zones-livraison",
        json={"slug": "segou", "nom": "Ségou bis", "frais": 1},
        headers=ADMIN,
    )
    assert doublon.status_code == 409
    fermee = await client.patch(
        f"/api/v1/admin/zones-livraison/{nouvelle.json()['id']}",
        json={"est_active": False},
        headers=ADMIN,
    )
    assert fermee.json()["est_active"] is False
    assert "segou" not in [z["slug"] for z in (await client.get("/api/v1/zones-livraison")).json()]
    toutes = (await client.get("/api/v1/admin/zones-livraison", headers=ADMIN)).json()
    assert "segou" in [z["slug"] for z in toutes]


async def test_recu_par_sms_de_l_argent_remis(app: FastAPI, client: AsyncClient) -> None:
    kit = await ligne(client, "kit-hygiene", quantite=2)  # 15 000 FCFA, sans acompte
    reference = (await commander(client, [kit]))["commande"]["reference"]
    await statut(client, reference, "confirmee")
    for montant, moyen in ((5_000, "orange_money"), (10_000, "especes")):
        reponse = await client.post(
            f"/api/v1/admin/commandes/{reference}/paiements",
            json={"montant": montant, "moyen": moyen},
            headers=ADMIN,
        )
        assert reponse.status_code == 200, reponse.text
    async with app.state.sessions() as session:
        recus = list(
            await session.scalars(
                select(Notification.message)
                .where(Notification.message.contains("paiement de"))
                .order_by(Notification.cree_le, Notification.id)
            )
        )
    assert recus == [
        f"Bibou : paiement de 5 000 FCFA (Orange Money) recu pour la commande {reference}. "
        "Reste à payer : 10 000 FCFA.",
        f"Bibou : paiement de 10 000 FCFA (espèces) recu pour la commande {reference}. "
        "Commande entièrement payée, merci !",
    ]
