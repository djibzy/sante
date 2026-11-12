"""Durées de conservation du service Comptes (loi n° 2013-015) :

- codes envoyés par SMS : effacés le lendemain ;
- sessions (jetons de rafraîchissement) expirées ou fermées : effacées après 30 jours ;
- adresses IP du journal d'audit : effacées après un an, l'action reste tracée.

    uv run python -m comptes.outils entretien   (chaque nuit : service comptes-entretien)
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import CursorResult, delete, or_, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from comptes.models import CodeVerification, JetonRafraichissement, JournalAudit
from socle.audit import journaliser


@dataclass
class Bilan:
    codes: int = 0
    sessions: int = 0
    adresses_ip: int = 0


def _nombre(resultat: object) -> int:
    return resultat.rowcount if isinstance(resultat, CursorResult) else 0


async def entretenir(
    sessions: async_sessionmaker[AsyncSession], maintenant: datetime | None = None
) -> Bilan:
    maintenant = maintenant or datetime.now(UTC)
    bilan = Bilan()
    async with sessions() as session:
        bilan.codes = _nombre(
            await session.execute(
                delete(CodeVerification).where(
                    CodeVerification.cree_le < maintenant - timedelta(days=1)
                )
            )
        )
        limite = maintenant - timedelta(days=30)
        bilan.sessions = _nombre(
            await session.execute(
                delete(JetonRafraichissement).where(
                    or_(
                        JetonRafraichissement.expire_le < limite,
                        JetonRafraichissement.revoque_le < limite,
                    )
                )
            )
        )
        bilan.adresses_ip = _nombre(
            await session.execute(
                update(JournalAudit)
                .where(
                    JournalAudit.cree_le < maintenant - timedelta(days=365),
                    JournalAudit.adresse_ip.is_not(None),
                )
                .values(adresse_ip=None)
            )
        )
        if any(asdict(bilan).values()):
            journaliser(
                session,
                JournalAudit,
                action="entretien.conservation",
                objet_type="comptes",
                details=asdict(bilan),
            )
        await session.commit()
    return bilan
