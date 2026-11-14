"""La tournée d'un jour : les structures à visiter (calendrier des contrats et collectes
ponctuelles), le linge enlevé à déposer chez les partenaires, le linge propre à rendre.

Rien n'est planifié d'avance en base : un passage du calendrier sans collecte enregistrée est
simplement « à enlever ». Changer les jours d'un contrat change donc les tournées à venir, sans
rien à supprimer.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces
from prestations.etats import StatutCollecte, StatutContrat
from prestations.linge import JOURS
from prestations.models import Collecte, Contrat
from prestations.schemas import Passage, Tournee
from prestations.vues import collecte_vue, contrat_resume


async def tournee(session: AsyncSession, jour: date) -> Tournee:
    contrats = list(
        await session.scalars(
            select(Contrat)
            .options(*acces.CHARGEMENT_CONTRAT)
            .where(
                Contrat.statut == StatutContrat.ACTIF,
                Contrat.debut_le <= jour,
                or_(Contrat.fin_le.is_(None), Contrat.fin_le >= jour),
                Contrat.jours_collecte.contains([jour.isoweekday()]),
            )
        )
    )
    du_jour = list(
        await session.scalars(
            acces.requete_collectes()
            .where(Collecte.prevue_le == jour)
            .order_by(Collecte.statut == StatutCollecte.ANNULEE, Collecte.numero)
        )
    )
    # Pour chaque contrat, la collecte qui compte : la non annulée d'abord.
    par_contrat: dict[UUID, Collecte] = {}
    for collecte in du_jour:
        par_contrat.setdefault(collecte.contrat_id, collecte)
    passages = [
        Passage(
            contrat=contrat_resume(contrat),
            collecte=collecte_vue(par_contrat[contrat.id], jour)
            if contrat.id in par_contrat
            else None,
            au_calendrier=True,
        )
        for contrat in contrats
    ]
    prevus = {contrat.id for contrat in contrats}
    passages += [
        Passage(
            contrat=contrat_resume(collecte.contrat),
            collecte=collecte_vue(collecte, jour),
            au_calendrier=False,
        )
        for contrat_id, collecte in par_contrat.items()
        if contrat_id not in prevus
    ]
    passages.sort(key=lambda p: p.contrat.structure.lower())

    a_deposer = await session.scalars(
        acces.requete_collectes()
        .where(Collecte.statut == StatutCollecte.ENLEVEE, Collecte.prevue_le <= jour)
        .order_by(Collecte.prevue_le, Collecte.numero)
    )
    a_rendre = await session.scalars(
        acces.requete_collectes()
        .where(
            Collecte.statut.in_([StatutCollecte.CHEZ_PARTENAIRE, StatutCollecte.PRETE]),
            Collecte.retour_prevu_le <= jour,
        )
        .order_by(Collecte.retour_prevu_le, Collecte.numero)
    )
    return Tournee(
        jour=jour,
        libelle_jour=f"{JOURS[jour.isoweekday() - 1].capitalize()} {jour:%d/%m/%Y}",
        passages=passages,
        a_deposer=[collecte_vue(c, jour) for c in a_deposer],
        a_rendre=[collecte_vue(c, jour) for c in a_rendre],
    )
