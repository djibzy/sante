import pytest
from httpx import AsyncClient

from comptes.outils import changer_role

from .conftest import MOT_DE_PASSE, URL, inscrire


async def test_attribuer_puis_retirer_un_role(client: AsyncClient) -> None:
    await inscrire(client, telephone="76 12 34 56", nom="Awa Traoré")

    assert await changer_role("76123456", "boutique:admin", database_url=URL) == ["boutique:admin"]
    connexion = await client.post(
        "/api/v1/auth/connexion", json={"telephone": "76 12 34 56", "mot_de_passe": MOT_DE_PASSE}
    )
    assert connexion.json()["utilisateur"]["roles"] == ["boutique:admin"]

    assert await changer_role("+22376123456", "boutique:pro", database_url=URL) == [
        "boutique:admin",
        "boutique:pro",
    ]
    assert await changer_role("76 12 34 56", "boutique:admin", retirer=True, database_url=URL) == [
        "boutique:pro"
    ]


async def test_role_inconnu_ou_compte_absent(client: AsyncClient) -> None:
    with pytest.raises(ValueError, match="Rôle inconnu"):
        await changer_role("76 12 34 56", "boutique:admn", database_url=URL)
    with pytest.raises(LookupError):
        await changer_role("76 99 99 99", "boutique:pro", database_url=URL)
