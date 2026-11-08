from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select

from boutique.models import Commande, JournalAudit

from .aides import ADRESSE, commander, fiche, ligne, zone
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])


def dans(jours: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=jours)).isoformat()


async def test_chiffrage_prix_frais_et_date(client: AsyncClient) -> None:
    corps = {
        "lignes": [
            await ligne(client, "blouse-medicale-brodee", "L", 2, "Aminata Traoré, sage-femme"),
            await ligne(client, "kit-hygiene"),
        ],
        "livraison": {"mode": "livraison", "zone_id": await zone(client)},
    }
    chiffrage = (await client.post("/api/v1/panier/chiffrage", json=corps)).json()

    assert chiffrage["commandable"] is True
    assert [ligne["montant"] for ligne in chiffrage["lignes"]] == [25_000, 7_500]
    assert chiffrage["lignes"][0]["libelle"] == "Blouse médicale brodée – Taille L · Blanc"
    assert chiffrage["lignes"][0]["personnalisation"] == "Aminata Traoré, sage-femme"
    assert chiffrage["sous_total"] == 32_500
    assert chiffrage["frais_livraison"] == 1_000
    assert chiffrage["total"] == 33_500
    assert chiffrage["date_estimee"] == dans(10 + 1)  # broderie 10 jours, livraison 1 jour


async def test_chiffrage_signale_ce_qui_ne_peut_pas_etre_commande(client: AsyncClient) -> None:
    blouse = await fiche(client, "blouse-medicale-brodee")
    corps = {
        "lignes": [
            await ligne(client, "gants-steriles"),
            {"produit_id": blouse["id"], "quantite": 1},
            {"produit_id": "0190f000-0000-7000-8000-000000000000", "quantite": 1},
            await ligne(client, "affiche-a2", quantite=3, personnalisation="ignoré"),
        ]
    }
    chiffrage = (await client.post("/api/v1/panier/chiffrage", json=corps)).json()

    gants, sans_taille, inconnu, affiche = chiffrage["lignes"]
    assert chiffrage["commandable"] is False
    assert "pharmacien partenaire" in gants["motif"] and gants["prix_unitaire"] is None
    assert sans_taille["motif"] == "choisissez une taille ou une variante"
    assert inconnu["motif"] == "ce produit n'est plus disponible"
    assert affiche["commandable"] and affiche["personnalisation"] is None
    assert chiffrage["sous_total"] == 4_500


async def test_prix_professionnel_pour_les_soignants_verifies(client: AsyncClient) -> None:
    corps = {"lignes": [await ligne(client, "blouse-medicale-brodee", "M")]}
    public = (await client.post("/api/v1/panier/chiffrage", json=corps)).json()
    pro = (
        await client.post("/api/v1/panier/chiffrage", json=corps, headers=jeton(["boutique:pro"]))
    ).json()
    assert public["total"] == 12_500
    assert pro["total"] == 11_000


async def test_commande_sans_compte_puis_suivi_par_lien(app: FastAPI, client: AsyncClient) -> None:
    livraison = {"mode": "livraison", "zone_id": await zone(client), "adresse": ADRESSE}
    lignes = [await ligne(client, "blouse-medicale-brodee", "L", 1, "A. Traoré")]
    reponse = await client.post(
        "/api/v1/commandes",
        json={
            "client": {"nom": "Aminata Traoré", "telephone": "76 12 34 56"},
            "livraison": livraison,
            "lignes": lignes,
            "note": "Appeler avant de venir",
        },
    )
    assert reponse.status_code == 201, reponse.text
    creee = reponse.json()
    commande, cle = creee["commande"], creee["cle_suivi"]
    assert commande["reference"] == "BB-1001"
    assert commande["statut"] == "en_attente"
    assert commande["telephone"] == "+22376123456"
    assert commande["total"] == 13_500 and commande["reste_a_payer"] == 13_500
    assert commande["zone_nom"] == "Bamako, commune IV"
    assert commande["date_promise"] == dans(11)
    assert commande["peut_annuler"] is True
    assert [e["libelle"] for e in commande["historique"]] == ["Reçue, à confirmer"]

    suivi = await client.get(f"/api/v1/suivi/BB-1001?cle={cle}")
    assert suivi.status_code == 200
    assert suivi.json()["lignes"][0]["personnalisation"] == "A. Traoré"
    assert (await client.get("/api/v1/suivi/bb1001", params={"cle": cle})).status_code == 200
    for adresse in ("/api/v1/suivi/BB-1001", "/api/v1/suivi/BB-1001?cle=mauvaise-cle-123"):
        assert (await client.get(adresse)).status_code == 404
    assert (await client.get(f"/api/v1/suivi/BB-9999?cle={cle}")).status_code == 404

    async with app.state.sessions() as session:
        entree = (
            await session.execute(select(JournalAudit).where(JournalAudit.objet_id == "BB-1001"))
        ).scalar_one()
    assert entree.action == "commande.creee"
    assert entree.details == {"total": 13_500, "lignes": 1}  # ni nom ni téléphone au journal


