"""« Commander à nouveau » : ce qui revient au panier, ce qui est écarté et pourquoi."""

from typing import Any

from httpx import AsyncClient

from .aides import commander, fiche, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])


async def a_recommander(client: AsyncClient, reference: str, cle: str) -> Any:
    reponse = await client.get(f"/api/v1/suivi/{reference}/a-recommander", params={"cle": cle})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def test_les_articles_reviennent_au_panier(client: AsyncClient) -> None:
    blouse, kit = await fiche(client, "blouse-medicale-brodee"), await fiche(client, "kit-hygiene")
    m = next(v for v in blouse["variantes"] if v["taille"] == "M")
    brodee = await ligne(
        client, "blouse-medicale-brodee", "M", personnalisation="Awa T. Infirmière"
    )
    creee = await commander(client, [brodee, await ligne(client, "kit-hygiene", quantite=2)])
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    # L'équipe a ajouté une retouche (ligne libre) au téléphone.
    lignes_corrigees = [
        {**brodee, "quantite": 1},
        {"produit_id": kit["id"], "quantite": 2},
        {"libelle": "Retouche des manches", "quantite": 1, "prix_unitaire": 1_000},
    ]
    corrigee = await client.put(
        f"/api/v1/admin/commandes/{reference}/articles",
        json={"lignes": lignes_corrigees, "prevenir_client": False},
        headers=ADMIN,
    )
    assert corrigee.status_code == 200, corrigee.text

    resultat = await a_recommander(client, reference, cle)
    assert resultat["lignes"] == [
        {
            "produit_id": blouse["id"],
            "variante_id": m["id"],
            "quantite": 1,
            "personnalisation": "Awa T. Infirmière",  # même broderie
            "slug": "blouse-medicale-brodee",
            "nom": blouse["nom"],
            "variante": m["libelle"],
            "rayon_slug": blouse["rayon_slug"],
            "prix_indicatif": 12_500,
        },
        {
            "produit_id": kit["id"],
            "variante_id": None,
            "quantite": 2,
            "personnalisation": None,
            "slug": "kit-hygiene",
            "nom": kit["nom"],
            "variante": None,
            "rayon_slug": kit["rayon_slug"],
            "prix_indicatif": 7_500,
        },
    ]
    assert resultat["ecartes"] == [
        "Retouche des manches : ligne sur mesure, à redemander à l'équipe"
    ]

    # La taille M n'est plus proposée, le kit n'est plus vendu : écartés, raison donnée.
    await client.patch(
        f"/api/v1/admin/variantes/{m['id']}", json={"est_active": False}, headers=ADMIN
    )
    await client.patch(
        f"/api/v1/admin/produits/{kit['id']}", json={"est_actif": False}, headers=ADMIN
    )
    resultat = await a_recommander(client, reference, cle)
    assert resultat["lignes"] == []
    assert resultat["ecartes"] == [
        f"{blouse['nom']} – {m['libelle']} : taille ou couleur à choisir de nouveau sur la fiche",
        f"{kit['nom']} : n'est plus vendu en ligne",
        "Retouche des manches : ligne sur mesure, à redemander à l'équipe",
    ]


async def test_compte_professionnel_et_acces(client: AsyncClient) -> None:
    soignante = jeton(["boutique:pro"], nom="Clinique Pasteur")
    creee = await commander(
        client, [await ligne(client, "blouse-medicale-brodee", "L")], entetes=soignante
    )
    reference, cle = creee["commande"]["reference"], creee["cle_suivi"]
    chemin = f"/api/v1/mes-commandes/{reference}/a-recommander"
    resultat = (await client.get(chemin, headers=soignante)).json()
    assert resultat["lignes"][0]["prix_indicatif"] == 11_000  # prix professionnel du jour
    assert (await client.get(chemin, headers=jeton(nom="Autre client"))).status_code == 404
    assert (await client.get(chemin)).status_code == 401
    faux = await client.get(f"/api/v1/suivi/{reference}/a-recommander", params={"cle": "x" * 20})
    assert faux.status_code == 404
    assert (await a_recommander(client, reference, cle))["lignes"][0]["prix_indicatif"] == 12_500
