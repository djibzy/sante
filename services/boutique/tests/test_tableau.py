from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import update

from boutique.models import Commande

from .aides import commander, fiche, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
AUJOURD_HUI = datetime.now(UTC).date()


async def statut(client: AsyncClient, reference: str, nouveau: str) -> None:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": nouveau}, headers=ADMIN
    )
    assert reponse.status_code == 200, reponse.text


async def devis(client: AsyncClient, telephone: str) -> tuple[str, str]:
    demande = await client.post(
        "/api/v1/devis",
        json={
            "etablissement": "CSCom de Banconi",
            "client": {"nom": "Dr Oumar Sangaré", "telephone": telephone},
            "lignes": [await ligne(client, "affiche-a2", quantite=10)],
        },
    )
    assert demande.status_code == 201, demande.text
    reference = demande.json()["commande"]["reference"]
    emission = await client.put(
        f"/api/v1/admin/commandes/{reference}/devis",
        json={"lignes": [await ligne(client, "affiche-a2", quantite=10)]},
        headers=ADMIN,
    )
    assert emission.status_code == 200, emission.text
    return reference, demande.json()["cle_suivi"]


async def tableau(client: AsyncClient, **periode: Any) -> dict[str, Any]:
    reponse = await client.get("/api/v1/admin/tableau-de-bord", params=periode, headers=ADMIN)
    assert reponse.status_code == 200, reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees


async def test_indicateurs_de_la_periode(app: FastAPI, client: AsyncClient) -> None:
    # Livrée et payée en espèces ; en cours (bientôt en retard) ; annulée.
    livree = await commander(client, [await ligne(client, "kit-hygiene")])
    reference, total = livree["commande"]["reference"], livree["commande"]["total"]
    for etape in ("confirmee", "prete", "livree"):
        await statut(client, reference, etape)
    encaissement = await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": total, "moyen": "especes"},
        headers=ADMIN,
    )
    assert encaissement.status_code == 200
    en_cours = await commander(
        client, [await ligne(client, "affiche-a2", quantite=2)], telephone="66 12 34 57"
    )
    await statut(client, en_cours["commande"]["reference"], "confirmee")
    annulee = await commander(client, [await ligne(client, "kit-hygiene")], telephone="70 12 34 58")
    await statut(client, annulee["commande"]["reference"], "annulee")
    # Deux devis : l'un accepté par le client, l'autre refusé.
    accepte, cle = await devis(client, "76 99 88 77")
    acceptation = await client.post(f"/api/v1/suivi/{accepte}/acceptation", params={"cle": cle})
    assert acceptation.status_code == 200
    refuse, _ = await devis(client, "76 99 88 66")
    await statut(client, refuse, "devis_refuse")
    async with app.state.sessions() as session:  # la date promise de la commande en cours passe
        hier = AUJOURD_HUI - timedelta(days=1)
        await session.execute(
            update(Commande)
            .where(Commande.numero == int(en_cours["commande"]["reference"][3:]))
            .values(date_promise=hier)
        )
        await session.commit()

    donnees = await tableau(client)
    assert (donnees["du"], donnees["au"]) == (
        str(AUJOURD_HUI - timedelta(days=29)),
        str(AUJOURD_HUI),
    )
    ventes = donnees["ventes"]
    assert (ventes["commandes_recues"], ventes["commandes_livrees"], ventes["annulees"]) == (
        3,
        1,
        1,
    )
    assert (ventes["chiffre_affaires"], ventes["panier_moyen"]) == (total, total)
    assert (ventes["encaisse"], ventes["encaisse_par_moyen"]) == (total, {"especes": total})
    assert (ventes["encaisse_en_ligne"], ventes["a_encaisser"]) == (0, 0)
    assert donnees["devis"] == {
        "demandes": 2,
        "envoyes": 2,
        "acceptes": 1,
        "refuses": 1,
        "taux_acceptation": 0.5,
    }
    delais = donnees["delais"]
    assert delais["confirmation_heures"] == 0.0 and delais["livraison_jours"] == 0.0
    assert delais["a_l_heure"] == 1.0
    clients = donnees["clients"]
    assert (clients["clients"], clients["nouveaux"], clients["note_moyenne"]) == (5, 5, None)
    kit = await fiche(client, "kit-hygiene")
    assert donnees["meilleures_ventes"] == [
        {"produit_slug": kit["slug"], "libelle": kit["nom"], "quantite": 1, "montant": total}
    ]
    alertes = donnees["alertes"]
    assert (alertes["a_traiter"], alertes["en_retard"], alertes["sms_en_echec"]) == (0, 1, 0)
    assert alertes["stock_bas"] >= 0 and alertes["paiements_a_verifier"] == 0
    assert donnees["pas"] == "jour" and len(donnees["serie"]) == 30
    assert donnees["serie"][-1] == {
        "debut": str(AUJOURD_HUI),
        "chiffre_affaires": total,
        "commandes": 1,
    }
    assert sum(point["chiffre_affaires"] for point in donnees["serie"]) == total


async def test_periode_par_semaine_et_bornes(client: AsyncClient) -> None:
    annee = await tableau(client, du=str(AUJOURD_HUI - timedelta(days=200)), au=str(AUJOURD_HUI))
    assert annee["pas"] == "semaine"
    premier = datetime.fromisoformat(annee["serie"][0]["debut"]).date()
    assert premier.weekday() == 0  # semaines du lundi
    assert annee["ventes"]["panier_moyen"] is None and annee["delais"]["a_l_heure"] is None
    inverse = await client.get(
        "/api/v1/admin/tableau-de-bord",
        params={"du": str(AUJOURD_HUI), "au": str(AUJOURD_HUI - timedelta(days=1))},
        headers=ADMIN,
    )
    assert inverse.status_code == 422
    trop_long = await client.get(
        "/api/v1/admin/tableau-de-bord",
        params={"du": str(AUJOURD_HUI - timedelta(days=400))},
        headers=ADMIN,
    )
    assert trop_long.status_code == 422
    assert (await client.get("/api/v1/admin/tableau-de-bord")).status_code == 401
    atelier = jeton(["boutique:atelier"])
    refuse = await client.get("/api/v1/admin/tableau-de-bord", headers=atelier)
    assert refuse.status_code == 403
