"""Le fil d'un contrat : messages entre la structure et l'équipe, gardés avec leur date.

La structure y accède par la clé de son lien de suivi (envoyé par SMS, seule l'empreinte est
gardée). Un message n'est jamais modifié : l'équipe peut le retirer, avec un motif journalisé,
et son texte est alors effacé. Aucune donnée de santé : l'équipe retire ce qui en contiendrait.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces, calendrier, notifications
from prestations.config import ParametresPrestations
from prestations.etats import StatutContrat
from prestations.models import Contrat, JournalAudit, Message
from socle.audit import journaliser

TEXTE_MAX = 2000
MESSAGES_PAR_JOUR = 20  # de la structure, par contrat
SANS_RAPPEL = timedelta(hours=24)  # pas de second SMS tant que le précédent n'est pas lu

Auteur = Literal["structure", "equipe"]


class EntreeFil(BaseModel):
    id: UUID
    auteur: Auteur
    nom_auteur: str = Field("", description="Membre de l'équipe ; montré à l'équipe seulement")
    texte: str
    quand: datetime
    lu_le: datetime | None = Field(None, description="Lu par l'autre partie")
    retire: bool = False
    motif_retrait: str = ""


class Fil(BaseModel):
    reference: str
    structure: str
    ouvert: bool
    entrees: list[EntreeFil]
    a_lire: int


class NouveauMessage(BaseModel):
    texte: str = Field(min_length=1, max_length=TEXTE_MAX)


class Retrait(BaseModel):
    motif: str = Field(min_length=3, max_length=200)


class LienDeSuivi(BaseModel):
    lien: str
    sms_envoye: bool


def nouvelle_cle() -> str:
    return secrets.token_urlsafe(24)


def empreinte(cle: str) -> str:
    return hashlib.sha256(cle.encode()).hexdigest()


async def pour_la_structure(session: AsyncSession, reference: str, cle: str | None) -> Contrat:
    contrat = await acces.contrat(session, reference)
    attendue = contrat.empreinte_cle_suivi
    if not (cle and attendue and hmac.compare_digest(attendue, empreinte(cle))):
        # Même réponse qu'une référence inconnue : on ne révèle pas quels contrats existent.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lien de suivi invalide")
    return contrat


def entree(message: Message, lecteur: Auteur) -> EntreeFil:
    retire = message.retire_le is not None
    return EntreeFil(
        id=message.id,
        auteur=message.auteur,
        nom_auteur=message.nom_auteur if lecteur == "equipe" else "",
        texte="" if retire else message.texte,
        quand=message.cree_le,
        lu_le=message.lu_le,
        retire=retire,
        motif_retrait=message.motif_retrait if lecteur == "equipe" else "",
    )


def _a_lire(contrat: Contrat, lecteur: Auteur):  # type: ignore[no-untyped-def]
    autre = "equipe" if lecteur == "structure" else "structure"
    return (
        Message.contrat_id == contrat.id,
        Message.auteur == autre,
        Message.lu_le.is_(None),
        Message.retire_le.is_(None),
    )


async def fil(session: AsyncSession, contrat: Contrat, lecteur: Auteur) -> Fil:
    messages = (
        await session.scalars(
            select(Message).where(Message.contrat_id == contrat.id).order_by(Message.cree_le)
        )
    ).all()
    a_lire = await session.scalar(
        select(func.count()).select_from(Message).where(*_a_lire(contrat, lecteur))
    )
    return Fil(
        reference=contrat.reference,
        structure=contrat.structure,
        ouvert=contrat.statut != StatutContrat.TERMINE,
        entrees=[entree(m, lecteur) for m in messages],
        a_lire=int(a_lire or 0),
    )


async def marquer_lus(session: AsyncSession, contrat: Contrat, lecteur: Auteur) -> None:
    await session.execute(
        update(Message).where(*_a_lire(contrat, lecteur)).values(lu_le=calendrier.maintenant())
    )
    await session.commit()


async def compter_a_lire(session: AsyncSession) -> dict[UUID, int]:
    """Messages de structures pas encore lus par l'équipe, par contrat."""
    lignes = await session.execute(
        select(Message.contrat_id, func.count())
        .where(Message.auteur == "structure", Message.lu_le.is_(None), Message.retire_le.is_(None))
        .group_by(Message.contrat_id)
    )
    return {contrat_id: nombre for contrat_id, nombre in lignes}


