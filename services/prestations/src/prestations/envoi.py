"""Processus d'envoi des SMS : lit la boîte d'envoi et expédie, avec reprises espacées ; applique
chaque jour les durées de conservation (prestations.conservation).

    uv run python -m prestations.envoi

Plusieurs processus peuvent tourner ensemble : chaque lot est verrouillé (SKIP LOCKED).
"""

import asyncio
import logging
import time
from datetime import timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from prestations import calendrier
from prestations.config import ParametresPrestations
from prestations.conservation import conserver
from prestations.models import Notification
from socle.db import creer_moteur, fabrique_sessions
from socle.journaux import configurer_journaux
from socle.sms import Expediteur, expediteur_pour

journal = logging.getLogger("prestations.envoi")
TENTATIVES_MAX = 5
CONSERVATION_SECONDES = 86_400.0


async def tour(
    sessions: async_sessionmaker[AsyncSession], expediteur: Expediteur, lot: int = 20
) -> int:
    """Envoie un lot de SMS dus ; renvoie le nombre traité."""
    maintenant = calendrier.maintenant()
    async with sessions() as session:
        notifications = list(
            await session.scalars(
                select(Notification)
                .where(Notification.etat == "a_envoyer", Notification.prochain_essai <= maintenant)
                .order_by(Notification.cree_le)
                .limit(lot)
                .with_for_update(skip_locked=True)
            )
        )
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
                notification.envoyee_le = calendrier.maintenant()
                notification.identifiant_fournisseur = identifiant
        await session.commit()
    return len(notifications)


async def boucle(parametres: ParametresPrestations, pause: float = 5.0) -> None:
    moteur = creer_moteur(parametres.database_url, pool=False)
    sessions = fabrique_sessions(moteur)
    async with httpx.AsyncClient(timeout=20) as client:
        expediteur = expediteur_pour(parametres, client)
        prochaine_conservation = time.monotonic()
        journal.info("Envoi des SMS démarré", extra={"fournisseur": parametres.sms_fournisseur})
        while True:
            try:
                traites = await tour(sessions, expediteur)
            except Exception:  # noqa: BLE001 - base indisponible : on réessaie
                journal.exception("Tour d'envoi interrompu")
                traites = 0
            if time.monotonic() >= prochaine_conservation:
                prochaine_conservation = time.monotonic() + CONSERVATION_SECONDES
                try:
                    bilan = await conserver(sessions)
                    journal.info("Durées de conservation appliquées", extra=vars(bilan))
                except Exception:  # noqa: BLE001 - base indisponible : demain
                    journal.exception("Conservation des données interrompue")
            if not traites:
                await asyncio.sleep(pause)


if __name__ == "__main__":
    configurer_journaux("prestations-envoi")
    asyncio.run(boucle(ParametresPrestations()))
