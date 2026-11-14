"""Images jointes aux messages (un logo, une photo du modèle à broder) : passées par le même
traitement que les photos des produits (vraie image, redressée, réduite, réencodée en WebP sans
métadonnée), mais gardées hors du dossier public. Elles ne se lisent que par l'API, avec la clé
du lien de suivi ou la session ; retirer un message efface son image.

Aucun autre type de fichier n'est accepté : pas de document, où une donnée de santé passerait
inaperçue.
"""

import re
from pathlib import Path

from boutique import photos
from socle.ids import uuid7

SOUS_DOSSIER = "messages"
_NOM = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\.webp")


def enregistrer(contenu: bytes, dossier: Path) -> str:
    """Enregistre l'image et renvoie le nom de son fichier (lève photos.PhotoRefusee)."""
    webp = photos.convertir(contenu)
    cible = dossier / SOUS_DOSSIER
    cible.mkdir(parents=True, exist_ok=True)
    nom = f"{uuid7()}.webp"
    (cible / nom).write_bytes(webp)
    return nom


def chemin(dossier: Path, nom: str) -> Path | None:
    """Le fichier d'une image de message, s'il existe (le nom vient de la base, jamais de
    l'adresse demandée ; son format est tout de même vérifié)."""
    if not _NOM.fullmatch(nom):
        return None
    fichier = dossier / SOUS_DOSSIER / nom
    return fichier if fichier.is_file() else None


def supprimer(dossier: Path, nom: str | None) -> None:
    if nom and (fichier := chemin(dossier, nom)):
        fichier.unlink(missing_ok=True)