async def envoyer(
    session: AsyncSession,
    parametres: ParametresPrestations,
    contrat: Contrat,
    auteur: Auteur,
    texte: str,
    *,
    auteur_id: UUID | None = None,
    nom_auteur: str = "",
) -> Message:
    texte = texte.strip()
    if not texte:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Message vide")
    if contrat.statut == StatutContrat.TERMINE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce contrat est terminé")
    maintenant = calendrier.maintenant()
    if auteur == "structure":
        deja = await session.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.contrat_id == contrat.id,
                Message.auteur == "structure",
                Message.cree_le > maintenant - timedelta(days=1),
            )
        )
        if (deja or 0) >= MESSAGES_PAR_JOUR:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, "Trop de messages aujourd'hui : appelez-nous"
            )
    message = Message(
        contrat_id=contrat.id,
        auteur=auteur,
        auteur_id=auteur_id,
        nom_auteur=nom_auteur[:120],
        texte=texte,
        cree_le=maintenant,
    )
    session.add(message)
    await session.flush()
    await _prevenir(session, parametres, contrat, auteur, message, maintenant)
    await session.commit()
    return message


async def _prevenir(
    session: AsyncSession,
    parametres: ParametresPrestations,
    contrat: Contrat,
    auteur: Auteur,
    message: Message,
    maintenant: datetime,
) -> None:
    """Un SMS sans le texte du message ; pas de second SMS tant que le précédent n'est pas lu."""
    precedent = await session.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            Message.contrat_id == contrat.id,
            Message.auteur == auteur,
            Message.id != message.id,
            Message.notifie.is_(True),
            Message.lu_le.is_(None),
            Message.cree_le > maintenant - SANS_RAPPEL,
        )
    )
    if precedent:
        return
    if auteur == "structure":
        for numero in parametres.telephones_equipe:
            notifications.deposer(
                session, "contrat", contrat.id, numero, notifications.message_pour_l_equipe(contrat)
            )
        message.notifie = bool(parametres.telephones_equipe)
    elif contrat.sms_actifs and contrat.empreinte_cle_suivi:
        notifications.deposer(
            session,
            "contrat",
            contrat.id,
            contrat.telephone,
            notifications.message_pour_la_structure(parametres.nom_service, contrat),
        )
        message.notifie = True


async def retirer(
    session: AsyncSession,
    contrat: Contrat,
    message_id: UUID,
    motif: str,
    *,
    acteur_id: UUID,
    adresse_ip: str | None,
) -> Message:
    message = await session.get(Message, message_id, with_for_update=True)
    if message is None or message.contrat_id != contrat.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message introuvable")
    if message.retire_le is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Message déjà retiré")
    message.retire_le = calendrier.maintenant()
    message.retire_par = acteur_id
    message.motif_retrait = motif
    message.texte = ""
    journaliser(
        session,
        JournalAudit,
        action="message.retire",
        acteur_id=acteur_id,
        objet_type="contrat",
        objet_id=contrat.reference,
        details={"message": str(message.id), "auteur": message.auteur, "motif": motif},
        adresse_ip=adresse_ip,
    )
    await session.commit()
    return message


async def envoyer_le_lien(
    session: AsyncSession,
    parametres: ParametresPrestations,
    contrat: Contrat,
    *,
    acteur_id: UUID,
    adresse_ip: str | None,
) -> LienDeSuivi:
    """Crée un nouveau lien (l'ancien cesse de marcher) et le texte à la structure par SMS."""
    cle = nouvelle_cle()
    contrat.empreinte_cle_suivi = empreinte(cle)
    lien = f"{parametres.url_publique.rstrip('/')}/contrat/{contrat.reference}?cle={cle}"
    sms = contrat.sms_actifs
    if sms:
        notifications.deposer(
            session,
            "contrat",
            contrat.id,
            contrat.telephone,
            notifications.lien_de_suivi(parametres.nom_service, contrat, lien),
        )
    journaliser(
        session,
        JournalAudit,
        action="contrat.lien_suivi",
        acteur_id=acteur_id,
        objet_type="contrat",
        objet_id=contrat.reference,
        details={"sms": sms},
        adresse_ip=adresse_ip,
    )
    await session.commit()
    return LienDeSuivi(lien=lien, sms_envoye=sms)
