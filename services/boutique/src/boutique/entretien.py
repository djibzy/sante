"""Durées de conservation (loi n° 2013-015 sur les données personnelles) : ce qui n'a plus à
être gardé est effacé ou anonymisé, chaque nuit, par le processus d'envoi.

- SMS : effacés 3 ans après leur création.
- Messages du fil d'une commande : effacés 3 ans après la fin de l'affaire (commande remise,
  annulée, devis refusé), images comprises. Les propositions acceptées, qui font foi, restent
  avec la commande jusqu'à son anonymisation.
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
from pathlib import Path
from uuid import UUID

from sqlalchemy import ColumnElement, CursorResult, and_, delete, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from boutique.commandes.cycle import Statut
from boutique.messagerie import images
from boutique.messagerie.etats import EtatProposition
from boutique.models import (
    Avis,
    Commande,
    EvenementCommande,
    Facture,
    JournalAudit,
    LigneCommande,
    Message,
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
# L'affaire est finie : plus rien ne se passera sur cette commande.
CLOSES = (Statut.LIVREE, Statut.ANNULEE, Statut.DEVIS_REFUSE)
ANS = timedelta(days=365)


@dataclass
class Bilan:
    sms: int = 0
    commandes: int = 0
    messages: int = 0
    avis: int = 0
    tentatives: int = 0
    adresses_ip: int = 0


def _nombre(resultat: object) -> int:
    return resultat.rowcount if isinstance(resultat, CursorResult) else 0


async def effacer_messages(
    session: AsyncSession, commandes: list[UUID], *, garder_les_accords: bool
) -> tuple[int, list[str]]:
    """Efface les messages de ces commandes. Renvoie leur nombre et les images à supprimer du
    disque une fois la transaction validée (voir supprimer_images)."""
    if not commandes:
        return 0, []
    condition: ColumnElement[bool] = Message.commande_id.in_(commandes)
    if garder_les_accords:
        condition = and_(
            condition, or_(Message.etat.is_(None), Message.etat != EtatProposition.ACCEPTEE)
        )
    fichiers = [
        nom
        for nom in await session.scalars(
            select(Message.image).where(condition, Message.image.is_not(None))
        )
        if nom
    ]
    efface = await session.execute(delete(Message).where(condition))
    return _nombre(efface), fichiers


def supprimer_images(dossier_medias: Path | None, fichiers: list[str]) -> None:
    if dossier_medias is not None:
        for nom in fichiers:
            images.supprimer(dossier_medias, nom)


async def anonymiser(session: AsyncSession, commandes: list[UUID]) -> list[str]:
    """Retire des commandes tout ce qui désigne la personne ; montants et articles restent.
    Renvoie les images de leurs messages, à supprimer du disque après validation."""
    if not commandes:
        return []
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
    _, fichiers = await effacer_messages(session, commandes, garder_les_accords=False)
    return fichiers


async def _anonymiser_commandes(
    session: AsyncSession, maintenant: datetime
) -> tuple[int, list[str]]:
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
    return len(cibles), await anonymiser(session, cibles)


async def _effacer_vieux_messages(
    session: AsyncSession, maintenant: datetime
) -> tuple[int, list[str]]:
    closes = list(
        await session.scalars(
            select(Commande.id).where(
                Commande.statut.in_(CLOSES),
                Commande.statut_le < maintenant - 3 * ANS,
                exists().where(Message.commande_id == Commande.id),
            )
        )
    )
    return await effacer_messages(session, closes, garder_les_accords=True)


async def entretenir(
    sessions: async_sessionmaker[AsyncSession],
    maintenant: datetime | None = None,
    dossier_medias: Path | None = None,
) -> Bilan:
    maintenant = maintenant or datetime.now(UTC)
    bilan = Bilan()
    fichiers: list[str] = []
    async with sessions() as session:
        bilan.sms = _nombre(
            await session.execute(
                delete(Notification).where(Notification.cree_le < maintenant - 3 * ANS)
            )
        )
        bilan.commandes, fichiers = await _anonymiser_commandes(session, maintenant)
        bilan.messages, vieux = await _effacer_vieux_messages(session, maintenant)
        fichiers += vieux
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
    supprimer_images(dossier_medias, fichiers)
    return bilan
