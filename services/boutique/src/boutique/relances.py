"""Rappels SMS : acompte attendu depuis quelques jours (la fabrication ne démarre qu'à sa
réception), devis sans réponse qui va expirer. Un rappel par étape au plus, envoyé en
journée (heure de Bamako, GMT) ; l'équipe le voit dans l'historique de la commande.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from boutique.commandes import acompte
from boutique.commandes.cycle import Statut
from boutique.commandes.operations import evenement
from boutique.config import ParametresBoutique
from boutique.models import Commande, JournalAudit
from boutique.notifications import boite, messages
from socle.audit import journaliser

HEURES_D_ENVOI = range(9, 19)  # Bamako est à l'heure GMT toute l'année


@dataclass
class Bilan:
    acomptes: int = 0
    devis: int = 0


def _rappeler(session: AsyncSession, commande: Commande, texte: str, note: str) -> None:
    commande.relances += 1
    boite.deposer(session, commande, texte)
    evenement(commande, Statut(commande.statut), None, note, visible_client=False)
    journaliser(
        session,
        JournalAudit,
        action="commande.relance",
        objet_type="commande",
        objet_id=commande.reference,
        details={"statut": commande.statut, "relance": commande.relances},
    )


async def relancer(
    sessions: async_sessionmaker[AsyncSession],
    parametres: ParametresBoutique,
    maintenant: datetime | None = None,
) -> Bilan:
    maintenant = maintenant or datetime.now(UTC)
    bilan = Bilan()
    if maintenant.hour not in HEURES_D_ENVOI:
        return bilan
    paliers = sorted(parametres.relances_acompte_jours)
    async with sessions() as session:
        attendus = await session.scalars(
            select(Commande)
            .where(Commande.statut == Statut.ACOMPTE_ATTENDU, Commande.relances < len(paliers))
            .options(selectinload(Commande.evenements))
            .with_for_update(skip_locked=True, of=Commande)
        )
        for commande in attendus:
            palier = paliers[commande.relances]
            if commande.statut_le > maintenant - timedelta(days=palier):
                continue
            du = acompte.restant(commande)
            if du <= 0:
                continue
            _rappeler(
                session,
                commande,
                messages.rappel_acompte(commande, du),
                f"Rappel SMS de l'acompte ({commande.relances + 1})",
            )
            bilan.acomptes += 1

        limite = (maintenant + timedelta(days=parametres.relance_devis_jours)).date()
        devis = await session.scalars(
            select(Commande)
            .where(
                Commande.statut == Statut.DEVIS_ENVOYE,
                Commande.relances == 0,
                Commande.devis_valable_jusqu_au.is_not(None),
                Commande.devis_valable_jusqu_au <= limite,
                Commande.devis_valable_jusqu_au >= maintenant.date(),
            )
            .options(selectinload(Commande.evenements))
            .with_for_update(skip_locked=True, of=Commande)
        )
        for commande in devis:
            _rappeler(
                session,
                commande,
                messages.rappel_devis(commande),
                "Rappel SMS : devis bientôt expiré",
            )
            bilan.devis += 1
        await session.commit()
    return bilan
