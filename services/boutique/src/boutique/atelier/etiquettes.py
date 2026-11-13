"""Étiquettes de fabrication : une par pièce de la file, à épingler sur le vêtement.

A4, deux colonnes de quatre étiquettes : référence en grand, client, article, taille et couleur
sur leur propre ligne, texte à broder en entier et en évidence, quantité, poste et date promise.
Le brodeur ne confond plus deux blouses blanches taille M au nom de deux infirmières.
"""

from dataclasses import dataclass
from datetime import date

from fpdf import FPDF

from boutique.commandes.pdf import BLEU, DOUX, ENCRE, RESSOURCES

COLONNES, RANGEES = 2, 4
MARGE, ECART = 10.0, 4.0
LARGEUR = (210 - 2 * MARGE - ECART) / COLONNES
HAUTEUR = (297 - 2 * MARGE - (RANGEES - 1) * ECART) / RANGEES
INTERIEUR = 4.0
# Ce que l'atelier fait du texte, selon le poste de la pièce.
TITRES_TEXTE = {"broderie": "Texte à broder", "impression": "Texte à imprimer"}


@dataclass(frozen=True)
class Etiquette:
    reference: str
    client: str
    libelle: str
    personnalisation: str | None
    quantite: int
    poste: str  # nom affiché
    poste_code: str
    date_promise: date | None


def _morceaux(pdf: FPDF, mot: str, largeur: float) -> list[str]:
    """Un mot plus large que l'étiquette (nom composé sans espace) est coupé où il faut."""
    morceaux, courant = [], ""
    for lettre in mot:
        if courant and pdf.get_string_width(courant + lettre) > largeur:
            morceaux.append(courant)
            courant = ""
        courant += lettre
    return [*morceaux, courant] if courant else morceaux


def _couper(pdf: FPDF, texte: str, largeur: float, lignes_max: int) -> list[str]:
    """Coupe aux espaces pour tenir dans la largeur ; « … » si le texte dépasse."""
    mots = [m for mot in texte.split() for m in _morceaux(pdf, mot, largeur)]
    lignes, courante = [], ""
    for mot in mots:
        essai = f"{courante} {mot}".strip()
        if pdf.get_string_width(essai) <= largeur or not courante:
            courante = essai
        else:
            lignes.append(courante)
            courante = mot
    if courante:
        lignes.append(courante)
    if len(lignes) > lignes_max:
        lignes = lignes[:lignes_max]
        while lignes[-1] and pdf.get_string_width(lignes[-1] + " …") > largeur:
            lignes[-1] = lignes[-1][:-1]
        lignes[-1] += " …"
    return lignes


ENTETE_CADRE, BAS_CADRE = 5.0, 1.5  # « Texte à broder », puis marge sous la dernière ligne


