"""Retrouver une demande, un contrat ou une collecte par sa référence, avec ce qu'il faut
charger (les relations sont en lazy="raise" : rien ne se charge sans qu'on le demande)."""

import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from prestations.models import Collecte, Contrat, Demande, Partenaire
from socle.telephones import NumeroInvalide, normaliser_telephone

CHARGEMENT_CONTRAT: tuple[LoaderOption, ...] = (selectinload(Contrat.partenaire),)
CHARGEMENT_COLLECTE: tuple[LoaderOption, ...] = (
    selectinload(Collecte.lignes),
    selectinload(Collecte.partenaire),
    selectinload(Collecte.contrat).selectinload(Contrat.partenaire),
)


def numero(reference: str, prefixe: str) -> int:
    """« BC-1001 », « bc 1001 » ou « 1001 » : 1001 ; sinon, introuvable."""
    trouve = re.fullmatch(rf"(?:{prefixe}[-\s]?)?(\d{{1,9}})", reference.strip(), re.IGNORECASE)
    if not trouve:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Référence inconnue")
    return int(trouve.group(1))


def telephone(brut: str) -> str:
    try:
        return normaliser_telephone(brut)
    except NumeroInvalide as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Numéro de téléphone invalide"
        ) from exc


def requete_collectes() -> Select[Collecte]:
    return select(Collecte).options(*CHARGEMENT_COLLECTE)


async def collecte(session: AsyncSession, reference: str, *, verrou: bool = False) -> Collecte:
    requete = requete_collectes().where(Collecte.numero == numero(reference, "BC"))
    if verrou:
        requete = requete.with_for_update(of=Collecte)
    trouvee = await session.scalar(requete)
    if trouvee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collecte introuvable")
    return trouvee


async def contrat(session: AsyncSession, reference: str, *, verrou: bool = False) -> Contrat:
    requete = (
        select(Contrat)
        .options(*CHARGEMENT_CONTRAT)
        .where(Contrat.numero == numero(reference, "CT"))
    )
    if verrou:
        requete = requete.with_for_update(of=Contrat)
    trouve = await session.scalar(requete)
    if trouve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrat introuvable")
    return trouve


async def contrat_par_id(session: AsyncSession, identifiant: UUID) -> Contrat:
    trouve = await session.scalar(
        select(Contrat).options(*CHARGEMENT_CONTRAT).where(Contrat.id == identifiant)
    )
    if trouve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrat introuvable")
    return trouve


async def demande(session: AsyncSession, reference: str) -> Demande:
    trouvee = await session.scalar(
        select(Demande).where(Demande.numero == numero(reference, "DE")).with_for_update()
    )
    if trouvee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable")
    return trouvee


async def partenaire(session: AsyncSession, identifiant: UUID) -> Partenaire:
    trouve = await session.get(Partenaire, identifiant)
    if trouve is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partenaire introuvable")
    return trouve