async def test_un_second_envoi_ne_cree_pas_de_doublon(app: FastAPI, client: AsyncClient) -> None:
    lignes = [await ligne(client, "kit-hygiene")]
    cle = "c3b2a1f0-1d2e-4f5a-8b9c-0d1e2f3a4b5c"
    premiere = await commander(client, lignes, cle=cle)
    seconde = await client.post(
        "/api/v1/commandes",
        json={
            "client": {"nom": "Aminata Traoré", "telephone": "76 12 34 56"},
            "livraison": {"mode": "retrait"},
            "lignes": lignes,
            "cle_suivi": cle,
        },
    )
    assert seconde.status_code == 200
    assert seconde.json()["commande"]["reference"] == premiere["commande"]["reference"]
    assert seconde.json()["cle_suivi"] == cle
    async with app.state.sessions() as session:
        assert await session.scalar(select(func.count(Commande.id))) == 1


async def test_commandes_refusees(client: AsyncClient) -> None:
    base = {"client": {"nom": "Aminata Traoré", "telephone": "76 12 34 56"}}
    kit = [await ligne(client, "kit-hygiene")]
    cas = [
        (
            {"livraison": {"mode": "retrait"}, "lignes": [await ligne(client, "gants-steriles")]},
            "pharmacien partenaire",
        ),
        (
            {"client": {"nom": "Aminata", "telephone": "00 00 00"}, "livraison": {}, "lignes": kit},
            "Numéro de téléphone invalide",
        ),
        (
            {"livraison": {"mode": "livraison", "adresse": ADRESSE}, "lignes": kit},
            "Choisissez une zone de livraison",
        ),
        (
            {"livraison": {"mode": "livraison", "zone_id": await zone(client)}, "lignes": kit},
            "Indiquez l'adresse de livraison",
        ),
    ]
    for corps, message in cas:
        reponse = await client.post("/api/v1/commandes", json={**base, **corps})
        assert reponse.status_code == 422, corps
        assert message in reponse.json()["detail"]


async def test_nombre_de_demandes_limite_par_telephone(client: AsyncClient) -> None:
    lignes = [await ligne(client, "affiche-a2")]
    for _ in range(5):
        await commander(client, lignes, telephone="+223 65 00 00 01")
    reponse = await client.post(
        "/api/v1/commandes",
        json={
            "client": {"nom": "Moussa Diarra", "telephone": "65 00 00 01"},
            "livraison": {"mode": "retrait"},
            "lignes": lignes,
        },
    )
    assert reponse.status_code == 429
    await commander(client, lignes, telephone="65 00 00 02")  # un autre numéro passe


async def test_le_client_annule_tant_que_rien_n_est_confirme(client: AsyncClient) -> None:
    lignes = [await ligne(client, "kit-hygiene")]
    premiere = await commander(client, lignes)
    reference, cle = premiere["commande"]["reference"], premiere["cle_suivi"]
    annulation = await client.post(f"/api/v1/suivi/{reference}/annulation", params={"cle": cle})
    assert annulation.status_code == 200
    assert annulation.json()["statut"] == "annulee"
    assert annulation.json()["historique"][-1]["note"] == "Annulée par le client"
    deuxieme = await client.post(f"/api/v1/suivi/{reference}/annulation", params={"cle": cle})
    assert deuxieme.status_code == 409

    seconde = await commander(client, lignes)
    reference, cle = seconde["commande"]["reference"], seconde["cle_suivi"]
    confirmation = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": "confirmee"}, headers=ADMIN
    )
    assert confirmation.status_code == 200
    refus = await client.post(f"/api/v1/suivi/{reference}/annulation", params={"cle": cle})
    assert refus.status_code == 409
    assert "appelez-nous" in refus.json()["detail"]


async def test_mes_commandes_avec_un_compte(client: AsyncClient) -> None:
    moi, autre = jeton(nom="Awa Coulibaly"), jeton(nom="Fanta Keïta")
    lignes = [await ligne(client, "tshirt-de-campagne", "M", 4), await ligne(client, "calot-brode")]
    reference = (await commander(client, lignes, entetes=moi))["commande"]["reference"]

    liste = (await client.get("/api/v1/mes-commandes", headers=moi)).json()
    assert [(c["reference"], c["nombre_articles"], c["total"]) for c in liste] == [
        (reference, 5, 17_000)
    ]
    detail = f"/api/v1/mes-commandes/{reference}"
    assert (await client.get(detail, headers=moi)).status_code == 200
    assert (await client.get(detail, headers=autre)).status_code == 404
    assert (await client.get("/api/v1/mes-commandes", headers=autre)).json() == []
    assert (await client.get("/api/v1/mes-commandes")).status_code == 401
    annulation = await client.post(f"/api/v1/mes-commandes/{reference}/annulation", headers=moi)
    assert annulation.json()["statut"] == "annulee"
