"""Processus d'envoi des SMS : lit la boîte d'envoi et expédie, avec reprises espacées. Il
relit aussi, toutes les 5 minutes, les paiements en ligne restés sans réponse, prépare chaque
heure les rappels (acompte attendu, devis bientôt expiré : boutique.relances), et applique
chaque jour les durées de conservation des données (boutique.entretien).

    uv run python -m boutique.envoi

Plusieurs processus peuvent tourner ensemble : chaque lot est verrouillé (SKIP LOCKED).
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from boutique.config import ParametresBoutique
from boutique.entretien import entretenir
from boutique.models import Notification
from boutique.paiements import fournisseurs
from boutique.paiements.service import rapprocher
from boutique.relances import relancer
from socle.db import creer_moteur, fabrique_sessions
from socle.journaux import configurer_journaux
from socle.sms import Expediteur, ExpediteurJournal, ExpediteurOrange, expediteur_pour

__all__ = ["Expediteur", "ExpediteurJournal", "ExpediteurOrange", "boucle", "tour"]

journal = logging.getLogger("boutique.envoi")
TENTATIVES_MAX = 5
RAPPROCHEMENT_SECONDES = 300.0
RELANCES_SECONDES = 3_600.0
ENTRETIEN_SECONDES = 86_400.0


async def tour(
    sessions: async_sessionmaker[AsyncSession], expediteur: Expediteur, lot: int = 20
) -> int:
    """Envoie un lot de notifications dues ; renvoie le nombre traité."""
    maintenant = datetime.now(UTC)
    async with sessions() as session:
        requete = (
            select(Notification)
            .where(Notification.etat == "a_envoyer", Notification.prochain_essai <= maintenant)
            .order_by(Notification.cree_le)
            .limit(lot)
            .with_for_update(skip_locked=True)
        )
        notifications = list(await session.scalars(requete))
        for notification in notifications:
            try:
                identifiant = await expediteur.envoyer(
                    notification.destinataire, notification.message
                )
            except Exception as exc:  # noqa: BLE001 - toute erreur d'envoi se reprend plus tard
                notification.tentatives += 1
                notification.derniere_erreur = f"{type(exc).__name__}: {exc}"[:500]
                if notification.tentatives >= TENTATIVES_MAX:
                    notification.etat = "echec"
                else:
                    attente = timedelta(minutes=2**notification.tentatives)
                    notification.prochain_essai = maintenant + attente
                journal.warning("Échec d'envoi d'un SMS", extra={"id": str(notification.id)})
            else:
                notification.etat = "envoyee"
                notification.envoyee_le = datetime.now(UTC)
                notification.identifiant_fournisseur = identifiant
        await session.commit()
    return len(notifications)


async def boucle(parametres: ParametresBoutique, pause: float = 5.0) -> None:
    moteur = creer_moteur(parametres.database_url, pool=False)
    sessions = fabrique_sessions(moteur)
    async with httpx.AsyncClient(timeout=20) as client:
        expediteur = expediteur_pour(parametres, client)
        agregateur = fournisseurs.fournisseur(parametres, client)
        prochain_rapprochement = prochain_relances = prochain_entretien = time.monotonic()
        journal.info("Envoi des SMS démarré", extra={"fournisseur": parametres.sms_fournisseur})
        while True:
            try:
                traites = await tour(sessions, expediteur)
            except Exception:  # noqa: BLE001 - base indisponible : on réessaie
                journal.exception("Tour d'envoi interrompu")
                traites = 0
            if agregateur is not None and time.monotonic() >= prochain_rapprochement:
                prochain_rapprochement = time.monotonic() + RAPPROCHEMENT_SECONDES
                try:
                    await rapprocher(sessions, agregateur)
                except Exception:  # noqa: BLE001 - agrégateur ou base indisponible
                    journal.exception("Rapprochement des paiements interrompu")
            if time.monotonic() >= prochain_relances:
                prochain_relances = time.monotonic() + RELANCES_SECONDES
                try:
                    rappels = await relancer(sessions, parametres)
                    if rappels.acomptes or rappels.devis:
                        journal.info("Rappels envoyés", extra=vars(rappels))
                except Exception:  # noqa: BLE001 - base indisponible : dans une heure
                    journal.exception("Rappels interrompus")
            if time.monotonic() >= prochain_entretien:
                prochain_entretien = time.monotonic() + ENTRETIEN_SECONDES
                try:
                    bilan = await entretenir(sessions)
                    journal.info("Durées de conservation appliquées", extra=vars(bilan))
                except Exception:  # noqa: BLE001 - base indisponible : demain
                    journal.exception("Entretien des données interrompu")
            if not traites:
                await asyncio.sleep(pause)


if __name__ == "__main__":
    configurer_journaux("boutique-envoi")
    asyncio.run(boucle(ParametresBoutique()))
