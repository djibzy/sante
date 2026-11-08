import asyncio
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from httpx import AsyncClient
from pypdf import PdfReader

from .aides import ADRESSE, commander, ligne, zone
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])
ANNEE = datetime.now(UTC).year


async def statut(client: AsyncClient, reference: str, nouveau: str, **autres: Any) -> Any:
    return await client.post(
        f"/api/v1/admin/commandes/{reference}/statut",
        json={"statut": nouveau, **autres},
        headers=ADMIN,
    )


def texte_pdf(contenu: bytes) -> str:
    pages = PdfReader(BytesIO(contenu)).pages
    return " ".join(page.extract_text() for page in pages).replace("\xa0", " ")


async def livreur(client: AsyncClient, nom: str = "Moussa Konaté") -> dict[str, Any]:
    reponse = await client.post(
        "/api/v1/admin/livreurs", json={"nom": nom, "telephone": "76 55 44 33"}, headers=ADMIN
    )
    assert reponse.status_code == 201, reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees


async def test_feuille_de_route_livreur_et_facture(client: AsyncClient) -> None:
    moussa = await livreur(client)
    assert moussa["telephone"] == "+22376554433"
    livraison = {"mode": "livraison", "zone_id": await zone(client), "adresse": ADRESSE}
    creee = await commander(client, [await ligne(client, "kit-hygiene")], livraison=livraison)
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    await statut(client, reference, "confirmee")
    await statut(client, reference, "prete")

    [arret] = (await client.get("/api/v1/admin/livraisons", headers=ADMIN)).json()
    assert (arret["reference"], arret["statut"], arret["livreur_nom"]) == (reference, "prete", None)
    assert (arret["reste_a_payer"], arret["adresse"]) == (8_500, ADRESSE)

    inconnu = await statut(
        client, reference, "en_livraison", livreur_id=creee["commande"]["lignes"][0]["id"]
    )
    assert inconnu.status_code == 422
    depart = await statut(client, reference, "en_livraison", livreur_id=moussa["id"])
    assert depart.status_code == 200
    suivi = (await client.get(f"/api/v1/suivi/{reference}", params={"cle": cle})).json()
    assert (suivi["livreur_nom"], suivi["livreur_telephone"]) == ("Moussa Konaté", "+22376554433")
    [arret] = (await client.get("/api/v1/admin/livraisons", headers=ADMIN)).json()
    assert arret["livreur_nom"] == "Moussa Konaté"

    pas_encore = await client.get(f"/api/v1/suivi/{reference}/facture.pdf", params={"cle": cle})
    assert pas_encore.status_code == 409
    livree = (await statut(client, reference, "livree")).json()
    assert livree["facture"] == f"F{ANNEE}-00001"
    assert (await client.get("/api/v1/admin/livraisons", headers=ADMIN)).json() == []
    await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": 8_500, "moyen": "especes"},
        headers=ADMIN,
    )

    pdf = await client.get(f"/api/v1/suivi/{reference}/facture.pdf", params={"cle": cle})
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    texte = texte_pdf(pdf.content)
    for attendu in (
        "Facture",
        f"F{ANNEE}-00001",
        f"Commande {reference}",
        "Payé le",
        "(espèces)",
        "Reste à payer",
        "huit mille cinq cents francs CFA",
    ):
        assert attendu in texte, attendu

    seconde = await commander(client, [await ligne(client, "affiche-a2")])
    await statut(client, seconde["commande"]["reference"], "confirmee")
    await statut(client, seconde["commande"]["reference"], "prete")
    remise = (await statut(client, seconde["commande"]["reference"], "livree")).json()
    assert remise["facture"] == f"F{ANNEE}-00002"


async def test_facture_a_la_demande_d_une_structure(client: AsyncClient) -> None:
    demande = await client.post(
        "/api/v1/devis",
        json={
            "etablissement": "Clinique du Fleuve",
            "client": {"nom": "Mme Coulibaly", "telephone": "66 00 11 22"},
            "lignes": [await ligne(client, "kit-premiers-secours", quantite=10)],
        },
    )
    reference = demande.json()["commande"]["reference"]
    trop_tot = await client.post(f"/api/v1/admin/commandes/{reference}/facture", headers=ADMIN)
    assert trop_tot.status_code == 409
    await client.put(
        f"/api/v1/admin/commandes/{reference}/devis",
        json={"lignes": [await ligne(client, "kit-premiers-secours", quantite=10)]},
        headers=ADMIN,
    )
    await statut(client, reference, "confirmee")
    premiere = await client.post(f"/api/v1/admin/commandes/{reference}/facture", headers=ADMIN)
    seconde = await client.post(f"/api/v1/admin/commandes/{reference}/facture", headers=ADMIN)
    assert premiere.json()["facture"] == seconde.json()["facture"] == f"F{ANNEE}-00001"
    pdf = await client.get(f"/api/v1/admin/commandes/{reference}/facture.pdf", headers=ADMIN)
    assert "Clinique du Fleuve" in texte_pdf(pdf.content)


async def test_numerotation_continue_meme_en_parallele(client: AsyncClient) -> None:
    references = []
    for _ in range(5):
        creee = await commander(
            client, [await ligne(client, "affiche-a2")], telephone="70 11 22 33"
        )
        await statut(client, creee["commande"]["reference"], "confirmee")
        references.append(creee["commande"]["reference"])
    reponses = await asyncio.gather(
        *(
            client.post(f"/api/v1/admin/commandes/{reference}/facture", headers=ADMIN)
            for reference in references
        )
    )
    numeros = sorted(r.json()["facture"] for r in reponses)
    assert numeros == [f"F{ANNEE}-{n:05d}" for n in range(1, 6)]


async def test_gestion_des_livreurs(client: AsyncClient) -> None:
    moussa = await livreur(client)
    modifie = await client.patch(
        f"/api/v1/admin/livreurs/{moussa['id']}",
        json={"est_actif": False, "telephone": "65 99 88 77"},
        headers=ADMIN,
    )
    assert (modifie.json()["est_actif"], modifie.json()["telephone"]) == (False, "+22365998877")
    assert [
        x["nom"] for x in (await client.get("/api/v1/admin/livreurs", headers=ADMIN)).json()
    ] == ["Moussa Konaté"]
    refus = await client.post(
        "/api/v1/admin/livreurs", json={"nom": "X", "telephone": "76 55 44 33"}, headers=ADMIN
    )
    assert refus.status_code == 422
