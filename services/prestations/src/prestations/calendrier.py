"""Dates de la tournée et des relevés. Le Mali est à l'heure UTC toute l'année ; le dimanche,
aucun linge ne bouge."""

import re
from datetime import UTC, date, datetime, timedelta

from prestations.linge import JOURS

MOIS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)  # fmt: skip
FORMAT_MOIS = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def maintenant() -> datetime:
    return datetime.now(UTC)


def aujourd_hui() -> date:
    return maintenant().date()


def date_de_retour(enlevement: date, jours: int) -> date:
    """Le retour promis : `jours` jours après l'enlèvement, sans compter les dimanches."""
    jour, restants = enlevement, jours
    while restants > 0:
        jour += timedelta(days=1)
        if jour.isoweekday() != 7:
            restants -= 1
    return jour


def jours_en_toutes_lettres(jours: list[int]) -> str:
    """[1, 4] : « lundi et jeudi » ; [] : « sur appel »."""
    noms = [JOURS[j - 1] for j in sorted(jours)]
    if not noms:
        return "sur appel"
    return noms[0] if len(noms) == 1 else f"{', '.join(noms[:-1])} et {noms[-1]}"


def bornes_du_mois(mois: str) -> tuple[datetime, datetime]:
    """« 2026-11 » : du 1er novembre 0 h au 1er décembre 0 h (heure de Bamako, donc UTC)."""
    trouve = FORMAT_MOIS.match(mois)
    if not trouve:
        raise ValueError("Mois attendu au format AAAA-MM")
    annee, numero = int(trouve.group(1)), int(trouve.group(2))
    debut = datetime(annee, numero, 1, tzinfo=UTC)
    fin = datetime(annee + numero // 12, numero % 12 + 1, 1, tzinfo=UTC)
    return debut, fin


def mois_en_toutes_lettres(mois: str) -> str:
    debut, _ = bornes_du_mois(mois)
    return f"{MOIS[debut.month - 1]} {debut.year}"


def date_courte(jour: date) -> str:
    """« jeu. 19/11 » : pour les SMS et la tournée."""
    return f"{JOURS[jour.isoweekday() - 1][:3]}. {jour:%d/%m}"
