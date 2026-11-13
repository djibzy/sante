"""Durées de conservation (loi n° 2013-015 sur les données personnelles) : ce qui n'a plus à
être gardé est effacé ou anonymisé, chaque nuit, par le processus d'envoi.

- SMS : effacés 3 ans après leur création.
- Commandes sans suite (annulées, devis refusés ou restés sans réponse, jamais confirmées) :
  anonymisées 3 ans après leur dernière modification ; commandes facturées : 10 ans après la
  facture (obligation comptable OHADA). Montants, articles et facture restent, pour les
  comptes ; nom, téléphone, adresse, courriel, notes et textes brodés disparaissent.
- Avis refusés : effacés 30 jours après la décision (ils peuvent contenir ce qu'on a refusé
  de publier, une information médicale par exemple).
- Tentatives de paiement en ligne jamais abouties : effacées après 90 jours.
- Adresses IP du journal d'audit : effacées après un an ; l'action reste tracée.
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import CursorResult, and_, delete, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from boutique.commandes.cycle import Statut
from boutique.models import (
    Avis,
    Commande,
    EvenementCommande,
    Facture,
    JournalAudit,
    LigneCommande,
    Notification,
    TransactionPaiement,
)
from socle.audit import journaliser

ANONYME = "anonyme"
NOM_ANONYME = "Client anonymisé"
SANS_SUITE = (
    Statut.ANNULEE,
    Statut.DEVIS_REFUSE,
    Statut.DEVIS_DEMANDE,
    Statut.DEVIS_ENVOYE,
    Statut.EN_ATTENTE,
    Statut.ACOMPTE_ATTENDU,
)
ANS = timedelta(days=365)


@dataclass
class Bilan:
    sms: int = 0
    commandes: int = 0
    avis: int = 0
    tentatives: int = 0
    adresses_ip: int = 0


def _nombre(resultat: object) -> int:
    return resultat.rowcount if isinstance(resultat, CursorResult) else 0


async def anonymiser(session: AsyncSession, commandes: list[UUID]) -> None:
    """Retire des commandes tout ce qui désigne la personne ; montants et articles restent."""
    if not commandes:
        return
    await session.execute(
        update(Commande)
        .where(Commande.id.in_(commandes))
        .values(
            nom_client=NOM_ANONYME,
            telephone=ANONYME,
            email=None,
            adresse="",
            note_client="",
            client_id=None,
        )
    )
    await session.execute(
        update(LigneCommande)
        .where(LigneCommande.commande_id.in_(commandes))
        .values(personnalisation=None)
    )
    await session.execute(
        update(EvenementCommande)
        .where(EvenementCommande.commande_id.in_(commandes))
        .values(note="")
    )


async def _anonymiser_commandes(session: AsyncSession, maintenant: datetime) -> int:
    facturee = exists().where(Facture.commande_id == Commande.id)
    facture_ancienne = exists().where(
        Facture.commande_id == Commande.id, Facture.emise_le < maintenant - 10 * ANS
    )
    cibles = list(
        await session.scalars(
            select(Commande.id).where(
                Commande.telephone != ANONYME,
                or_(
                    and_(
                        Commande.statut.in_(SANS_SUITE),
                        Commande.modifie_le < maintenant - 3 * ANS,
                        ~facturee,
                    ),
                    facture_ancienne,
                ),
            )
        )
    )
    await anonymiser(session, cibles)
    return len(cibles)


async def entretenir(
    sessions: async_sessionmaker[AsyncSession], maintenant: datetime | None = None
) -> Bilan:
    maintenant = maintenant or datetime.now(UTC)
    bilan = Bilan()
    async with sessions() as session:
        bilan.sms = _nombre(
            await session.execute(
                delete(Notification).where(Notification.cree_le < maintenant - 3 * ANS)
            )
        )
        bilan.commandes = await _anonymiser_commandes(session, maintenant)
        bilan.avis = _nombre(
            await session.execute(
                delete(Avis).where(
                    Avis.statut == "refuse", Avis.modere_le < maintenant - timedelta(days=30)
                )
            )
        )
        bilan.tentatives = _nombre(
            await session.execute(
                delete(TransactionPaiement).where(
                    TransactionPaiement.statut == "initiee",
                    TransactionPaiement.cree_le < maintenant - timedelta(days=90),
                )
            )
        )
        bilan.adresses_ip = _nombre(
            await session.execute(
                update(JournalAudit)
                .where(
                    JournalAudit.cree_le < maintenant - ANS, JournalAudit.adresse_ip.is_not(None)
                )
                .values(adresse_ip=None)
            )
        )
        if any(asdict(bilan).values()):
            journaliser(
                session,
                JournalAudit,
                action="entretien.conservation",
                objet_type="boutique",
                details=asdict(bilan),
            )
        await session.commit()
    return bilan
