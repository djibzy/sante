from io import BytesIO
from pathlib import Path

from fastapi import FastAPI
from httpx import AsyncClient, Response
from PIL import Image

from .aides import fiche
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])


def photo(format_: str = "JPEG", taille: tuple[int, int] = (3000, 2000)) -> bytes:
    image = Image.new("RGB", taille, (16, 0, 208))
    exif = Image.Exif()
    exif[0x0110] = "Telephone de test"  # modèle de l'appareil, à ne pas publier
    tampon = BytesIO()
    image.save(tampon, format_, exif=exif) if format_ == "JPEG" else image.save(tampon, format_)
    return tampon.getvalue()


async def envoyer(
    client: AsyncClient, produit_id: str, contenu: bytes, nom: str = "p.jpg"
) -> Response:
    return await client.post(
        f"/api/v1/admin/produits/{produit_id}/photos",
        files={"fichier": (nom, contenu, "image/jpeg")},
        data={"texte_alternatif": "Tunique bleu roi, de face"},
        headers=ADMIN,
    )


async def test_photo_reduite_sans_metadonnees_puis_servie(
    app: FastAPI, client: AsyncClient
) -> None:
    tunique = await fiche(client, "tunique-col-v")
    reponse = await envoyer(client, tunique["id"], photo())
    assert reponse.status_code == 201, reponse.text
    [image] = reponse.json()["images"]
    assert image["url"].startswith("/medias/produits/") and image["url"].endswith(".webp")
    fichier = Path(app.state.parametres.dossier_medias) / image["url"].removeprefix("/medias/")
    with Image.open(fichier) as enregistree:
        assert enregistree.format == "WEBP" and max(enregistree.size) == 1600
        assert not enregistree.getexif()
    servie = await client.get(image["url"])
    assert servie.status_code == 200 and servie.headers["content-type"] == "image/webp"
    assert (await fiche(client, "tunique-col-v"))["images"][0]["url"] == image["url"]


async def test_fichiers_refuses(app: FastAPI, client: AsyncClient) -> None:
    tunique = await fiche(client, "tunique-col-v")
    texte = await envoyer(client, tunique["id"], b"<script>alert(1)</script>", "x.jpg")
    assert texte.status_code == 422
    gif = BytesIO()
    Image.new("RGB", (10, 10)).save(gif, "GIF")
    assert (await envoyer(client, tunique["id"], gif.getvalue())).status_code == 422
    app.state.parametres.taille_max_photo = 1000
    assert (await envoyer(client, tunique["id"], photo())).status_code == 413
    anonyme = await client.post(
        f"/api/v1/admin/produits/{tunique['id']}/photos",
        files={"fichier": ("p.jpg", photo(), "image/jpeg")},
        data={"texte_alternatif": "Photo"},
    )
    assert anonyme.status_code == 401


async def test_png_transparent_sur_fond_blanc(client: AsyncClient) -> None:
    calot = await fiche(client, "calot-wax")
    tampon = BytesIO()
    Image.new("RGBA", (400, 400), (0, 0, 0, 0)).save(tampon, "PNG")
    reponse = await envoyer(client, calot["id"], tampon.getvalue(), "calot.png")
    assert reponse.status_code == 201
