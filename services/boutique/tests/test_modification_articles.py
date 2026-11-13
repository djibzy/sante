"""Articles corrigés au téléphone avant la fabrication : taille, quantité, ajout, retrait."""

from datetime import date, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from boutique.commandes.tarifs import aujourd_hui
from boutique.models import Commande, JournalAudit, Notification
from boutique.notifications import messages

from .aides import commander, fiche, ligne
from .conftest import jeton
from .test_notifications import GSM7

ADMIN = jeton(["boutique:admin"])


@pytest.fixture(autouse=True)
def avec_acompte(app: FastAPI) -> None:
    app.state.parametres.acompte_pourcent = 50


async def modifier(
    client: AsyncClient, reference: str, lignes: list[dict[str, Any]], **autres: Any
) -> Any:
    return await client.put(
        f"/api/v1/admin/commandes/{reference}/articles",
        json={"lignes": lignes, **autres},
        headers=ADMIN,
    )


async def sms(app: FastAPI, reference: str) -> list[str]:
    """SMS au client de la commande, dans l'ordre de dépôt (alerte de l'équipe exclue)."""
    async with app.state.sessions() as session:
        return list(
            await session.scalars(
                select(Notification.message)
                .where(Notification.message.contains(f"commande {reference}"))
                .where(~Notification.message.contains("nouvelle commande"))
                .order_by(Notification.cree_le, Notification.id)
            )
        )


async def statut(client: AsyncClient, reference: str, nouveau: str) -> Any:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": nouveau}, headers=ADMIN
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


def variante(produit: dict[str, Any], taille: str) -> str:
    return next(v["id"] for v in produit["variantes"] if v["taille"] == taille)


async def test_taille_quantite_ajout_retrait(app: FastAPI, client: AsyncClient) -> None:
    blouse = await fiche(client, "blouse-medicale-brodee")
    creee = await commander(
        client,
        [await ligne(client, "blouse-medicale-brodee", "M"), await ligne(client, "kit-hygiene")],
    )
    reference = creee["commande"]["reference"]
    assert creee["commande"]["total"] == 20_000

    # La cliente rappelle : la blouse en L, deux fois, sans le kit, avec une retouche.
    corrigee = await modifier(
        client,
        reference,
        [
            {"produit_id": blouse["id"], "variante_id": variante(blouse, "L"), "quantite": 2},
            {"libelle": "Retouche des manches", "quantite": 1, "prix_unitaire": 1_000},
        ],
    )
    assert corrigee.status_code == 200, corrigee.text
    commande = corrigee.json()
    assert [(x["libelle"], x["quantite"], x["montant"]) for x in commande["lignes"]] == [
        (f"{blouse['nom']} – Taille L · Blanc", 2, 25_000),
        ("Retouche des manches", 1, 1_000),
    ]
    assert (commande["total"], commande["acompte"], commande["statut"]) == (
        26_000,
        12_500,
        "en_attente",
    )
    assert "Articles modifiés : 20 000 FCFA → 26 000 FCFA" in [
        e["note"] for e in commande["historique_complet"]
    ]
    async with app.state.sessions() as session:
        details = await session.scalar(
            select(JournalAudit.details).where(JournalAudit.action == "commande.articles_modifies")
        )
    assert details == {"avant": 20_000, "apres": 26_000, "lignes": 2}
    assert (await sms(app, reference))[-1] == (
        f"Bibou : commande {reference} modifiée. Nouveau total : 26 000 FCFA, dont acompte "
        "12 500 FCFA (non remboursable). Détail sur votre lien de suivi."
    )

    # Une fois la fabrication lancée, plus de correction.
    await statut(client, reference, "confirmee")  # en attente de l'acompte
    await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": 12_500, "moyen": "especes"},
        headers=ADMIN,
    )
    refus = await modifier(
        client,
        reference,
        [{"produit_id": blouse["id"], "variante_id": variante(blouse, "M"), "quantite": 1}],
    )
    assert refus.status_code == 409


async def test_le_prix_d_origine_est_garde(client: AsyncClient) -> None:
    kit = await fiche(client, "kit-hygiene")
    reference = (await commander(client, [await ligne(client, "kit-hygiene")]))["commande"][
        "reference"
    ]
    # Prix du catalogue changé depuis la commande : la ligne déjà commandée garde le sien.
    reponse = await client.patch(
        f"/api/v1/admin/produits/{kit['id']}", json={"prix_public": 9_000}, headers=ADMIN
    )
    assert reponse.status_code == 200, reponse.text
    commande = (
        await modifier(client, reference, [{"produit_id": kit["id"], "quantite": 3}])
    ).json()
    assert (commande["lignes"][0]["prix_unitaire"], commande["total"]) == (7_500, 22_500)


