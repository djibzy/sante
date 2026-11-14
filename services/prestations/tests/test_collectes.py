"""Le linge d'une collecte, compté à chaque étape : enlèvement, dépôt, retour."""

from datetime import date

from fastapi import FastAPI
from httpx import AsyncClient

from .aides import (
    GESTION,
    LUNDI,
    TERRAIN,
    action,
    contrat,
    enlever,
    journal,
    lignes,
    partenaire,
    rendre,
    sms,
)
from .conftest import jeton


async def test_un_tour_complet_compte_et_confirme_par_sms(
    app: FastAPI, client: AsyncClient
) -> None:
    app.state.parametres.telephones_equipe = ["+22370000099"]
    pressing = await partenaire(client)
    signe = await contrat(client, partenaire_id=pressing["id"])
    enlevee = await enlever(client, signe["id"], blouse=12, drap=20, taie=1)
    assert enlevee["reference"] == "BC-1001"
    assert enlevee["statut"] == "enlevee"
    assert enlevee["prevue_le"] == "2026-11-16"
    assert enlevee["retour_prevu_le"] == "2026-11-18"  # deux jours après
    assert enlevee["pieces_enlevees"] == 33
    assert enlevee["pieces_rendues"] is None
    assert enlevee["partenaire"]["nom"] == "Pressing du Fleuve"
    assert enlevee["remis_par"] == "Awa, surveillante" and enlevee["sacs"] == 2
    assert "prix_unitaire" not in enlevee["lignes"][0]  # aucun prix pour le terrain

    deposee = await action(client, "BC-1001", "depot")
    assert deposee["statut"] == "chez_partenaire" and deposee["deposee_le"]
    prete = await action(client, "bc-1001", "prete")
    assert prete["libelle_statut"] == "Prête chez le partenaire"
    rendue = await rendre(client, "1001", blouse=12, drap=19, taie=1)
    assert rendue["statut"] == "rendue"
    assert rendue["pieces_rendues"] == 32 and rendue["pieces_manquantes"] == 1
    assert rendue["recu_par"] == "Mariam, lingère"
    drap = next(ligne for ligne in rendue["lignes"] if ligne["article"] == "drap")
    assert drap["ecart"] == -1 and drap["libelle"] == "Drap"

    messages = [(n.destinataire, n.message) for n in await sms(app)]
    assert messages == [
        (
            "+22376000001",
            "Yasal Santé : 33 pièces collectées le 16/11, bon BC-1001 : 20 draps, 12 blouses et "
            "1 taie d'oreiller. Retour prévu mer. 18/11.",
        ),
        (
            "+22376000001",
            "Yasal Santé : bon BC-1001, 32 sur 33 pièces rendues. Manque 1 drap : nous les "
            "recherchons et revenons vers vous.",
        ),
        (
            "+22370000099",  # la gestion, pour chercher la pièce chez le partenaire
            "Linge manquant au retour, bon BC-1001 (Clinique Pasteur) : 1 drap. Partenaire : "
            "Pressing du Fleuve.",
        ),
    ]
    assert await journal(app) == [
        "partenaire.ajoute",
        "contrat.cree",
        "collecte.enlevee",
        "collecte.deposee",
        "collecte.prete",
        "collecte.rendue",
    ]


async def test_recompter_avant_le_depot_seulement(app: FastAPI, client: AsyncClient) -> None:
    signe = await contrat(client, partenaire_id=(await partenaire(client))["id"])
    await enlever(client, signe["id"], blouse=12)
    corrigee = await enlever(client, signe["id"], blouse=11, drap=4)
    assert corrigee["reference"] == "BC-1001"  # la même collecte, recomptée
    assert [(ligne["article"], ligne["quantite_enlevee"]) for ligne in corrigee["lignes"]] == [
        ("blouse", 11),
        ("drap", 4),
    ]
    assert (await sms(app))[-1].message == (
        "Yasal Santé : 15 pièces collectées le 16/11 (comptage corrigé), bon BC-1001 : 11 blouses "
        "et 4 draps. Retour prévu mer. 18/11."
    )
    await action(client, "BC-1001", "depot")
    trop_tard = await client.post(
        "/api/v1/collectes",
        json={
            "contrat_id": signe["id"],
            "jour": LUNDI.isoformat(),
            "lignes": lignes(blouse=10),
            "remis_par": "Awa",
        },
        headers=TERRAIN,
    )
    assert trop_tard.status_code == 409
    assert trop_tard.json()["detail"] == (
        "Collecte chez le partenaire : impossible de la passer à « enlevée »"
    )


