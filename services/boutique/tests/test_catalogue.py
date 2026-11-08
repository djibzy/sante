from httpx import AsyncClient

from boutique.donnees_demo import PRODUITS, RAYONS
from boutique.routes.catalogue import motif_recherche


async def test_rayons_dans_l_ordre_avec_leur_nombre_de_produits(client: AsyncClient) -> None:
    rayons = (await client.get("/api/v1/rayons")).json()

    assert [r["slug"] for r in rayons] == [r["slug"] for r in RAYONS]
    assert sum(r["nombre_produits"] for r in rayons) == len(PRODUITS)
    tenues = next(r for r in rayons if r["slug"] == "tenues-brodees")
    assert tenues["nombre_produits"] == 4


async def test_liste_paginee(client: AsyncClient) -> None:
    page = (await client.get("/api/v1/produits", params={"par_page": 5, "page": 2})).json()

    assert page["total"] == len(PRODUITS)
    assert len(page["elements"]) == 5
    assert page["page"] == 2


async def test_filtre_par_rayon(client: AsyncClient) -> None:
    page = (await client.get("/api/v1/produits", params={"rayon": "kits"})).json()
    assert {p["rayon_slug"] for p in page["elements"]} == {"kits"}
    assert page["total"] == 3


async def test_recherche_sans_accents_ni_majuscules(client: AsyncClient) -> None:
    for texte in ("medicale", "MÉDICALE", "Médicale"):
        page = (await client.get("/api/v1/produits", params={"q": texte})).json()
        assert [p["slug"] for p in page["elements"]] == ["blouse-medicale-brodee"], texte


async def test_recherche_dans_le_resume(client: AsyncClient) -> None:
    page = (await client.get("/api/v1/produits", params={"q": "causeries"})).json()
    assert [p["slug"] for p in page["elements"]] == ["boite-a-images"]


async def test_recherche_avec_caracteres_speciaux(client: AsyncClient) -> None:
    assert motif_recherche("50%_x") == "%50\\%\\_x%"
    page = (await client.get("/api/v1/produits", params={"q": "%"})).json()
    assert page["total"] == 0


async def test_fiche_produit_avec_variantes(client: AsyncClient) -> None:
    fiche = (await client.get("/api/v1/produits/blouse-medicale-brodee")).json()

    assert fiche["prix_public"] == 12500
    assert fiche["personnalisable"] is True
    assert fiche["vendable_en_ligne"] is True
    assert [v["taille"] for v in fiche["variantes"]] == ["S", "M", "L", "XL"]
    assert {v["prix"] for v in fiche["variantes"]} == {12500}
    assert fiche["variantes"][0]["libelle"] == "Taille S · Blanc"


async def test_produit_du_domaine_pharmaceutique_sans_prix(client: AsyncClient) -> None:
    fiche = (await client.get("/api/v1/produits/gants-steriles")).json()

    assert fiche["categorie_reglementaire"] == "pharmaceutique"
    assert fiche["vendable_en_ligne"] is False
    assert fiche["prix_public"] is None
    assert fiche["prix_pro"] is None


async def test_produit_inconnu(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/produits/inexistant")).status_code == 404


async def test_sante(client: AsyncClient) -> None:
    assert (await client.get("/sante")).json()["statut"] == "ok"