async def test_acompte_et_code_promo_suivent(app: FastAPI, client: AsyncClient) -> None:
    code = await client.post(
        "/api/v1/admin/codes-promo",
        json={
            "code": "DIX",
            "libelle": "Dix pour cent",
            "nature": "pourcentage",
            "valeur": 10,
            "minimum": 10_000,
        },
        headers=ADMIN,
    )
    assert code.status_code == 201
    kit = await fiche(client, "kit-hygiene")
    blouse = await fiche(client, "blouse-medicale-brodee")
    deux_kits = {"produit_id": kit["id"], "quantite": 2}
    creee = await client.post(
        "/api/v1/commandes",
        json={
            "client": {"nom": "Awa Sidibé", "telephone": "76 45 12 39"},
            "livraison": {"mode": "retrait"},
            "lignes": [deux_kits, await ligne(client, "blouse-medicale-brodee", "M")],
            "code_promo": "DIX",
        },
    )
    assert creee.status_code == 201, creee.text
    reference = creee.json()["commande"]["reference"]
    assert creee.json()["commande"]["remise"] == 2_750  # 10 % de 27 500

    # En attente de l'acompte, payé en partie ; la blouse brodée est retirée : plus d'acompte,
    # la fabrication est lancée. Le code suit les articles : 10 % de 15 000.
    assert (await statut(client, reference, "confirmee"))["statut"] == "acompte_attendu"
    await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": 2_000, "moyen": "especes"},
        headers=ADMIN,
    )
    commande = (await modifier(client, reference, [deux_kits])).json()
    assert (commande["remise"], commande["total"], commande["acompte"]) == (1_500, 13_500, 0)
    assert commande["statut"] == "confirmee"
    assert (await sms(app, reference))[-2:] == [
        f"Bibou : commande {reference} modifiée. Nouveau total : 13 500 FCFA. Détail sur votre "
        "lien de suivi.",
        f"Bibou : commande {reference} confirmée, prete vers le "
        f"{date.fromisoformat(commande['date_promise']):%d/%m}.",
    ]

    # Sous le minimum du code, la réduction tombe (commande confirmée : passer par l'annulation).
    autre = (
        await client.post(
            "/api/v1/commandes",
            json={
                "client": {"nom": "Awa Sidibé", "telephone": "66 45 12 39"},
                "livraison": {"mode": "retrait"},
                "lignes": [
                    deux_kits,
                    {
                        "produit_id": blouse["id"],
                        "variante_id": variante(blouse, "S"),
                        "quantite": 1,
                    },
                ],
                "code_promo": "DIX",
            },
        )
    ).json()["commande"]["reference"]
    avant = await sms(app, autre)
    seul = (
        await modifier(
            client, autre, [{"produit_id": kit["id"], "quantite": 1}], prevenir_client=False
        )
    ).json()
    assert (seul["remise"], seul["total"]) == (0, 7_500)
    assert await sms(app, autre) == avant  # client prévenu de vive voix


async def test_le_tarif_professionnel_est_repris(client: AsyncClient) -> None:
    blouse = await fiche(client, "blouse-medicale-brodee")
    creee = await client.post(
        "/api/v1/commandes",
        json={
            "client": {"nom": "Clinique Pasteur", "telephone": "76 45 12 41"},
            "livraison": {"mode": "retrait"},
            "lignes": [await ligne(client, "blouse-medicale-brodee", "M")],
        },
        headers=jeton(["boutique:pro"]),
    )
    assert creee.status_code == 201, creee.text
    reference = creee.json()["commande"]["reference"]
    assert creee.json()["commande"]["total"] == 11_000

    # Autre taille, une blouse de plus : toujours le prix professionnel, pas le prix public.
    reponse = await modifier(
        client,
        reference,
        [{"produit_id": blouse["id"], "variante_id": variante(blouse, "XL"), "quantite": 2}],
    )
    commande = reponse.json()
    assert (commande["tarif_professionnel"], commande["total"]) == (True, 22_000)


async def test_la_date_promise_suit_les_articles(client: AsyncClient) -> None:
    relais = await fiche(client, "kit-du-relais")  # 14 jours d'approvisionnement, sans stock
    creee = await commander(client, [await ligne(client, "kit-hygiene")])  # 7 jours
    reference = creee["commande"]["reference"]
    assert creee["commande"]["date_promise"] == str(aujourd_hui() + timedelta(days=7))
    commande = (
        await modifier(client, reference, [{"produit_id": relais["id"], "quantite": 1}])
    ).json()
    assert commande["date_promise"] == str(aujourd_hui() + timedelta(days=14))


def test_le_sms_tient_en_un_message() -> None:
    """Pire cas : grosse commande, acompte, ou trop-perçu à rendre ; un seul SMS GSM."""
    for total, acompte, paye in ((1_250_000, 625_000, 0), (1_250_000, 0, 9_990_000)):
        commande = Commande(numero=10_999, total=total, acompte=acompte, montant_paye=paye)
        texte = messages.articles_modifies(commande)
        assert set(texte) <= GSM7 and len(texte) <= 160, (len(texte), texte)
