"""Processus d'envoi des SMS : lit la boîte d'envoi et expédie, avec reprises espacées.

    uv run python -m boutique.envoi

Plusieurs processus peuvent tourner ensemble : chaque lot est verrouillé (SKIP LOCKED).
"""

import asyncio
import base64
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from boutique.config import ParametresBoutique
from boutique.models import Notification
from socle.db import creer_moteur, fabrique_sessions
from socle.journaux import configurer_journaux

journal = logging.getLogger("boutique.envoi")
TENTATIVES_MAX = 5


class Expediteur(Protocol):
    async def envoyer(self, destinataire: str, message: str) -> str | None:
        """Envoie le SMS ; renvoie l'identifiant du fournisseur. Lève une exception en cas
        d'échec (le message sera repris plus tard)."""
        ...


class ExpediteurJournal:
    """Aucun envoi réel : pour les essais et la préproduction."""

    async def envoyer(self, destinataire: str, message: str) -> str | None:
        journal.info("SMS simulé", extra={"destinataire": destinataire[:-4] + "****"})
        return None


class ExpediteurOrange:
    """API SMS d'Orange (Orange Developer). Jeton OAuth2 mis en cache jusqu'à expiration.

    À valider avec le contrat : pays du compte, numéro expéditeur et nom d'expéditeur.
    """

    JETON = "https://api.orange.com/oauth/v3/token"
    ENVOI = "https://api.orange.com/smsmessaging/v1/outbound/{expediteur}/requests"

    def __init__(self, parametres: ParametresBoutique, client: httpx.AsyncClient) -> None:
        self.parametres = parametres
        self.client = client
        self._jeton: str | None = None
        self._expire = 0.0

    async def _jeton_valide(self) -> str:
        if self._jeton and time.monotonic() < self._expire:
            return self._jeton
        identifiants = (
            f"{self.parametres.orange_client_id}:"
            f"{self.parametres.orange_client_secret.get_secret_value()}"
        )
        reponse = await self.client.post(
            self.JETON,
            headers={"Authorization": "Basic " + base64.b64encode(identifiants.encode()).decode()},
            data={"grant_type": "client_credentials"},
        )
        reponse.raise_for_status()
        donnees = reponse.json()
        self._jeton = str(donnees["access_token"])
        self._expire = time.monotonic() + int(donnees.get("expires_in", 3600)) - 60
        return self._jeton

    async def envoyer(self, destinataire: str, message: str) -> str | None:
        expediteur = f"tel:{self.parametres.sms_expediteur}"
        demande: dict[str, object] = {
            "address": f"tel:{destinataire}",
            "senderAddress": expediteur,
            "outboundSMSTextMessage": {"message": message},
        }
        if self.parametres.sms_nom_expediteur:
            demande["senderName"] = self.parametres.sms_nom_expediteur
        reponse = await self.client.post(
            self.ENVOI.format(expediteur=quote(expediteur, safe="")),
            headers={"Authorization": f"Bearer {await self._jeton_valide()}"},
            json={"outboundSMSMessageRequest": demande},
        )
        if reponse.status_code == 401:
            self._jeton = None  # jeton révoqué : on en redemandera un au prochain essai
        reponse.raise_for_status()
        ressource = reponse.json().get("outboundSMSMessageRequest", {}).get("resourceURL")
        return str(ressource) if ressource else None


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


def expediteur_pour(parametres: ParametresBoutique, client: httpx.AsyncClient) -> Expediteur:
    if parametres.sms_fournisseur == "orange":
        return ExpediteurOrange(parametres, client)
    return ExpediteurJournal()


async def boucle(parametres: ParametresBoutique, pause: float = 5.0) -> None:
    moteur = creer_moteur(parametres.database_url, pool=False)
    sessions = fabrique_sessions(moteur)
    async with httpx.AsyncClient(timeout=20) as client:
        expediteur = expediteur_pour(parametres, client)
        journal.info("Envoi des SMS démarré", extra={"fournisseur": parametres.sms_fournisseur})
        while True:
            try:
                traites = await tour(sessions, expediteur)
            except Exception:  # noqa: BLE001 - base indisponible : on réessaie
                journal.exception("Tour d'envoi interrompu")
                traites = 0
            if not traites:
                await asyncio.sleep(pause)


if __name__ == "__main__":
    configurer_journaux("boutique-envoi")
    asyncio.run(boucle(ParametresBoutique()))