async def test_etapes_dans_l_ordre_et_comptes_complets(client: AsyncClient) -> None:
    signe = await contrat(client, partenaire_id=(await partenaire(client))["id"])
    await enlever(client, signe["id"], blouse=5, drap=3)
    trop_tot = await client.post(
        "/api/v1/collectes/BC-1001/retour",
        json={"lignes": lignes(blouse=5, drap=3), "recu_par": "Mariam"},
        headers=TERRAIN,
    )
    assert trop_tot.status_code == 409
    await action(client, "BC-1001", "depot")
    deux_fois = await client.post("/api/v1/collectes/BC-1001/depot", json={}, headers=TERRAIN)
    assert deux_fois.status_code == 409
    oubli = await client.post(
        "/api/v1/collectes/BC-1001/retour",
        json={"lignes": lignes(blouse=5), "recu_par": "Mariam"},
        headers=TERRAIN,
    )
    assert oubli.status_code == 422
    assert oubli.json()["detail"] == "Recomptez chaque article : Drap"
    intrus = await client.post(
        "/api/v1/collectes/BC-1001/retour",
        json={"lignes": lignes(blouse=5, drap=3, taie=1), "recu_par": "Mariam"},
        headers=TERRAIN,
    )
    assert intrus.status_code == 422
    assert intrus.json()["detail"] == "Taie d'oreiller : article absent de l'enlèvement"
    assert (await client.get("/api/v1/collectes/BC-9999", headers=TERRAIN)).status_code == 404


async def test_saisies_refusees(client: AsyncClient) -> None:
    signe = await contrat(client)
    for erreur in (
        {"lignes": lignes(blouse=0)},  # rien compté : on annule le passage
        {"lignes": lignes(blouse=2) + lignes(blouse=3)},  # deux fois le même article
        {"lignes": [{"article": "autre", "quantite": 2}]},  # « autre » sans précision
        {"remis_par": ""},
    ):
        reponse = await client.post(
            "/api/v1/collectes",
            json={
                "contrat_id": signe["id"],
                "lignes": lignes(blouse=1),
                "remis_par": "Awa",
                **erreur,
            },
            headers=TERRAIN,
        )
        assert reponse.status_code == 422, erreur
    autre = await client.post(
        "/api/v1/collectes",
        json={
            "contrat_id": signe["id"],
            "jour": LUNDI.isoformat(),
            "lignes": [{"article": "autre", "precision": "  nappes  ", "quantite": 3}],
            "remis_par": "Awa",
        },
        headers=TERRAIN,
    )
    assert autre.status_code == 201
    assert autre.json()["lignes"][0]["libelle"] == "Autre pièce : nappes"


async def test_partenaire_au_kilo_pesee_requise(client: AsyncClient) -> None:
    kilo = await partenaire(client, nom="Blanchisserie Djoliba", mode_tarif="kg", tarif_kg=600)
    signe = await contrat(client)  # sans partenaire : choisi au dépôt
    await enlever(client, signe["id"], drap=40)
    sans_partenaire = await client.post("/api/v1/collectes/BC-1001/depot", json={}, headers=TERRAIN)
    assert sans_partenaire.status_code == 422
    assert sans_partenaire.json()["detail"] == "Choisissez le partenaire qui lave ce linge"
    sans_pesee = await client.post(
        "/api/v1/collectes/BC-1001/depot", json={"partenaire_id": kilo["id"]}, headers=TERRAIN
    )
    assert sans_pesee.status_code == 422
    assert sans_pesee.json()["detail"] == "Pesée requise : Blanchisserie Djoliba facture au kilo"
    pesee = await action(
        client, "BC-1001", "depot", {"partenaire_id": kilo["id"], "poids_kg": 12.34}
    )
    assert pesee["poids_kg"] == 12.3
    assert pesee["partenaire"]["pesee_requise"] is True


