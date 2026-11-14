"""Relevé mensuel en PDF, à remettre à la structure avec la facture : pièces enlevées, rendues et
manquantes article par article, bons de collecte du mois, montant dû. Jamais les coûts des
partenaires ni la marge."""

from contextlib import AbstractContextManager
from pathlib import Path

from fpdf import FPDF, FontFace
from fpdf.table import Table

from prestations.config import ParametresPrestations
from prestations.etats import Formule
from prestations.linge import TYPES_STRUCTURE
from prestations.schemas import Releve
from socle import polices
from socle.telephones import afficher_telephone

LOGO = Path(__file__).resolve().parent / "ressources" / "yasal-sante.png"
VERT = (23, 122, 74)
ENCRE = (21, 36, 29)
DOUX = (86, 101, 93)


def fcfa(montant: int) -> str:
    return f"{montant:,}".replace(",", " ") + " FCFA"


class DocumentReleve(FPDF):
    def __init__(self, pied: str) -> None:
        super().__init__(format="A4", unit="mm")
        self.pied = pied
        self.add_font("Liberation", "", polices.REGULIERE)
        self.add_font("Liberation", "B", polices.GRASSE)
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, margin=24)
        self.set_creator(pied)
        self.set_author(pied)

    def footer(self) -> None:
        self.set_y(-16)
        self.set_font("Liberation", "", 8)
        self.set_text_color(*DOUX)
        self.cell(0, 5, f"{self.pied} – page {self.page_no()}/{{nb}}", align="C")


def _bloc(pdf: FPDF, x: float, y: float, largeur: float, titre: str, lignes: list[str]) -> float:
    pdf.set_xy(x, y)
    pdf.set_font("Liberation", "B", 9)
    pdf.set_text_color(*DOUX)
    pdf.cell(largeur, 5, titre, new_x="LEFT", new_y="NEXT")
    pdf.set_text_color(*ENCRE)
    for i, ligne in enumerate(ligne for ligne in lignes if ligne):
        pdf.set_font("Liberation", "B" if i == 0 else "", 10)
        pdf.multi_cell(largeur, 5, ligne, new_x="LEFT", new_y="NEXT")
    return pdf.get_y()


def _tableau(
    pdf: FPDF, largeurs: tuple[float, ...], alignements: tuple[str, ...]
) -> AbstractContextManager[Table]:
    pdf.set_font("Liberation", "", 9.5)
    pdf.set_text_color(*ENCRE)
    pdf.set_draw_color(*DOUX)
    return pdf.table(
        col_widths=largeurs,
        text_align=alignements,
        headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=VERT),
        borders_layout="HORIZONTAL_LINES",
        line_height=5.5,
        padding=1.6,
    )


def _total(pdf: FPDF, intitule: str, valeur: str, fort: bool = False) -> None:
    pdf.set_x(100)
    pdf.set_font("Liberation", "B" if fort else "", 12 if fort else 10)
    pdf.set_text_color(*(VERT if fort else ENCRE))
    pdf.cell(62, 8 if fort else 6, intitule)
    pdf.cell(30, 8 if fort else 6, valeur, align="R", new_x="LMARGIN", new_y="NEXT")


