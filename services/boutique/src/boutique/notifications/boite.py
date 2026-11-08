"""Boîte d'envoi : la notification est écrite dans la même transaction que l'événement qui
la déclenche ; le processus d'envoi la lit ensuite (aucun SMS perdu ni envoyé à tort)."""

from sqlalchemy.ext.asyncio import AsyncSession

from boutique.commandes.cycle import Statut
from boutique.models import Commande, Notification
from boutique.notifications import messages


def deposer(session: AsyncSession, commande: Commande, texte: str | None) -> None:
    if texte:
        session.add(
            Notification(
                commande_id=commande.id,
                canal="sms",
                destinataire=commande.telephone,
                message=texte,
                etat="a_envoyer",
            )
        )


def apres_creation(session: AsyncSession, commande: Commande, lien: str | None) -> None:
    deposer(session, commande, messages.creation(commande, lien))


def apres_changement(session: AsyncSession, commande: Commande, statut: Statut) -> None:
    deposer(session, commande, messages.changement(commande, statut))
