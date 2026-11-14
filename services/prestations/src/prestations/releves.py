"""Relevés du mois : ce que doit chaque structure, ce que l'on doit à chaque partenaire, la
marge entre les deux.

Une collecte compte dans le mois où son linge a été rendu. La structure paie les pièces
rendues (formule à la pièce) ou son forfait, avec les pièces au-delà du volume compris ; le
partenaire est payé pour les pièces qu'il a rendues, ou au kilo pesé au dépôt. Une pièce
manquante n'est facturée à personne : elle se règle à part, une fois retrouvée ou remboursée.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces, calendrier, operations
from prestations.etats import Formule, ModeTarif, StatutCollecte
from prestations.linge import Article, libelle
from prestations.models import Collecte, Contrat, Partenaire
from prestations.schemas import (
    CollecteReleve,
    LigneReleve,
    Releve,
    Synthese,
    SyntheseContrat,
    SynthesePartenaire,
)
from prestations.vues import contrat_vue, manquantes


def cout(collecte: Collecte) -> tuple[int, bool]:
    """Ce que coûte la collecte chez le partenaire, et si un tarif manquait pour le calculer.

    Tarif relevé au dépôt ; s'il manquait, celui du partenaire aujourd'hui."""
    if collecte.cout_kg is not None:
        if collecte.poids_kg is None:
            return 0, True
        montant = (collecte.poids_kg * collecte.cout_kg).quantize(Decimal(1), ROUND_HALF_UP)
        return int(montant), False
    partenaire = collecte.partenaire
    total, incomplet = 0, partenaire is None
    for ligne in collecte.lignes:
        rendues = ligne.quantite_rendue or 0
        prix = ligne.cout_unitaire
        if prix is None and partenaire is not None and partenaire.mode_tarif == ModeTarif.PIECE:
            prix = partenaire.tarifs.get(ligne.article)
        if prix is None:
            incomplet = incomplet or rendues > 0
        else:
            total += rendues * prix
    return total, incomplet


@dataclass
class Calcul:
    lignes: list[LigneReleve] = field(default_factory=list)
    pieces_enlevees: int = 0
    pieces_rendues: int = 0
    pieces_manquantes: int = 0
    forfait: int | None = None
    pieces_supplementaires: int = 0
    montant_supplement: int = 0
    total: int = 0
    cout: int = 0
    cout_incomplet: bool = False
    prix_manquants: bool = False


def actif_dans_le_mois(contrat: Contrat, debut: datetime, fin: datetime) -> bool:
    return contrat.debut_le < fin.date() and (
        contrat.fin_le is None or contrat.fin_le >= debut.date()
    )


def calculer(contrat: Contrat, collectes: list[Collecte], forfait_du: bool) -> Calcul:
    """Prix relevé à l'enlèvement ; s'il manquait (article absent des tarifs du contrat), celui
    du contrat aujourd'hui ; sinon la ligne est signalée « prix à fixer » et comptée à zéro."""
    calcul = Calcul()
    a_la_piece = contrat.formule == Formule.PIECE
    groupes: dict[tuple[str, str, int | None], LigneReleve] = {}
    for collecte in collectes:
        for ligne in collecte.lignes:
            prix = ligne.prix_unitaire
            if prix is None and a_la_piece:
                prix = contrat.tarifs.get(ligne.article)
            if a_la_piece and prix is None:
                calcul.prix_manquants = True
            groupe = groupes.setdefault(
                (ligne.article, ligne.precision, prix),
                LigneReleve(
                    article=Article(ligne.article),
                    libelle=libelle(Article(ligne.article), ligne.precision),
                    prix_unitaire=prix,
                    enlevees=0,
                    rendues=0,
                    manquantes=0,
                    montant=0,
                ),
            )
            rendues = ligne.quantite_rendue or 0
            groupe.enlevees += ligne.quantite_enlevee
            groupe.rendues += rendues
            groupe.manquantes += max(0, ligne.quantite_enlevee - rendues)
            groupe.montant += rendues * (prix or 0)
        montant, incomplet = cout(collecte)
        calcul.cout += montant
        calcul.cout_incomplet = calcul.cout_incomplet or incomplet
    ordre = list(Article)
    calcul.lignes = sorted(
        groupes.values(),
        key=lambda g: (ordre.index(g.article), g.libelle, g.prix_unitaire or 0),
    )
    calcul.pieces_enlevees = sum(g.enlevees for g in calcul.lignes)
    calcul.pieces_rendues = sum(g.rendues for g in calcul.lignes)
    calcul.pieces_manquantes = sum(manquantes(c.lignes) for c in collectes)
    if contrat.formule == Formule.FORFAIT:
        calcul.forfait = (contrat.forfait_mensuel or 0) if forfait_du else 0
        if contrat.pieces_incluses is not None:
            calcul.pieces_supplementaires = max(0, calcul.pieces_rendues - contrat.pieces_incluses)
            calcul.montant_supplement = calcul.pieces_supplementaires * (
                contrat.prix_piece_supplementaire or 0
            )
        calcul.total = calcul.forfait + calcul.montant_supplement
    else:
        calcul.total = sum(g.montant for g in calcul.lignes)
    return calcul