def releve_pdf(releve: Releve, parametres: ParametresPrestations, emis_le: str) -> bytes:
    contrat = releve.contrat
    pdf = DocumentReleve(f"{parametres.nom_service} – Entretien du linge")
    pdf.set_title(f"Relevé {releve.libelle_mois} – {contrat.reference}")
    pdf.add_page()

    pdf.image(LOGO, x=18, y=15, w=46)
    pdf.set_xy(100, 15)
    pdf.set_font("Liberation", "B", 20)
    pdf.set_text_color(*VERT)
    pdf.cell(92, 9, "Relevé mensuel", align="R", new_x="LEFT", new_y="NEXT")
    pdf.set_font("Liberation", "", 10)
    pdf.set_text_color(*ENCRE)
    for texte in (
        f"Entretien du linge – {releve.libelle_mois}",
        f"Contrat {contrat.reference}",
        f"Émis le {emis_le}",
    ):
        pdf.cell(92, 5, texte, align="R", new_x="LEFT", new_y="NEXT")

    haut = 46
    fin_gauche = _bloc(
        pdf,
        18,
        haut,
        76,
        "Prestataire",
        [parametres.nom_service, *parametres.coordonnees.splitlines()],
    )
    fin_droite = _bloc(
        pdf,
        100,
        haut,
        92,
        "Structure",
        [
            contrat.structure,
            TYPES_STRUCTURE[contrat.type_structure],
            f"{contrat.contact} – {afficher_telephone(contrat.telephone)}",
            contrat.adresse,
        ],
    )
    pdf.set_xy(18, max(fin_gauche, fin_droite) + 6)
    pdf.set_font("Liberation", "", 9.5)
    pdf.set_text_color(*DOUX)
    pdf.multi_cell(
        0,
        5,
        f"Collectes : {contrat.libelle_jours}. Retour promis en {contrat.delai_retour_jours} "
        "jours ouvrés. Chaque pièce est comptée à l'enlèvement et au retour, devant votre "
        "personnel.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)

    a_la_piece = contrat.formule == Formule.PIECE
    if not releve.lignes:
        pdf.set_text_color(*ENCRE)
        pdf.set_font("Liberation", "", 10)
        pdf.cell(0, 6, "Aucun linge rendu ce mois-ci.", new_x="LMARGIN", new_y="NEXT")
    elif a_la_piece:
        with _tableau(
            pdf, (56, 20, 20, 24, 24, 30), ("LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT")
        ) as tableau:
            entete = tableau.row()
            for titre in ("Article", "Enlevées", "Rendues", "Manquantes", "Prix unit.", "Montant"):
                entete.cell(titre)
            for ligne in releve.lignes:
                rangee = tableau.row()
                rangee.cell(ligne.libelle)
                rangee.cell(str(ligne.enlevees))
                rangee.cell(str(ligne.rendues))
                rangee.cell(str(ligne.manquantes) if ligne.manquantes else "–")
                rangee.cell(
                    fcfa(ligne.prix_unitaire) if ligne.prix_unitaire is not None else "à fixer"
                )
                rangee.cell(fcfa(ligne.montant))
    else:
        with _tableau(pdf, (94, 26, 26, 28), ("LEFT", "RIGHT", "RIGHT", "RIGHT")) as tableau:
            entete = tableau.row()
            for titre in ("Article", "Enlevées", "Rendues", "Manquantes"):
                entete.cell(titre)
            for ligne in releve.lignes:
                rangee = tableau.row()
                rangee.cell(ligne.libelle)
                rangee.cell(str(ligne.enlevees))
                rangee.cell(str(ligne.rendues))
                rangee.cell(str(ligne.manquantes) if ligne.manquantes else "–")

    pdf.ln(4)
    _total(pdf, "Pièces rendues", str(releve.pieces_rendues))
    if releve.forfait is not None:
        _total(pdf, f"Forfait de {releve.libelle_mois}", fcfa(releve.forfait))
        if releve.pieces_supplementaires:
            _total(
                pdf,
                f"{releve.pieces_supplementaires} pièces au-delà des "
                f"{contrat.pieces_incluses} comprises",
                fcfa(releve.montant_supplement),
            )
    _total(pdf, "Total du mois", fcfa(releve.total), fort=True)

    if releve.pieces_manquantes:
        pdf.ln(2)
        pdf.set_font("Liberation", "", 9.5)
        pdf.set_text_color(*ENCRE)
        pdf.multi_cell(
            0,
            5,
            f"{releve.pieces_manquantes} pièce(s) manquante(s) au retour : elles ne sont pas "
            "facturées. Nous les recherchons ; une pièce perdue vous sera remplacée ou "
            "remboursée.",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    if releve.collectes:
        pdf.ln(4)
        pdf.set_font("Liberation", "B", 11)
        pdf.set_text_color(*ENCRE)
        pdf.cell(0, 7, "Bons de collecte du mois", new_x="LMARGIN", new_y="NEXT")
        with _tableau(
            pdf, (34, 40, 40, 30, 30), ("LEFT", "LEFT", "LEFT", "RIGHT", "RIGHT")
        ) as tableau:
            entete = tableau.row()
            for titre in ("Bon", "Enlevé le", "Rendu le", "Enlevées", "Rendues"):
                entete.cell(titre)
            for collecte in releve.collectes:
                rangee = tableau.row()
                rangee.cell(collecte.reference)
                rangee.cell(f"{collecte.enlevee_le:%d/%m/%Y}")
                rangee.cell(f"{collecte.rendue_le:%d/%m/%Y}")
                rangee.cell(str(collecte.pieces_enlevees))
                rangee.cell(str(collecte.pieces_rendues))

    pdf.ln(6)
    pdf.set_font("Liberation", "", 8.5)
    pdf.set_text_color(*DOUX)
    mentions = "Montants en francs CFA."
    if parametres.mentions_legales:
        mentions += f" {parametres.mentions_legales}"
    pdf.multi_cell(0, 4.5, mentions, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
