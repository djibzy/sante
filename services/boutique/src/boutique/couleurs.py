"""Couleurs du catalogue : familles du nuancier (page « Explorer ») et proximité entre deux
couleurs, mesurées dans l'espace OKLab, proche de la perception humaine.

Une distance de 100 sépare le noir du blanc ; en dessous de 5, deux couleurs se confondent à
l'œil, au-delà de 20 elles sont nettement différentes.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Famille:
    code: str
    nom: str
    hex: str  # pastille du nuancier


# Dans l'ordre du cercle des couleurs, du blanc aux neutres.
FAMILLES = (
    Famille("blanc", "Blancs", "#ffffff"),
    Famille("rose", "Roses", "#e58fa5"),
    Famille("rouge", "Rouges et bordeaux", "#7a1f35"),
    Famille("orange", "Jaunes, orangés, beiges", "#e07b1f"),
    Famille("vert", "Verts et turquoises", "#2e8b6e"),
    Famille("bleu", "Bleus", "#1f4fa8"),
    Famille("violet", "Violets et prunes", "#6b2d5c"),
    Famille("gris", "Gris et noirs", "#5b6770"),
)
CODES = tuple(f.code for f in FAMILLES)
NEUTRE = 0.035  # chroma en dessous duquel une couleur est un blanc, un gris ou un noir


def _lineaire(composante: float) -> float:
    if composante <= 0.04045:
        return composante / 12.92
    return float(((composante + 0.055) / 1.055) ** 2.4)


def oklab(hexa: str) -> tuple[float, float, float]:
    """« #rrggbb » vers OKLab (L de 0 à 1, a et b autour de 0)."""
    r, g, b = (_lineaire(int(hexa[i : i + 2], 16) / 255) for i in (1, 3, 5))
    l_ = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklch(hexa: str) -> tuple[float, float, float]:
    """Clarté, chroma (intensité) et teinte en degrés."""
    clarte, a, b = oklab(hexa)
    return clarte, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def distance(une: str, autre: str) -> float:
    """Écart perçu entre deux couleurs, de 0 (identiques) à 100 (noir et blanc)."""
    return 100 * math.dist(oklab(une), oklab(autre))


def famille(hexa: str) -> str:
    clarte, chroma, teinte = oklch(hexa)
    if chroma < NEUTRE:
        return "blanc" if clarte >= 0.9 else "gris"
    if teinte < 45 or teinte >= 345:
        return "rose" if clarte >= 0.65 else "rouge"
    if teinte < 115:
        return "orange"
    if teinte < 225:
        return "vert"
    if teinte < 290:
        return "bleu"
    return "violet"


def rang(hexa: str) -> tuple[int, int]:
    """Ordre du mur de couleurs : par famille, puis du plus clair au plus foncé (par paliers,
    pour que des teintes presque égales se rangent ensuite par type d'article)."""
    return CODES.index(famille(hexa)), -round(oklch(hexa)[0] * 20)