async def _rendues(
    session: AsyncSession, debut: datetime, fin: datetime, contrat_id: UUID | None = None
) -> list[Collecte]:
    requete = acces.requete_collectes().where(
        Collecte.statut == StatutCollecte.RENDUE,
        Collecte.rendue_le >= debut,
        Collecte.rendue_le < fin,
    )
    if contrat_id is not None:
        requete = requete.where(Collecte.contrat_id == contrat_id)
    return list(await session.scalars(requete.order_by(Collecte.rendue_le, Collecte.numero)))


async def releve(session: AsyncSession, contrat: Contrat, mois: str) -> Releve:
    debut, fin = calendrier.bornes_du_mois(mois)
    collectes = await _rendues(session, debut, fin, contrat.id)
    calcul = calculer(contrat, collectes, actif_dans_le_mois(contrat, debut, fin))
    return Releve(
        mois=mois,
        libelle_mois=calendrier.mois_en_toutes_lettres(mois),
        contrat=contrat_vue(contrat),
        collectes=[
            CollecteReleve(
                reference=c.reference,
                enlevee_le=c.prevue_le,
                rendue_le=c.rendue_le.date() if c.rendue_le else c.prevue_le,
                pieces_enlevees=sum(ligne.quantite_enlevee for ligne in c.lignes),
                pieces_rendues=sum(ligne.quantite_rendue or 0 for ligne in c.lignes),
            )
            for c in collectes
        ],
        lignes=calcul.lignes,
        pieces_enlevees=calcul.pieces_enlevees,
        pieces_rendues=calcul.pieces_rendues,
        pieces_manquantes=calcul.pieces_manquantes,
        forfait=calcul.forfait,
        pieces_supplementaires=calcul.pieces_supplementaires,
        montant_supplement=calcul.montant_supplement,
        total=calcul.total,
        cout_partenaires=calcul.cout,
        cout_incomplet=calcul.cout_incomplet,
        prix_manquants=calcul.prix_manquants,
    )


async def synthese(session: AsyncSession, mois: str) -> Synthese:
    debut, fin = calendrier.bornes_du_mois(mois)
    collectes = await _rendues(session, debut, fin)
    par_contrat: dict[UUID, list[Collecte]] = defaultdict(list)
    for collecte in collectes:
        par_contrat[collecte.contrat_id].append(collecte)
    # Les contrats à forfait comptent même sans linge rendu ce mois-ci.
    contrats = list(
        await session.scalars(
            select(Contrat)
            .options(*acces.CHARGEMENT_CONTRAT)
            .where(
                or_(
                    Contrat.id.in_(par_contrat.keys()),
                    (Contrat.formule == Formule.FORFAIT)
                    & (Contrat.debut_le < fin.date())
                    & (Contrat.fin_le.is_(None) | (Contrat.fin_le >= debut.date())),
                )
            )
            .order_by(Contrat.structure)
        )
    )
    lignes_contrats: list[SyntheseContrat] = []
    for contrat in contrats:
        siennes = par_contrat.get(contrat.id, [])
        calcul = calculer(contrat, siennes, actif_dans_le_mois(contrat, debut, fin))
        lignes_contrats.append(
            SyntheseContrat(
                reference=contrat.reference,
                structure=contrat.structure,
                formule=Formule(contrat.formule),
                collectes=len(siennes),
                pieces_rendues=calcul.pieces_rendues,
                pieces_manquantes=calcul.pieces_manquantes,
                chiffre=calcul.total,
                cout=calcul.cout,
                marge=calcul.total - calcul.cout,
                cout_incomplet=calcul.cout_incomplet,
                prix_manquants=calcul.prix_manquants,
            )
        )

    par_partenaire: dict[UUID, list[Collecte]] = defaultdict(list)
    for collecte in collectes:
        if collecte.partenaire_id is not None:
            par_partenaire[collecte.partenaire_id].append(collecte)
    partenaires = {
        p.id: p
        for p in await session.scalars(
            select(Partenaire).where(Partenaire.id.in_(par_partenaire.keys()))
        )
    }
    lignes_partenaires: list[SynthesePartenaire] = []
    for identifiant, siennes in sorted(
        par_partenaire.items(), key=lambda item: partenaires[item[0]].nom
    ):
        couts = [cout(c) for c in siennes]
        lignes_partenaires.append(
            SynthesePartenaire(
                id=identifiant,
                nom=partenaires[identifiant].nom,
                mode_tarif=ModeTarif(partenaires[identifiant].mode_tarif),
                collectes=len(siennes),
                pieces=sum(ligne.quantite_rendue or 0 for c in siennes for ligne in c.lignes),
                poids_kg=float(sum((c.poids_kg or Decimal(0)) for c in siennes)),
                cout=sum(montant for montant, _ in couts),
                cout_incomplet=any(incomplet for _, incomplet in couts),
            )
        )

    chiffre = sum(c.chiffre for c in lignes_contrats)
    total_cout = sum(c.cout for c in lignes_contrats)
    return Synthese(
        mois=mois,
        libelle_mois=calendrier.mois_en_toutes_lettres(mois),
        contrats=lignes_contrats,
        partenaires=lignes_partenaires,
        chiffre=chiffre,
        cout=total_cout,
        marge=chiffre - total_cout,
        pieces_rendues=sum(c.pieces_rendues for c in lignes_contrats),
        pieces_manquantes=sum(c.pieces_manquantes for c in lignes_contrats),
        en_cours=await operations.en_cours(session),
    )
