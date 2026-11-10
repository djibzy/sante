"""Photos des produits envoyées par l'équipe, souvent depuis un téléphone.

Chaque photo est vérifiée (vraie image JPEG, PNG ou WebP), redressée selon l'orientation du
téléphone, réduite à 1600 pixels et réencodée en WebP : le fichier servi ne garde aucune
métadonnée (position GPS, modèle de téléphone) et pèse quelques dizaines de kilo-octets.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from socle.ids import uuid7

FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}  # MPO : JPEG de certains téléphones
PIXELS_MAX = 40_000_000
COTE_MAX = 1600
SOUS_DOSSIER = "produits"


class PhotoRefusee(ValueError):
    """Le fichier n'est pas une photo exploitable."""


def enregistrer(contenu: bytes, dossier: Path) -> str:
    """Enregistre la photo et renvoie son adresse publique (/medias/produits/….webp)."""
    try:
        with Image.open(BytesIO(contenu)) as controle:
            if controle.format not in FORMATS:
                raise PhotoRefusee("Envoyez une photo JPEG, PNG ou WebP")
            if controle.width * controle.height > PIXELS_MAX:
                raise PhotoRefusee("Photo trop grande : 40 millions de pixels au plus")
            controle.verify()
        with Image.open(BytesIO(contenu)) as originale:
            redressee: Image.Image = ImageOps.exif_transpose(originale)
            if redressee.mode in ("RGBA", "LA", "P"):
                image = Image.new("RGB", redressee.size, (255, 255, 255))
                rgba = redressee.convert("RGBA")
                image.paste(rgba, mask=rgba.getchannel("A"))
            else:
                image = redressee.convert("RGB")
            image.thumbnail((COTE_MAX, COTE_MAX), Image.Resampling.LANCZOS)
            cible = dossier / SOUS_DOSSIER
            cible.mkdir(parents=True, exist_ok=True)
            nom = f"{uuid7()}.webp"
            image.save(cible / nom, "WEBP", quality=82, method=4)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PhotoRefusee("Ce fichier n'est pas une photo lisible") from exc
    return f"/medias/{SOUS_DOSSIER}/{nom}"
