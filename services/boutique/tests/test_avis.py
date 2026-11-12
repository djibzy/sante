from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from boutique.avis.service import auteur_de
from boutique.models import JournalAudit

from .aides import commander, fiche, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
TEXTE = "Tissu agréable, la broderie a tenu après plusieurs lavages."


async def statut(client: AsyncClient, reference: str, nouveau: str) -> None:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": nouveau}, headers=ADMIN
    )
    assert reponse.status_code == 200, reponse.text


async def commande(
    client: AsyncClient,
    livrer: bool = True,
    telephone: str = "76 12 34 56",
    entetes: dict[str, str] | None = None,
    nom: str | None = None,
) -> tuple[str, str]:
    lignes = [await ligne(client, "kit-hygiene"), await ligne(client, "affiche-a2", quantite=2)]
    creee = await commander(client, lignes, telephone=telephone, entetes=entetes)
    reference = creee["commande"]["reference"]
    if livrer:
        for etape in ("confirmee", "prete", "livree"):
            await statut(client, reference, etape)
    return reference, creee["cle_suivi"]


async def donner_avis(
    client: AsyncClient, reference: str, cle: str, slug: str, note: int, texte: str = TEXTE
) -> Any:
    produit = await fiche(client, slug)
    return await client.post(
        f"/api/v1/suivi/{reference}/avis",
        params={"cle": cle},
        json={"produit_id": produit["id"], "note": note, "texte": texte},
    )


async def a_relire(client: AsyncClient) -> list[dict[str, Any]]:
    reponse = await client.get("/api/v1/admin/avis", headers=ADMIN)
    assert reponse.status_code == 200, reponse.text
    elements: list[dict[str, Any]] = reponse.json()["elements"]
    return elements


async def moderer(client: AsyncClient, avis_id: str, **decision: Any) -> Any:
    return await client.post(
        f"/api/v1/admin/avis/{avis_id}/moderation", json=decision, headers=ADMIN
    )


async def test_avis_seulement_une_fois_la_commande_recue(client: AsyncClient) -> None:
    reference, cle = await commande(client, livrer=False)
    attente = (await client.get(f"/api/v1/suivi/{reference}/avis", params={"cle": cle})).json()
    assert (attente["possible"], attente["raison"]) == (
        False,
        "Vous pourrez donner votre avis une fois la commande reçue.",
    )
    assert [p["slug"] for p in attente["produits"]] == ["kit-hygiene", "affiche-a2"]
    assert (await donner_avis(client, reference, cle, "kit-hygiene", 5)).status_code == 409
    mauvaise_cle = await client.get(f"/api/v1/suivi/{reference}/avis", params={"cle": "x" * 24})
    assert mauvaise_cle.status_code == 404


