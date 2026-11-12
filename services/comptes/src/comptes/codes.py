"""Codes à usage unique envoyés par SMS : création (avec limite par heure), vérification
(essais comptés, code brûlé après le dernier), envoi en tâche de fond."""

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from comptes.config import ParametresComptes
from comptes.models import CodeVerification, Utilisateur
from socle.ids import uuid7
from socle.sms import Expediteur, expediteur_pour

journal = logging.getLogger("comptes.codes")


def _empreinte(code_id: object, code: str) -> str:
    return hashlib.sha256(f"{code_id}:{code}".encode()).hexdigest()


async def creer(
    session: AsyncSession, utilisateur: Utilisateur, objet: str, parametres: ParametresComptes
) -> str | None:
    """Nouveau code (les précédents ne valent plus), ou rien si la limite horaire est atteinte."""
    maintenant = datetime.now(UTC)
    recents = await session.scalar(
        select(func.count())
        .select_from(CodeVerification)
        .where(
            CodeVerification.utilisateur_id == utilisateur.id,
            CodeVerification.objet == objet,
            CodeVerification.cree_le >= maintenant - timedelta(hours=1),
        )
    )
    if (recents or 0) >= parametres.codes_par_heure:
        return None
    await session.execute(
        update(CodeVerification)
        .where(
            CodeVerification.utilisateur_id == utilisateur.id,
            CodeVerification.objet == objet,
            CodeVerification.utilise_le.is_(None),
        )
        .values(utilise_le=maintenant)
    )
    code = f"{secrets.randbelow(10**6):06d}"
    identifiant = uuid7()
    session.add(
        CodeVerification(
            id=identifiant,
            utilisateur_id=utilisateur.id,
            objet=objet,
            empreinte=_empreinte(identifiant, code),
            expire_le=maintenant + timedelta(minutes=parametres.code_validite_minutes),
        )
    )
    return code


async def verifier(
    session: AsyncSession,
    utilisateur: Utilisateur,
    objet: str,
    code: str,
    parametres: ParametresComptes,
) -> bool:
    """Vrai si le code est le bon : il est alors consommé. Chaque erreur compte un essai."""
    maintenant = datetime.now(UTC)
    actif = await session.scalar(
        select(CodeVerification)
        .where(
            CodeVerification.utilisateur_id == utilisateur.id,
            CodeVerification.objet == objet,
            CodeVerification.utilise_le.is_(None),
            CodeVerification.expire_le > maintenant,
        )
        .order_by(CodeVerification.cree_le.desc())
        .limit(1)
        .with_for_update()
    )
    if actif is None:
        return False
    if hmac.compare_digest(actif.empreinte, _empreinte(actif.id, code)):
        actif.utilise_le = maintenant
        return True
    actif.essais += 1
    if actif.essais >= parametres.code_essais_max:
        actif.utilise_le = maintenant  # trop d'essais : il faut demander un nouveau code
    return False


async def envoyer_sms(app: FastAPI, destinataire: str, texte: str) -> None:
    """Tâche de fond, après la réponse : la durée de l'envoi ne révèle pas qu'un compte existe."""
    expediteur: Expediteur | None = getattr(app.state, "expediteur_sms", None)
    try:
        if expediteur is not None:
            await expediteur.envoyer(destinataire, texte)
            return
        async with httpx.AsyncClient(timeout=20) as client:
            await expediteur_pour(app.state.parametres, client).envoyer(destinataire, texte)
    except Exception:  # noqa: BLE001 - la personne pourra redemander un code
        journal.exception("Échec de l'envoi d'un code par SMS")