async def test_annuler_un_passage_ou_une_collecte(app: FastAPI, client: AsyncClient) -> None:
    signe = await contrat(client)
    ferme = await client.post(
        "/api/v1/tournee/annulations",
        json={"contrat_id": signe["id"], "jour": LUNDI.isoformat(), "motif": "Clinique fermée"},
        headers=TERRAIN,
    )
    assert ferme.status_code == 200, ferme.text
    assert ferme.json()["statut"] == "annulee"
    assert ferme.json()["motif_annulation"] == "Clinique fermée"
    # Le linge arrive finalement : un enlèvement reste possible ce jour-là.
    enlevee = await enlever(client, signe["id"], blouse=3)
    assert enlevee["reference"] == "BC-1002"
    refus = await client.post(
        "/api/v1/collectes/BC-1002/annulation", json={"motif": "Erreur de saisie"}, headers=TERRAIN
    )
    assert refus.status_code == 403  # linge déjà compté : la gestion décide
    annulee = await action(
        client, "BC-1002", "annulation", {"motif": "Erreur de saisie"}, entetes=GESTION
    )
    assert annulee["statut"] == "annulee"
    assert len(await sms(app)) == 1  # seul l'enlèvement a prévenu la structure


async def test_collecte_ponctuelle_puis_enlevee(client: AsyncClient) -> None:
    signe = await contrat(client, jours_collecte=[])  # sur appel
    mercredi = date(2026, 11, 18)
    prevue = await client.post(
        "/api/v1/collectes/ponctuelles",
        json={"contrat_id": signe["id"], "prevue_le": mercredi.isoformat()},
        headers=GESTION,
    )
    assert prevue.status_code == 201, prevue.text
    assert prevue.json()["statut"] == "prevue"
    deux_fois = await client.post(
        "/api/v1/collectes/ponctuelles",
        json={"contrat_id": signe["id"], "prevue_le": mercredi.isoformat()},
        headers=TERRAIN,
    )
    assert deux_fois.status_code == 409
    enlevee = await enlever(client, signe["id"], jour=mercredi, blouse=4)
    assert enlevee["reference"] == prevue.json()["reference"]
    assert enlevee["statut"] == "enlevee"


async def test_contrat_suspendu_et_sms_coupes(app: FastAPI, client: AsyncClient) -> None:
    signe = await contrat(client, sms_actifs=False)
    await enlever(client, signe["id"], blouse=2)
    assert await sms(app) == []
    await client.patch(
        f"/api/v1/admin/contrats/{signe['reference']}", json={"statut": "suspendu"}, headers=GESTION
    )
    suspendu = await client.post(
        "/api/v1/collectes",
        json={"contrat_id": signe["id"], "lignes": lignes(blouse=1), "remis_par": "Awa"},
        headers=TERRAIN,
    )
    assert suspendu.status_code == 409
    assert suspendu.json()["detail"] == "Contrat CT-101 suspendu ou terminé"


async def test_acces_reserve_a_l_equipe(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/tournee")).status_code == 401
    boutique = jeton(["boutique:admin"])
    assert (await client.get("/api/v1/tournee", headers=boutique)).status_code == 403
    assert (await client.get("/api/v1/tournee", headers=jeton(["admin"]))).status_code == 200
    assert (await client.get("/api/v1/admin/collectes", headers=TERRAIN)).status_code == 403