async def test_avis_relu_puis_publie(app: FastAPI, client: AsyncClient) -> None:
    reference, cle = await commande(client)
    premier = await donner_avis(
        client, reference, cle, "kit-hygiene", 4, "Pratique, mais le flacon fuit."
    )
    assert premier.status_code == 201, premier.text
    corrige = await donner_avis(client, reference, cle, "kit-hygiene", 5)
    assert corrige.status_code == 200  # encore en relecture : le client peut le corriger
    assert corrige.json() == {
        "note": 5,
        "texte": TEXTE,
        "statut": "en_attente",
        "motif_refus": None,
        "reponse": None,
    }
    publics = (await client.get("/api/v1/produits/kit-hygiene/avis")).json()
    assert (publics["nombre"], publics["moyenne"], publics["elements"]) == (0, None, [])

    [avis] = await a_relire(client)
    assert (avis["auteur"], avis["commande_reference"], avis["note"]) == (
        "Aminata T.",
        reference,
        5,
    )
    assert avis["produit_slug"] == "kit-hygiene"
    decision = await moderer(
        client, avis["id"], decision="publier", reponse="Merci Aminata, à bientôt !"
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["statut"] == "publie"
    assert await a_relire(client) == []

    publics = (await client.get("/api/v1/produits/kit-hygiene/avis")).json()
    assert (publics["nombre"], publics["moyenne"]) == (1, 5.0)
    assert publics["repartition"] == {"5": 1, "4": 0, "3": 0, "2": 0, "1": 0}
    [public] = publics["elements"]
    assert (public["auteur"], public["texte"], public["achat_verifie"]) == (
        "Aminata T.",
        TEXTE,
        True,
    )
    assert public["reponse"] == "Merci Aminata, à bientôt !"
    assert "telephone" not in public and "commande" not in str(public)
    kit = await fiche(client, "kit-hygiene")
    assert (kit["note_moyenne"], kit["nombre_avis"]) == (5.0, 1)
    liste = (await client.get("/api/v1/produits", params={"q": "kit hygiene"})).json()
    assert liste["elements"][0]["nombre_avis"] == 1

    verrouille = await donner_avis(client, reference, cle, "kit-hygiene", 1)
    assert verrouille.status_code == 409
    suivi = (await client.get(f"/api/v1/suivi/{reference}/avis", params={"cle": cle})).json()
    assert suivi["possible"] is True
    assert [p["avis"]["statut"] if p["avis"] else None for p in suivi["produits"]] == [
        "publie",
        None,
    ]
    async with app.state.sessions() as session:
        actions = list(await session.scalars(select(JournalAudit.action)))
    assert {"avis.depose", "avis.modifie", "avis.publie"} <= set(actions)


async def test_avis_refuse_puis_reecrit(client: AsyncClient) -> None:
    reference, cle = await commande(client)
    await donner_avis(
        client, reference, cle, "affiche-a2", 2, "Reçue pendant mon traitement contre le palu."
    )
    [avis] = await a_relire(client)
    assert (await moderer(client, avis["id"], decision="refuser")).status_code == 422
    motif = "Merci de ne mentionner aucune information médicale."
    refus = await moderer(client, avis["id"], decision="refuser", motif=motif)
    assert refus.json()["statut"] == "refuse"
    suivi = (await client.get(f"/api/v1/suivi/{reference}/avis", params={"cle": cle})).json()
    affiche = next(p for p in suivi["produits"] if p["slug"] == "affiche-a2")
    assert (affiche["avis"]["statut"], affiche["avis"]["motif_refus"]) == ("refuse", motif)

    reecrit = await donner_avis(
        client, reference, cle, "affiche-a2", 3, "Couleurs fidèles, papier un peu fin."
    )
    assert reecrit.status_code == 200
    assert (reecrit.json()["statut"], reecrit.json()["motif_refus"]) == ("en_attente", None)
    [avis] = await a_relire(client)
    await moderer(client, avis["id"], decision="publier")
    assert (await fiche(client, "affiche-a2"))["nombre_avis"] == 1
    # Retiré plus tard par l'équipe : la note du produit est recomptée.
    await moderer(
        client, avis["id"], decision="refuser", motif="Avis retiré à la demande du client."
    )
    affiche = await fiche(client, "affiche-a2")
    assert (affiche["nombre_avis"], affiche["note_moyenne"]) == (0, None)
    refuses = await client.get("/api/v1/admin/avis", params={"statut": "refuse"}, headers=ADMIN)
    assert refuses.json()["total"] == 1


async def test_moyenne_et_pages(client: AsyncClient) -> None:
    for telephone, note in (("76 12 34 56", 5), ("66 12 34 57", 2), ("70 12 34 58", 4)):
        reference, cle = await commande(client, telephone=telephone)
        assert (await donner_avis(client, reference, cle, "kit-hygiene", note)).status_code == 201
    for avis in await a_relire(client):
        await moderer(client, avis["id"], decision="publier")
    page = (await client.get("/api/v1/produits/kit-hygiene/avis", params={"par_page": 2})).json()
    assert (page["nombre"], page["moyenne"], len(page["elements"])) == (3, 3.7, 2)
    assert page["repartition"] == {"5": 1, "4": 1, "3": 0, "2": 1, "1": 0}
    suite = await client.get("/api/v1/produits/kit-hygiene/avis", params={"par_page": 2, "page": 2})
    assert len(suite.json()["elements"]) == 1
    assert (await fiche(client, "kit-hygiene"))["note_moyenne"] == 3.7
    assert (await client.get("/api/v1/produits/inconnu/avis")).status_code == 404


async def test_avis_refuses_a_l_entree(client: AsyncClient) -> None:
    reference, cle = await commande(client)
    hors_commande = await donner_avis(client, reference, cle, "tunique-sage-femme", 5)
    assert hors_commande.status_code == 422
    assert (await donner_avis(client, reference, cle, "kit-hygiene", 6)).status_code == 422
    assert (await donner_avis(client, reference, cle, "kit-hygiene", 5, "Bien.")).status_code == 422
    blancs = await donner_avis(client, reference, cle, "kit-hygiene", 5, " " * 12)
    assert blancs.status_code == 422


async def test_avis_depuis_le_compte_client(client: AsyncClient) -> None:
    aminata = jeton(nom="Aminata Traoré")
    reference, _ = await commande(client, entetes=aminata)
    produit = await fiche(client, "kit-hygiene")
    corps = {"produit_id": produit["id"], "note": 5, "texte": TEXTE}
    chemin = f"/api/v1/mes-commandes/{reference}/avis"
    assert (await client.post(chemin, json=corps, headers=jeton(nom="Autre"))).status_code == 404
    assert (await client.post(chemin, json=corps, headers=aminata)).status_code == 201
    mes_avis = (await client.get(chemin, headers=aminata)).json()
    assert mes_avis["produits"][0]["avis"]["statut"] == "en_attente"


async def test_relecture_reservee_a_l_equipe(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/admin/avis")).status_code == 401
    atelier = jeton(["boutique:atelier"])
    assert (await client.get("/api/v1/admin/avis", headers=atelier)).status_code == 403
    inconnu = "0190f000-0000-7000-8000-000000000000"
    assert (await moderer(client, inconnu, decision="publier")).status_code == 404


def test_seulement_le_prenom_et_l_initiale() -> None:
    assert auteur_de("Aminata Traoré") == "Aminata T."
    assert auteur_de("AMINATA TRAORE") == "Aminata T."
    assert auteur_de("Fatoumata Binta Diallo") == "Fatoumata D."
    assert auteur_de("Moussa") == "Moussa"
    assert auteur_de("   ") == "Client Bibou"
