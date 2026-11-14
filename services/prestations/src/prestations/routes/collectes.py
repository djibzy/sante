"""La tournée et le linge, pour l'équipe de terrain (et la gestion) : enlever en comptant,
déposer chez le partenaire, rendre en recomptant. Aucun prix dans ces réponses."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces, calendrier, operations
from prestations.config import ROLE_ADMIN_PRESTATIONS
from prestations.etats import StatutCollecte
from prestations.models import Collecte
from prestations.routes import GESTION, TERRAIN, adresse_ip, parametres
from prestations.schemas import (
    Annulation,
    AnnulationPassage,
    CollectePonctuelle,
    CollecteVue,
    Depot,
    Enlevement,
    PageCollectes,
    Retour,
    Tournee,
)
from prestations.tournee import tournee
from prestations.vues import collecte_vue
from socle.db import session_db
from socle.security import Principal

routeur = APIRouter(prefix="/api/v1", tags=["tournée et collectes"])


@routeur.get("/tournee", summary="La tournée d'un jour (aujourd'hui par défaut)")
async def tournee_du_jour(
    jour: date | None = Query(None, description="AAAA-MM-JJ"),
    _: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> Tournee:
    return await tournee(session, jour or calendrier.aujourd_hui())


@routeur.post(
    "/tournee/annulations",
    summary="Rien à collecter à ce passage (structure fermée, linge pas prêt…)",
)
async def annuler_passage(
    donnees: AnnulationPassage,
    request: Request,
    principal: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> CollecteVue:
    collecte = await operations.annuler_passage(
        session,
        principal,
        donnees.contrat_id,
        donnees.jour,
        donnees.motif,
        adresse_ip(request),
        gestion=principal.a_role(ROLE_ADMIN_PRESTATIONS),
    )
    return collecte_vue(collecte)


@routeur.post(
    "/collectes",
    status_code=status.HTTP_201_CREATED,
    summary="Enlever le linge d'une structure, compté article par article",
)
async def enlever(
    donnees: Enlevement,
    request: Request,
    principal: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> CollecteVue:
    collecte = await operations.enlever(
        session, parametres(request), principal, donnees, adresse_ip(request)
    )
    return collecte_vue(collecte)


@routeur.post(
    "/collectes/ponctuelles",
    status_code=status.HTTP_201_CREATED,
    summary="Prévoir une collecte hors calendrier (la structure a appelé)",
)
async def prevoir(
    donnees: CollectePonctuelle,
    request: Request,
    principal: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> CollecteVue:
    collecte = await operations.prevoir(
        session,
        principal,
        donnees.contrat_id,
        donnees.prevue_le,
        donnees.observations,
        adresse_ip(request),
    )
    return collecte_vue(collecte)


@routeur.get("/collectes/{reference}", summary="Bon de collecte")
async def detail(
    reference: str,
    _: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> CollecteVue:
    return collecte_vue(await acces.collecte(session, reference))


@routeur.post("/collectes/{reference}/depot", summary="Linge déposé chez le partenaire")
async def deposer(
    reference: str,
    donnees: Depot,
    request: Request,
    principal: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> CollecteVue:
    collecte = await operations.deposer(session, principal, reference, donnees, adresse_ip(request))
    return collecte_vue(collecte)


@routeur.post("/collectes/{reference}/prete", summary="Le partenaire a fini : linge à reprendre")
async def marquer_prete(
    reference: str,
    request: Request,
    principal: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> CollecteVue:
    collecte = await operations.marquer_prete(session, principal, reference, adresse_ip(request))
    return collecte_vue(collecte)


@routeur.post("/collectes/{reference}/retour", summary="Linge rendu, recompté article par article")
async def rendre(
    reference: str,
    donnees: Retour,
    request: Request,
    principal: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> CollecteVue:
    collecte = await operations.rendre(
        session, parametres(request), principal, reference, donnees, adresse_ip(request)
    )
    return collecte_vue(collecte)


@routeur.post("/collectes/{reference}/annulation", summary="Annuler une collecte")
async def annuler(
    reference: str,
    donnees: Annulation,
    request: Request,
    principal: Principal = Depends(TERRAIN),
    session: AsyncSession = Depends(session_db),
) -> CollecteVue:
    collecte = await operations.annuler(
        session,
        principal,
        reference,
        donnees,
        adresse_ip(request),
        gestion=principal.a_role(ROLE_ADMIN_PRESTATIONS),
    )
    return collecte_vue(collecte)


@routeur.get("/admin/collectes", summary="Collectes, les plus récentes d'abord")
async def lister(
    contrat: str | None = Query(None, description="Référence du contrat, ex. CT-101"),
    statut: list[StatutCollecte] | None = Query(None),
    page: int = Query(1, ge=1),
    par_page: int = Query(30, ge=1, le=100),
    _: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> PageCollectes:
    filtres: list[ColumnElement[bool]] = []
    if contrat:
        filtres.append(Collecte.contrat_id == (await acces.contrat(session, contrat)).id)
    if statut:
        filtres.append(Collecte.statut.in_(statut))
    total = await session.scalar(select(func.count(Collecte.id)).where(*filtres))
    collectes = await session.scalars(
        acces.requete_collectes()
        .where(*filtres)
        .order_by(Collecte.prevue_le.desc(), Collecte.numero.desc())
        .offset((page - 1) * par_page)
        .limit(par_page)
    )
    return PageCollectes(elements=[collecte_vue(c) for c in collectes], total=total or 0)
