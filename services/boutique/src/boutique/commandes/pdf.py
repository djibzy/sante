"""Devis et factures en PDF, au format A4, aux couleurs de Bibou.

fpdf2 est en Python pur : rien à installer sur le serveur. La police Liberation Sans (licence
OFL, fournie dans ressources/polices) couvre tous les caractères du français.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from fastapi import HTTPException, Response, status
from fpdf import FPDF, FontFace

from boutique.commandes.cycle import Moyen
from boutique.commandes.lettres import francs_cfa
from boutique.config import ParametresBoutique
from boutique.models import Commande
from socle.telephones import afficher_telephone

RESSOURCES = Path(__file__).resolve().parents[1] / "ressources"
BLEU = (16, 0, 208)
ENCRE = (23, 21, 58)
DOUX = (91, 90, 120)
PIED = "Bibou, une marque de Yasal Santé"
MOYENS = {
    Moyen.ESPECES: "espèces",
    Moyen.ORANGE_MONEY: "Orange Money",
    Moyen.MOOV_MONEY: "Moov Money",
    Moyen.VIREMENT: "virement",
    Moyen.CHEQUE: "chèque",
}


def fcfa(montant: int) -> str:
    return f"{montant:,}".replace(",", " ") + " FCFA"


def _date(jour: date) -> str:
    return jour.strftime("%d/%m/%Y")


@dataclass(frozen=True)
class Entete:
    titre: str  # « Devis » ou « Facture »
    lignes: tuple[str, ...]  # numéro, dates…
    arrete: str  # « Arrêté le présent devis » / « Arrêtée la présente facture »


class _Document(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4", unit="mm")
        self.add_font("Liberation", "", RESSOURCES / "polices" / "LiberationSans-Regular.ttf")
        self.add_font("Liberation", "B", RESSOURCES / "polices" / "LiberationSans-Bold.ttf")
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, margin=24)
        self.set_creator("Bibou")
        self.set_author("Bibou, Yasal Santé")

    def footer(self) -> None:
        self.set_y(-16)
        self.set_font("Liberation", "", 8)
        self.set_text_color(*DOUX)
        self.cell(0, 5, f"{PIED} – page {self.page_no()}/{{nb}}", align="C")


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


def _total(pdf: FPDF, intitule: str, valeur: str, fort: bool = False) -> None:
    pdf.set_x(110)
    pdf.set_font("Liberation", "B" if fort else "", 12 if fort else 10)
    pdf.set_text_color(*(BLEU if fort else ENCRE))
    pdf.cell(52, 8 if fort else 6, intitule)
    pdf.cell(30, 8 if fort else 6, valeur, align="R", new_x="LMARGIN", new_y="NEXT")


def _document(
    commande: Commande, parametres: ParametresBoutique, entete: Entete, paiements: bool
) -> bytes:
    pdf = _Document()
    pdf.set_title(f"{entete.titre} {entete.lignes[0]}")
    pdf.add_page()

    pdf.image(RESSOURCES / "bibou.png", x=18, y=14, w=44)
    pdf.set_xy(110, 15)
    pdf.set_font("Liberation", "B", 20)
    pdf.set_text_color(*BLEU)
    pdf.cell(82, 9, entete.titre, align="R", new_x="LEFT", new_y="NEXT")
    pdf.set_font("Liberation", "", 10)
    pdf.set_text_color(*ENCRE)
    for texte in entete.lignes:
        pdf.cell(82, 5, texte, align="R", new_x="LEFT", new_y="NEXT")

    haut = 46
    livraison = f"Livraison : {commande.zone.nom}" if commande.zone else "Retrait à la boutique"
    fin_gauche = _bloc(pdf, 18, haut, 80, "Émetteur", [PIED, *parametres.coordonnees.splitlines()])
    fin_droite = _bloc(
        pdf,
        110,
        haut,
        82,
        "Client",
        [
            commande.etablissement or commande.nom_client,
            commande.nom_client if commande.etablissement else "",
            afficher_telephone(commande.telephone),
            commande.email or "",
            livraison,
            commande.adresse,
        ],
    )

    pdf.set_xy(18, max(fin_gauche, fin_droite) + 8)
    pdf.set_font("Liberation", "", 9.5)
    pdf.set_draw_color(*DOUX)
    with pdf.table(
        col_widths=(98, 16, 30, 30),
        text_align=("LEFT", "RIGHT", "RIGHT", "RIGHT"),
        headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=BLEU),
        borders_layout="HORIZONTAL_LINES",
        line_height=5.5,
        padding=1.6,
    ) as tableau:
        ligne_entete = tableau.row()
        for titre in ("Désignation", "Qté", "Prix unitaire", "Montant"):
            ligne_entete.cell(titre)
        for ligne in commande.lignes:
            rangee = tableau.row()
            designation = ligne.libelle
            if ligne.personnalisation:
                designation += f"\nBroderie : {ligne.personnalisation}"
            rangee.cell(designation)
            rangee.cell(str(ligne.quantite))
            rangee.cell(fcfa(ligne.prix_unitaire))
            rangee.cell(fcfa(ligne.montant))

    pdf.ln(4)
    _total(pdf, "Sous-total", fcfa(commande.sous_total))
    if commande.remise:
        _total(pdf, "Remise", "- " + fcfa(commande.remise))
    if commande.zone:
        livre = fcfa(commande.frais_livraison) if commande.frais_livraison else "Offerte"
        _total(pdf, "Livraison", livre)
    else:
        _total(pdf, "Retrait à la boutique", fcfa(0))
    _total(pdf, "Total", fcfa(commande.total), fort=True)
    if paiements:
        for paiement in commande.paiements:
            jour = _date(paiement.encaisse_le.date())
            _total(pdf, f"Payé le {jour} ({MOYENS[Moyen(paiement.moyen)]})", fcfa(paiement.montant))
        _total(pdf, "Reste à payer", fcfa(commande.reste_a_payer), fort=True)

    pdf.ln(4)
    pdf.set_text_color(*ENCRE)
    pdf.set_font("Liberation", "", 10)
    somme = francs_cfa(commande.total)
    pdf.multi_cell(0, 5, f"{entete.arrete} à la somme de {somme}.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Liberation", "", 9)
    pdf.set_text_color(*DOUX)
    if not paiements:
        pdf.multi_cell(0, 4.6, parametres.conditions_devis, new_x="LMARGIN", new_y="NEXT")
    if parametres.mentions_legales:
        pdf.ln(2)
        pdf.multi_cell(0, 4.6, parametres.mentions_legales, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def devis_pdf(commande: Commande, parametres: ParametresBoutique) -> bytes:
    emis = commande.devis_emis_le.date() if commande.devis_emis_le else commande.cree_le.date()
    lignes = [f"N° {commande.reference}", f"Émis le {_date(emis)}"]
    if commande.devis_valable_jusqu_au:
        lignes.append(f"Valable jusqu'au {_date(commande.devis_valable_jusqu_au)}")
    entete = Entete("Devis", tuple(lignes), "Arrêté le présent devis")
    return _document(commande, parametres, entete, paiements=False)


def facture_pdf(commande: Commande, parametres: ParametresBoutique) -> bytes:
    facture = commande.facture
    assert facture is not None
    entete = Entete(
        "Facture",
        (
            f"N° {facture.reference}",
            f"Émise le {_date(facture.emise_le.date())}",
            f"Commande {commande.reference}",
        ),
        "Arrêtée la présente facture",
    )
    return _document(commande, parametres, entete, paiements=True)


def _reponse(contenu: bytes, nom: str) -> Response:
    return Response(
        contenu,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{nom}.pdf"',
            "Cache-Control": "no-store",
        },
    )


def reponse_devis(commande: Commande, parametres: ParametresBoutique) -> Response:
    if commande.devis_emis_le is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Le devis n'a pas encore été établi")
    return _reponse(devis_pdf(commande, parametres), f"devis-{commande.reference}")


def reponse_facture(commande: Commande, parametres: ParametresBoutique) -> Response:
    if commande.facture is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "La facture n'a pas encore été émise")
    return _reponse(facture_pdf(commande, parametres), f"facture-{commande.facture.reference}")
