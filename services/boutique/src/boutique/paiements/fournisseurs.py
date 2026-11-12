"""Agrégateurs de paiement. Le statut d'un paiement est toujours lu auprès de l'agrégateur,
avec notre clé : une notification reçue n'est qu'un signal pour aller vérifier."""

from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

from boutique.config import ParametresBoutique
from boutique.models import TransactionPaiement

EN_TETES = {"User-Agent": "Bibou/1.0 (+https://github.com/djibzy/sante)"}


class ErreurFournisseur(Exception):
    """L'agrégateur a refusé la demande ou ne répond pas."""


@dataclass(frozen=True)
class Verification:
    statut: Literal["acceptee", "refusee", "en_attente"]
    montant: int | None = None
    devise: str | None = None
    operateur: str | None = None
    reference_operateur: str | None = None


class Fournisseur(Protocol):
    nom: str

    async def initier(
        self,
        *,
        transaction_id: str,
        montant: int,
        description: str,
        reference: str,
        url_retour: str,
        url_notification: str,
    ) -> str:
        """Ouvre le paiement et renvoie l'adresse de la page de paiement."""
        ...

    async def verifier(self, transaction: TransactionPaiement) -> Verification:
        """Relit le statut du paiement auprès de l'agrégateur."""
        ...


class CinetPay:
    """API Checkout v2 de CinetPay (Orange Money et Moov Money au Mali, en francs CFA)."""

    nom = "cinetpay"
    INITIALISATION = "https://api-checkout.cinetpay.com/v2/payment"
    VERIFICATION = "https://api-checkout.cinetpay.com/v2/payment/check"

    def __init__(self, parametres: ParametresBoutique, client: httpx.AsyncClient) -> None:
        self.parametres = parametres
        self.client = client

    def _identifiants(self) -> dict[str, str]:
        return {
            "apikey": self.parametres.cinetpay_apikey.get_secret_value(),
            "site_id": self.parametres.cinetpay_site_id,
        }

    async def _poster(self, adresse: str, corps: dict[str, object]) -> dict[str, object]:
        try:
            reponse = await self.client.post(adresse, json=corps, headers=EN_TETES)
            donnees: dict[str, object] = reponse.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ErreurFournisseur(f"{type(exc).__name__}: {exc}") from exc
        return donnees

    async def initier(
        self,
        *,
        transaction_id: str,
        montant: int,
        description: str,
        reference: str,
        url_retour: str,
        url_notification: str,
    ) -> str:
        # Aucune donnée personnelle n'est transmise : l'opérateur demande lui-même le numéro.
        donnees = await self._poster(
            self.INITIALISATION,
            {
                **self._identifiants(),
                "transaction_id": transaction_id,
                "amount": montant,
                "currency": "XOF",
                "description": description,
                "notify_url": url_notification,
                "return_url": url_retour,
                "channels": self.parametres.cinetpay_canaux,
                "lang": "fr",
                "metadata": reference,
            },
        )
        page = donnees.get("data")
        if str(donnees.get("code")) != "201" or not isinstance(page, dict):
            raise ErreurFournisseur(f"{donnees.get('code')} {donnees.get('message')}")
        return str(page["payment_url"])

    async def verifier(self, transaction: TransactionPaiement) -> Verification:
        donnees = await self._poster(
            self.VERIFICATION,
            {**self._identifiants(), "transaction_id": transaction.transaction_id},
        )
        detail = donnees.get("data")
        detail = detail if isinstance(detail, dict) else {}
        code, etat = str(donnees.get("code")), detail.get("status")
        if code == "00" and etat == "ACCEPTED":
            statut: Literal["acceptee", "refusee", "en_attente"] = "acceptee"
        elif etat == "REFUSED" or code == "627":  # 627 : transaction annulée par le client
            statut = "refusee"
        else:  # en attente de validation sur le téléphone du client
            statut = "en_attente"
        montant = detail.get("amount")
        return Verification(
            statut=statut,
            montant=int(float(str(montant))) if montant not in (None, "") else None,
            devise=str(detail["currency"]) if detail.get("currency") else None,
            operateur=str(detail["payment_method"]) if detail.get("payment_method") else None,
            reference_operateur=str(detail["operator_id"]) if detail.get("operator_id") else None,
        )


class Simulation:
    """Pour les essais : pas de page de paiement, retour immédiat au suivi de la commande, et
    tout paiement est accepté. Jamais disponible en production."""

    nom = "simulation"

    async def initier(
        self,
        *,
        transaction_id: str,
        montant: int,
        description: str,
        reference: str,
        url_retour: str,
        url_notification: str,
    ) -> str:
        return f"/suivi/{reference}?paiement=retour"

    async def verifier(self, transaction: TransactionPaiement) -> Verification:
        return Verification(
            statut="acceptee",
            montant=transaction.montant,
            devise="XOF",
            operateur="OM",
            reference_operateur=f"SIMULATION-{transaction.transaction_id}",
        )


def configuration_incomplete(parametres: ParametresBoutique) -> str | None:
    """Ce qui manque pour ouvrir le paiement en ligne, ou rien s'il est prêt (ou éteint)."""
    if parametres.paiement_mobile == "simulation" and parametres.en_production:
        return "la simulation est interdite en production"
    if parametres.paiement_mobile != "cinetpay":
        return None
    requis = {
        "BOUTIQUE_CINETPAY_APIKEY": parametres.cinetpay_apikey.get_secret_value(),
        "BOUTIQUE_CINETPAY_SITE_ID": parametres.cinetpay_site_id,
        # Adresse de notification et de retour : CinetPay refuse les adresses locales.
        "BOUTIQUE_URL_PUBLIQUE": parametres.url_publique,
    }
    manquants = [nom for nom, valeur in requis.items() if not valeur]
    return ("à renseigner : " + ", ".join(manquants)) if manquants else None


def est_ouvert(parametres: ParametresBoutique) -> bool:
    return parametres.paiement_mobile != "aucun" and configuration_incomplete(parametres) is None


def fournisseur(parametres: ParametresBoutique, client: httpx.AsyncClient) -> Fournisseur | None:
    """L'agrégateur configuré, ou rien quand le paiement en ligne est éteint ou incomplet."""
    if not est_ouvert(parametres):
        return None
    if parametres.paiement_mobile == "cinetpay":
        return CinetPay(parametres, client)
    if parametres.paiement_mobile == "simulation":
        return Simulation()
    return None
