"""Raccourcis pour construire paniers et commandes dans les tests."""

from typing import Any

from httpx import AsyncClient

ADRESSE = "Hamdallaye ACI 2000, rue 300, porte 12, près de la pharmacie"


async def fiche(client: AsyncClient, slug: str) -> dict[str, Any]:
    reponse = await client.get(f"/api/v1/produits/{slug}")
    assert reponse.status_code == 200, reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees


async def ligne(
    client: AsyncClient,
    slug: str,
    taille: str | None = None,
    quantite: int = 1,
    personnalisation: str | None = None,
) -> dict[str, Any]:
    produit = await fiche(client, slug)
    variante = (
        next(v["id"] for v in produit["variantes"] if v["taille"] == taille) if taille else None
    )
    return {
        "produit_id": produit["id"],
        "variante_id": variante,
        "quantite": quantite,
        "personnalisation": personnalisation,
    }


async def zone(client: AsyncClient, slug: str = "bamako-commune-4") -> str:
    zones = (await client.get("/api/v1/zones-livraison")).json()
    return str(next(z["id"] for z in zones if z["slug"] == slug))


async def commander(
    client: AsyncClient,
    lignes: list[dict[str, Any]],
    *,
    telephone: str = "76 12 34 56",
    nom: str = "Aminata Traoré",
    livraison: dict[str, Any] | None = None,
    entetes: dict[str, str] | None = None,
    cle: str | None = None,
) -> dict[str, Any]:
    corps: dict[str, Any] = {
        "client": {"nom": nom, "telephone": telephone},
        "livraison": livraison or {"mode": "retrait"},
        "lignes": lignes,
    }
    if cle:
        corps["cle_suivi"] = cle
    reponse = await client.post("/api/v1/commandes", json=corps, headers=entetes or {})
    assert reponse.status_code in (200, 201), reponse.text
    donnees: dict[str, Any] = reponse.json()
    return donnees
