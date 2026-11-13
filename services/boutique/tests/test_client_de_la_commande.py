"""Le client de la commande, vu par l'équipe : ses autres commandes au même numéro."""

from httpx import AsyncClient

from .aides import commander, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])


async def test_client_de_la_commande(client: AsyncClient) -> None:
    kit = [await ligne(client, "kit-hygiene")]  # 7 500 FCFA
    premiere = (await commander(client, kit))["commande"]["reference"]
    for etape in ("confirmee", "en_preparation", "prete", "livree"):
        reponse = await client.post(
            f"/api/v1/admin/commandes/{premiere}/statut", json={"statut": etape}, headers=ADMIN
        )
        assert reponse.status_code == 200, reponse.text
    annulee = (await commander(client, kit, telephone="+223 76 12 34 56"))["commande"]["reference"]
    await client.post(
        f"/api/v1/admin/commandes/{annulee}/statut", json={"statut": "annulee"}, headers=ADMIN
    )
    await commander(client, kit, telephone="66 99 88 77")  # autre client
    courante = (await commander(client, kit))["commande"]["reference"]

    resume = await client.get(f"/api/v1/admin/commandes/{courante}/client", headers=ADMIN)
    assert resume.status_code == 200, resume.text
    donnees = resume.json()
    assert (donnees["autres_commandes"], donnees["remises"], donnees["annulees"]) == (2, 1, 1)
    assert donnees["depense"] == 7_500
    assert [c["reference"] for c in donnees["dernieres"]] == [annulee, premiere]
    assert donnees["dernieres"][1]["statut_libelle"] == "Livrée"
    seule = await client.get(f"/api/v1/admin/commandes/{premiere}/client", headers=ADMIN)
    assert seule.json()["autres_commandes"] == 2
    assert (await client.get(f"/api/v1/admin/commandes/{courante}/client")).status_code == 401
