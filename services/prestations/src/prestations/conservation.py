"""Durées de conservation (loi n° 2013-015 sur les données personnelles), appliquées chaque nuit
par le processus d'envoi :

- demandes classées sans suite : effacées un an après leur dernière modification ;
- SMS : effacés un an après leur création (le bon de collecte, lui, reste en base) ;
- adresses IP du journal d'audit : effacées après un an ; l'action reste tracée.

Contrats et collectes restent : ils fondent les relevés et la facturation (10 ans, OHADA).
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import CursorResult, delete, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from prestations import calendrier
from prestations.etats import StatutDemande
from prestations.models import Demande, JournalAudit, Notification

UN_AN = timedelta(days=365)


@dataclass
class Bilan:
    demandes: int = 0
    sms: int = 0
    adresses_ip: int = 0


def _lignes(resultat: object) -> int:
    return resultat.rowcount if isinstance(resultat, CursorResult) else 0


async def conserver(sessions: async_sessionmaker[AsyncSession]) -> Bilan:
    limite = calendrier.maintenant() - UN_AN
    async with sessions() as session:
        bilan = Bilan(
            demandes=_lignes(
                await session.execute(
                    delete(Demande).where(
                        Demande.statut == StatutDemande.SANS_SUITE, Demande.modifie_le < limite
                    )
                )
            ),
            sms=_lignes(
                await session.execute(delete(Notification).where(Notification.cree_le < limite))
            ),
            adresses_ip=_lignes(
                await session.execute(
                    update(JournalAudit)
                    .where(JournalAudit.cree_le < limite, JournalAudit.adresse_ip.is_not(None))
                    .values(adresse_ip=None)
                )
            ),
        )
        await session.commit()
    return bilan
