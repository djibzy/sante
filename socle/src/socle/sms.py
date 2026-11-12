"""Envoi de SMS, commun aux services : API SMS d'Orange, ou simple journal pour les essais."""

import base64
import logging
import time
from typing import Protocol
from urllib.parse import quote

import httpx

from socle.settings import ParametresSms

journal = logging.getLogger("socle.sms")


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

    def __init__(self, parametres: ParametresSms, client: httpx.AsyncClient) -> None:
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


def expediteur_pour(parametres: ParametresSms, client: httpx.AsyncClient) -> Expediteur:
    if parametres.sms_fournisseur == "orange":
        return ExpediteurOrange(parametres, client)
    return ExpediteurJournal()
