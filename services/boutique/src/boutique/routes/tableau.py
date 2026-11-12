"""Tableau de bord de l'équipe : ventes, devis, délais, clients, alertes, sur une période."""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.indicateurs.calculs import tableau_de_bord
from boutique.indicateurs.schemas import TableauDeBord
from socle.db import session_db
from socle.security import Principal, exiger_role

routeur = APIRouter(prefix="/api/v1/admin", tags=["tableau de bord"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)
_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


@routeur.get("/tableau-de-bord", summary="Indicateurs de la boutique sur une période")
async def tableau(
    du: date | None = Query(None, description="Premier jour (par défaut : 30 derniers jours)"),
    au: date | None = Query(None, description="Dernier jour, compris (par défaut : aujourd'hui)"),
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> TableauDeBord:
    aujourd_hui = datetime.now(UTC).date()
    au = au or aujourd_hui
    du = du or au - timedelta(days=29)
    if du > au:
        raise HTTPException(_422, "Le premier jour doit précéder le dernier")
    if (au - du).days > 366:
        raise HTTPException(_422, "Choisissez une période d'un an au plus")
    return await tableau_de_bord(session, du, au, aujourd_hui)
