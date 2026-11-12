"""Boîte d'envoi : la notification est écrite dans la même transaction que l'événement qui
la déclenche ; le processus d'envoi la lit ensuite (aucun SMS perdu ni envoyé à tort)."""

from sqlalchemy.ext.asyncio import AsyncSession

from boutique.commandes.cycle import Statut
from boutique.models import Commande, Notification
from boutique.notifications import messages


def deposer(
    session: AsyncSession, commande: Commande, texte: str | None, destinataire: str | None = None
) -> None:
    """SMS au client de la commande, ou à un autre numéro (équipe)."""
    if texte:
        session.add(
            Notification(
                commande_id=commande.id,
                canal="sms",
                destinataire=destinataire or commande.telephone,
                message=texte,
                etat="a_envoyer",
            )
        )


def prevenir_equipe(
    session: AsyncSession, commande: Commande, numeros: list[str], zone: str | None
) -> None:
    texte = messages.pour_l_equipe(commande, zone)
    for numero in numeros:
        deposer(session, commande, texte, numero)


def apres_creation(session: AsyncSession, commande: Commande, lien: str | None) -> None:
    deposer(session, commande, messages.creation(commande, lien))


def apres_changement(session: AsyncSession, commande: Commande, statut: Statut) -> None:
    deposer(session, commande, messages.changement(commande, statut))
