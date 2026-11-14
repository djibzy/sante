"""Police des documents PDF de tous les services : Liberation Sans (licence OFL, fournie dans
ressources/polices), qui couvre tous les caractères du français. Rien à installer sur le
serveur : chaque service l'ajoute à ses documents fpdf2 sous le nom « Liberation »."""

from pathlib import Path

DOSSIER = Path(__file__).resolve().parent / "ressources" / "polices"
REGULIERE = DOSSIER / "LiberationSans-Regular.ttf"
GRASSE = DOSSIER / "LiberationSans-Bold.ttf"
