"""Catalogue imprimable : tous les produits en ligne, rayon par rayon, avec leurs prix.

Pour les structures qui préparent un achat groupé, ou pour l'affichage en boutique. Les
articles du domaine pharmaceutique y figurent sans prix (pharmacien partenaire).
"""

from fpdf import FontFace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from boutique.commandes.pdf import BLEU, DOUX, ENCRE, RESSOURCES, DocumentBibou, fcfa
from boutique.commandes.tarifs import aujourd_hui
from boutique.models import Produit, Rayon
from boutique.vues import rang_taille


def _tailles(tailles: list[str]) -> str:
    if not tailles:
        return ""
    ordonnees = sorted(tailles, key=rang_taille)
    return ordonnees[0] if len(ordonnees) == 1 else f"{ordonnees[0]} à {ordonnees[-1]}"


async def catalogue_pdf(session: AsyncSession) -> bytes:
    produits = (
        (
            await session.execute(
                select(Produit)
                .join(Produit.rayon)
                .options(contains_eager(Produit.rayon), selectinload(Produit.variantes))
                .where(Produit.est_actif, Rayon.est_actif)
                .order_by(Rayon.position, Rayon.nom, Produit.nom)
            )
        )
        .scalars()
        .unique()
        .all()
    )
    pdf = DocumentBibou()
    pdf.set_title("Catalogue Bibou")
    pdf.add_page()
    pdf.image(RESSOURCES / "bibou.png", x=18, y=40, w=90)
    pdf.set_xy(18, 90)
    pdf.set_font("Liberation", "B", 28)
    pdf.set_text_color(*BLEU)
    pdf.cell(0, 14, "Catalogue", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Liberation", "", 13)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(
        0,
        7,
        "Tenues médicales brodées à votre nom, kits de soins, matériel médical et supports de "
        "campagne. Fabriqué et brodé à Bamako.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)
    pdf.set_font("Liberation", "", 10)
    pdf.set_text_color(*DOUX)
    pdf.multi_cell(
        0,
        5.5,
        f"Édition du {aujourd_hui().strftime('%d/%m/%Y')}. Prix en francs CFA. Prix "
        "professionnel pour les soignants et les structures dont le statut a été vérifié. "
        "Paiement à la livraison. Pour un achat groupé, demandez un devis.",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    rayon_courant = None
    entete = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=BLEU)
    for rayon in dict.fromkeys(p.rayon for p in produits):
        lignes = [p for p in produits if p.rayon is rayon]
        if rayon is not rayon_courant:
            pdf.add_page()
            rayon_courant = rayon
        pdf.set_font("Liberation", "B", 16)
        pdf.set_text_color(*BLEU)
        pdf.cell(0, 9, rayon.nom, new_x="LMARGIN", new_y="NEXT")
        if rayon.description:
            pdf.set_font("Liberation", "", 9.5)
            pdf.set_text_color(*DOUX)
            pdf.multi_cell(0, 5, rayon.description, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_text_color(*ENCRE)
        pdf.set_font("Liberation", "", 9)
        pdf.set_draw_color(*DOUX)
        with pdf.table(
            col_widths=(64, 40, 22, 24, 24),
            text_align=("LEFT", "LEFT", "LEFT", "RIGHT", "RIGHT"),
            headings_style=entete,
            borders_layout="HORIZONTAL_LINES",
            line_height=5,
            padding=1.5,
            markdown=True,
        ) as tableau:
            titres = tableau.row()
            for titre in ("Produit", "Couleurs", "Tailles", "Prix", "Pro"):
                titres.cell(titre)
            for produit in lignes:
                actives = [v for v in produit.variantes if v.est_active]
                couleurs = list(dict.fromkeys(v.couleur for v in actives if v.couleur))
                rangee = tableau.row()
                # Le nom en gras ; les astérisques éventuels du texte sont neutralisés.
                texte = "**" + produit.nom.replace("*", "") + "**"
                if produit.resume:
                    texte += "\n" + produit.resume.replace("*", "").replace("__", "_")
                if produit.personnalisable:
                    texte += "\nPersonnalisable : nom et fonction brodés"
                rangee.cell(texte)
                rangee.cell(", ".join(couleurs))
                rangee.cell(_tailles([v.taille for v in actives if v.taille]))
                if produit.vendable_en_ligne and produit.prix_public is not None:
                    rangee.cell(fcfa(produit.prix_public))
                    rangee.cell(fcfa(produit.prix_pro) if produit.prix_pro else "")
                else:
                    rangee.cell("Pharmacien partenaire", colspan=2)
        pdf.ln(4)
    return bytes(pdf.output())
