"""Avis clients : notes publiées sur les fiches produits, dépôt depuis le suivi d'une commande
livrée, relecture par l'équipe avant publication."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.avis import service
from boutique.avis.schemas import (
    AvisClient,
    AvisCommande,
    AvisGestion,
    Moderation,
    NouvelAvis,
    PageAvis,
    PageAvisGestion,
)
from boutique.commandes import acces
from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.models import Avis, Commande, Produit
from boutique.routes.commandes import CLE, LIMITE_DEMANDES, LIMITE_LECTURES
from socle.db import session_db
from socle.security import Principal, exiger_role, principal_requis

routeur = APIRouter(prefix="/api/v1", tags=["avis"])
routeur_equipe = APIRouter(prefix="/api/v1/admin", tags=["avis"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _deposer(
    request: Request,
    response: Response,
    session: AsyncSession,
    commande: Commande,
    donnees: NouvelAvis,
    acteur: Principal | None,
) -> AvisClient:
    avis, cree = await service.deposer(
        session, commande, donnees, acteur.id if acteur else None, _ip(request)
    )
    response.status_code = status.HTTP_201_CREATED if cree else status.HTTP_200_OK
    return avis


@routeur.get("/produits/{slug}/avis", summary="Avis publiés sur un produit")
async def avis_du_produit(
    slug: str,
    page: int = Query(1, ge=1, le=1000),
    par_page: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(session_db),
) -> PageAvis:
    produit = await session.scalar(select(Produit).where(Produit.slug == slug, Produit.est_actif))
    if produit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit introuvable")
    return await service.page_publique(session, produit, page, par_page)


@routeur.get(
    "/suivi/{reference}/avis",
    summary="Produits de la commande à noter",
    dependencies=[LIMITE_LECTURES],
)
async def avis_suivi(
    reference: str, cle: str | None = CLE, session: AsyncSession = Depends(session_db)
) -> AvisCommande:
    commande = await acces.charger_pour_client(session, reference, cle)
    return await service.de_la_commande(session, commande)


@routeur.post(
    "/suivi/{reference}/avis",
    summary="Donner son avis sur un produit reçu",
    status_code=status.HTTP_201_CREATED,
    dependencies=[LIMITE_DEMANDES],
)
async def deposer_suivi(
    reference: str,
    donnees: NouvelAvis,
    request: Request,
    response: Response,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> AvisClient:
    commande = await acces.charger_pour_client(session, reference, cle)
    return await _deposer(request, response, session, commande, donnees, None)


@routeur.get("/mes-commandes/{reference}/avis", summary="Produits de ma commande à noter")
async def avis_mien(
    reference: str,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> AvisCommande:
    commande = await acces.charger_pour_compte(session, reference, principal.id)
    return await service.de_la_commande(session, commande)


@routeur.post(
    "/mes-commandes/{reference}/avis",
    summary="Donner mon avis sur un produit reçu",
    status_code=status.HTTP_201_CREATED,
    dependencies=[LIMITE_DEMANDES],
)
async def deposer_mien(
    reference: str,
    donnees: NouvelAvis,
    request: Request,
    response: Response,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> AvisClient:
    commande = await acces.charger_pour_compte(session, reference, principal.id)
    return await _deposer(request, response, session, commande, donnees, principal)


@routeur_equipe.get("/avis", summary="Avis à relire, publiés ou refusés")
async def lister(
    statut: Literal["en_attente", "publie", "refuse"] = "en_attente",
    page: int = Query(1, ge=1),
    par_page: int = Query(30, ge=1, le=100),
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> PageAvisGestion:
    total = await session.scalar(
        select(func.count()).select_from(Avis).where(Avis.statut == statut)
    )
    # Les plus anciens d'abord pour la relecture, les plus récents d'abord une fois traités.
    ordre = Avis.cree_le.asc() if statut == "en_attente" else Avis.modere_le.desc()
    requete = (
        select(Avis, Produit, Commande.numero)
        .join(Produit, Produit.id == Avis.produit_id)
        .join(Commande, Commande.id == Avis.commande_id)
        .where(Avis.statut == statut)
        .order_by(ordre, Avis.id)
        .offset((page - 1) * par_page)
        .limit(par_page)
    )
    return PageAvisGestion(
        elements=[
            service.vue_gestion(avis, produit, numero)
            for avis, produit, numero in await session.execute(requete)
        ],
        total=total or 0,
        page=page,
        par_page=par_page,
    )


@routeur_equipe.post("/avis/{avis_id}/moderation", summary="Publier ou refuser un avis")
async def moderer(
    avis_id: UUID,
    decision: Moderation,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> AvisGestion:
    avis = await service.moderer(session, avis_id, decision, principal)
    await session.commit()
    produit = await session.get_one(Produit, avis.produit_id)
    numero = await session.scalar(select(Commande.numero).where(Commande.id == avis.commande_id))
    return service.vue_gestion(avis, produit, numero or 0)