def _texte_a_broder(
    pdf: FPDF, texte: str, largeur: float, hauteur_max: float
) -> tuple[float, float, list[str]]:
    """Le texte en entier, dans la place qui reste : police réduite s'il le faut."""
    for taille, interligne in ((11.0, 5.0), (9.5, 4.3), (8.0, 3.7)):
        pdf.set_font("Liberation", "B", taille)
        lignes = _couper(pdf, f"« {texte} »", largeur, 99)
        if ENTETE_CADRE + len(lignes) * interligne + BAS_CADRE <= hauteur_max:
            return taille, interligne, lignes
    tiennent = max(1, int((hauteur_max - ENTETE_CADRE - BAS_CADRE) // interligne))
    return taille, interligne, _couper(pdf, f"« {texte} »", largeur, tiennent)


def _etiquette(pdf: FPDF, x: float, y: float, e: Etiquette) -> None:
    pdf.set_draw_color(*DOUX)
    pdf.set_line_width(0.2)
    pdf.rect(x, y, LARGEUR, HAUTEUR, round_corners=True, corner_radius=3)
    gauche, utile = x + INTERIEUR, LARGEUR - 2 * INTERIEUR
    curseur = y + INTERIEUR

    pdf.set_text_color(*BLEU)
    pdf.set_font("Liberation", "B", 18)
    pdf.set_xy(gauche, curseur)
    pdf.cell(utile * 0.6, 8, e.reference)
    pdf.set_text_color(*ENCRE)
    pdf.set_font("Liberation", "B", 14)
    pdf.cell(utile * 0.4, 8, f"× {e.quantite}", align="R")
    curseur += 8

    pdf.set_font("Liberation", "", 9)
    pdf.set_text_color(*DOUX)
    pdf.set_xy(gauche, curseur)
    pdf.cell(utile, 4.5, _couper(pdf, e.client, utile, 1)[0])
    curseur += 5.5

    # « Blouse médicale brodée – Taille L · Blanc » : la taille et la couleur ne sont jamais
    # coupées, elles ont leur ligne.
    nom, _, variante = e.libelle.rpartition(" – ") if " – " in e.libelle else (e.libelle, "", "")
    pdf.set_text_color(*ENCRE)
    pdf.set_font("Liberation", "B", 10)
    for ligne in _couper(pdf, nom, utile, 2):
        pdf.set_xy(gauche, curseur)
        pdf.cell(utile, 4.6, ligne)
        curseur += 4.6
    if variante:
        pdf.set_font("Liberation", "B", 11.5)
        pdf.set_text_color(*BLEU)
        pdf.set_xy(gauche, curseur + 0.5)
        pdf.cell(utile, 5.5, _couper(pdf, variante, utile, 1)[0])
        curseur += 6.5

    if e.personnalisation:
        curseur += 1
        pied = y + HAUTEUR - INTERIEUR - 5  # ligne du poste et de la date
        taille, interligne, lignes = _texte_a_broder(
            pdf, e.personnalisation, utile - 4, pied - 1 - curseur
        )
        hauteur = ENTETE_CADRE + len(lignes) * interligne + BAS_CADRE
        pdf.set_fill_color(238, 236, 255)
        pdf.rect(gauche, curseur, utile, hauteur, style="F", round_corners=True, corner_radius=2)
        pdf.set_font("Liberation", "", 7.5)
        pdf.set_text_color(*DOUX)
        pdf.set_xy(gauche + 2, curseur + 1)
        pdf.cell(utile - 4, 3.5, TITRES_TEXTE.get(e.poste_code, "Personnalisation"))
        pdf.set_font("Liberation", "B", taille)
        pdf.set_text_color(*ENCRE)
        for k, ligne in enumerate(lignes):
            pdf.set_xy(gauche + 2, curseur + ENTETE_CADRE + k * interligne)
            pdf.cell(utile - 4, interligne, ligne)

    pdf.set_font("Liberation", "", 9)
    pdf.set_text_color(*DOUX)
    pdf.set_xy(gauche, y + HAUTEUR - INTERIEUR - 5)
    pdf.cell(utile / 2, 5, e.poste)
    pour = f"Pour le {e.date_promise:%d/%m}" if e.date_promise else "Sans date"
    pdf.set_font("Liberation", "B", 9)
    pdf.cell(utile / 2, 5, pour, align="R")


def etiquettes_pdf(etiquettes: list[Etiquette]) -> bytes:
    pdf = FPDF(format="A4", unit="mm")
    pdf.add_font("Liberation", "", RESSOURCES / "polices" / "LiberationSans-Regular.ttf")
    pdf.add_font("Liberation", "B", RESSOURCES / "polices" / "LiberationSans-Bold.ttf")
    pdf.set_auto_page_break(False)
    pdf.set_creator("Bibou")
    pdf.set_title("Étiquettes de fabrication")
    par_page = COLONNES * RANGEES
    for i, etiquette in enumerate(etiquettes or [None]):  # une page même vide
        if i % par_page == 0:
            pdf.add_page()
        if etiquette is None:
            pdf.set_font("Liberation", "", 11)
            pdf.set_xy(MARGE, MARGE)
            pdf.cell(0, 8, "Aucune pièce dans la file.")
            continue
        colonne, rangee = (i % par_page) % COLONNES, (i % par_page) // COLONNES
        _etiquette(
            pdf,
            MARGE + colonne * (LARGEUR + ECART),
            MARGE + rangee * (HAUTEUR + ECART),
            etiquette,
        )
    return bytes(pdf.output())
