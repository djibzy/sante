"""Retrouver une commande : par sa référence, avec la clé de son lien de suivi."""

import hashlib
import hmac
import re
import secrets
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from boutique.models import Commande, LigneCommande, ZoneLivraison

_REFERENCE = re.compile(r"(?:BB-?)?(\d{1,9})", re.IGNORECASE)
INTROUVABLE = "Commande introuvable"


def numero(reference: str) -> int:
    """« BB-1001 », « bb1001 » ou « 1001 » donnent 1001."""
    correspondance = _REFERENCE.fullmatch(reference.strip())
    if correspondance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, INTROUVABLE)
    return int(correspondance.group(1))


def nouvelle_cle() -> str:
    return secrets.token_urlsafe(18)


def empreinte(cle: str) -> str:
    return hashlib.sha256(cle.encode()).hexdigest()


def cle_valide(commande: Commande, cle: str | None) -> bool:
    return bool(cle) and hmac.compare_digest(commande.empreinte_cle_suivi, empreinte(cle or ""))


# Tout ce qu'affichent le suivi et la gestion, chargé explicitement (relations en lazy="raise").
_COMPLETE = (
    selectinload(Commande.lignes),
    selectinload(Commande.evenements),
    selectinload(Commande.paiements),
    selectinload(Commande.zone),
    selectinload(Commande.livreur),
    selectinload(Commande.facture),
)


async def charger(session: AsyncSession, reference: str) -> Commande:
    requete = (
        select(Commande)
        .options(*_COMPLETE)
        .where(Commande.numero == numero(reference))
        .execution_options(populate_existing=True)
    )
    commande = (await session.execute(requete)).scalar_one_or_none()
    if commande is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, INTROUVABLE)
    return commande


async def charger_par_id(session: AsyncSession, commande_id: UUID) -> Commande:
    requete = (
        select(Commande)
        .options(*_COMPLETE)
        .where(Commande.id == commande_id)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(requete)).scalar_one()


async def charger_par_cle(session: AsyncSession, cle: str) -> Commande | None:
    requete = (
        select(Commande)
        .options(*_COMPLETE)
        .where(Commande.empreinte_cle_suivi == empreinte(cle))
        .execution_options(populate_existing=True)
    )
    return (await session.execute(requete)).scalar_one_or_none()


async def charger_pour_client(session: AsyncSession, reference: str, cle: str | None) -> Commande:
    """Même réponse pour une référence inconnue et une mauvaise clé : rien ne fuit."""
    commande = await charger(session, reference)
    if not cle_valide(commande, cle):
        raise HTTPException(status.HTTP_404_NOT_FOUND, INTROUVABLE)
    return commande


async def charger_du_client(session: AsyncSession, client_id: UUID) -> list[Commande]:
    """Toutes les commandes passées avec ce compte, complètes, les plus récentes d'abord."""
    requete = (
        select(Commande)
        .options(*_COMPLETE)
        .where(Commande.client_id == client_id)
        .order_by(Commande.cree_le.desc())
    )
    return list((await session.execute(requete)).scalars())


async def charger_pour_compte(session: AsyncSession, reference: str, client_id: UUID) -> Commande:
    """Commande passée avec ce compte ; même réponse qu'une référence inconnue sinon."""
    commande = await charger(session, reference)
    if commande.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, INTROUVABLE)
    return commande


async def verrouiller(session: AsyncSession, commande_id: UUID) -> None:
    """Verrouille la commande jusqu'à la fin de la transaction : deux encaissements simultanés
    (équipe, paiement en ligne) ne peuvent pas écraser le montant payé l'un de l'autre."""
    await session.execute(select(Commande.id).where(Commande.id == commande_id).with_for_update())


def requete_resumes() -> Select[Commande, str | None, int]:
    """Commandes avec le nom de leur zone et leur nombre d'articles, sans charger les lignes."""
    articles = (
        select(func.coalesce(func.sum(LigneCommande.quantite), 0))
        .where(LigneCommande.commande_id == Commande.id)
        .correlate(Commande)
        .scalar_subquery()
    )
    return select(Commande, ZoneLivraison.nom, articles).outerjoin(
        ZoneLivraison, Commande.zone_id == ZoneLivraison.id
    )
