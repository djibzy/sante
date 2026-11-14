"""Surveillance : interroge /sante de chaque service et prévient par SMS quand l'un d'eux tombe.

    python -m socle.surveillance

Variables (préfixe SURVEILLANCE_) : ADRESSES (séparées par des virgules), DESTINATAIRES (numéros
E.164), INTERVALLE (secondes), ECHECS_AVANT_ALERTE, et celles de l'envoi de SMS (SMS_FOURNISSEUR…).
Une alerte part après plusieurs échecs de suite (pas pour un raté isolé), une seule fois par
panne, puis un SMS dit quand le service est rétabli. À faire tourner idéalement hors du serveur
surveillé : sur le même serveur, une machine éteinte ne préviendrait personne.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx
from pydantic_settings import SettingsConfigDict

from socle.journaux import configurer_journaux
from socle.settings import ParametresSms
from socle.sms import Expediteur, expediteur_pour, gsm

journal = logging.getLogger("socle.surveillance")


class ParametresSurveillance(ParametresSms):
    model_config = SettingsConfigDict(env_prefix="SURVEILLANCE_", env_file=".env", extra="ignore")

    adresses: str = ""  # https://comptes.exemple.ml/sante,https://boutique.exemple.ml/sante
    destinataires: str = ""  # +22370000000,+22371000000
    intervalle: float = 60.0
    echecs_avant_alerte: int = 3
    delai: float = 10.0

    def liste(self, valeur: str) -> list[str]:
        return [v.strip() for v in valeur.split(",") if v.strip()]


@dataclass
class Etat:
    echecs: int = 0
    en_panne: bool = False
    depuis: float = 0.0


@dataclass
class Surveillant:
    destinataires: list[str]
    expediteur: Expediteur
    echecs_avant_alerte: int = 3
    etats: dict[str, Etat] = field(default_factory=dict)

    async def _prevenir(self, message: str) -> None:
        for numero in self.destinataires:
            try:
                await self.expediteur.envoyer(numero, gsm(message))
            except Exception:  # noqa: BLE001 - un SMS raté ne doit pas arrêter la surveillance
                journal.exception("SMS d'alerte non parti")

    async def noter(self, adresse: str, bon: bool, maintenant: float | None = None) -> None:
        """Enregistre le résultat d'un contrôle et envoie l'alerte ou le rétablissement."""
        instant = time.monotonic() if maintenant is None else maintenant
        etat = self.etats.setdefault(adresse, Etat())
        nom = adresse.split("//")[-1].split("/")[0]
        if bon:
            if etat.en_panne:
                minutes = max(1, round((instant - etat.depuis) / 60))
                await self._prevenir(f"Yasal Sante : {nom} fonctionne de nouveau ({minutes} min).")
            etat.echecs, etat.en_panne = 0, False
            return
        etat.echecs += 1
        if etat.echecs >= self.echecs_avant_alerte and not etat.en_panne:
            etat.en_panne, etat.depuis = True, instant
            await self._prevenir(f"Yasal Sante : {nom} ne repond plus. A verifier.")


async def controler(client: httpx.AsyncClient, adresse: str) -> bool:
    try:
        reponse = await client.get(adresse)
        return reponse.status_code == 200 and reponse.json().get("statut") == "ok"
    except (httpx.HTTPError, ValueError):
        return False


async def boucle(parametres: ParametresSurveillance) -> None:
    adresses = parametres.liste(parametres.adresses)
    destinataires = parametres.liste(parametres.destinataires)
    if not adresses or not destinataires:
        raise SystemExit("SURVEILLANCE_ADRESSES et SURVEILLANCE_DESTINATAIRES sont à renseigner")
    async with httpx.AsyncClient(timeout=parametres.delai) as client:
        surveillant = Surveillant(
            destinataires, expediteur_pour(parametres, client), parametres.echecs_avant_alerte
        )
        journal.info("Surveillance démarrée", extra={"services": len(adresses)})
        while True:
            resultats = await asyncio.gather(*(controler(client, a) for a in adresses))
            for adresse, bon in zip(adresses, resultats, strict=True):
                await surveillant.noter(adresse, bon)
            await asyncio.sleep(parametres.intervalle)


if __name__ == "__main__":
    configurer_journaux("surveillance")
    asyncio.run(boucle(ParametresSurveillance()))
