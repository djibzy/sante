"""Tenues proposées : idées de tenue complètes, composées par l'équipe dans « Composer ma
tenue », montrées sur la page « Explorer » et dans le composeur."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.models import JournalAudit, TenueProposee
from boutique.schemas import Metier
from boutique.tenues import service
from boutique.tenues.schemas import ModificationTenue, NouvelleTenue, TenueGestion, TenueVue
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role

routeur = APIRouter(prefix="/api/v1", tags=["catalogue"])
routeur_equipe = APIRouter(prefix="/api/v1/admin", tags=["gestion du catalogue"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)
ORDRE = (TenueProposee.position, TenueProposee.cree_le)


@routeur.get("/tenues-proposees", summary="Idées de tenues complètes")
async def lister(
    metier: Metier | None = None, session: AsyncSession = Depends(session_db)
) -> list[TenueVue]:
    requete = select(TenueProposee).where(TenueProposee.est_active).order_by(*ORDRE)
    if metier:
        requete = requete.where(TenueProposee.metier == metier)
    tenues = await service.vues(session, list(await session.scalars(requete)))
    # Une tenue réduite à une pièce n'a plus de sens : elle attend que l'équipe la revoie.
    return [service.publique(t) for t in tenues if len(t.pieces) >= 2]


@routeur_equipe.get("/tenues-proposees", summary="Toutes les tenues proposées")
async def lister_tout(
    _: Principal = Depends(equipe), session: AsyncSession = Depends(session_db)
) -> list[TenueGestion]:
    tenues = await session.scalars(select(TenueProposee).order_by(*ORDRE))
    return await service.vues(session, list(tenues))


@routeur_equipe.post(
    "/tenues-proposees", status_code=status.HTTP_201_CREATED, summary="Proposer une tenue"
)
async def creer(
    donnees: NouvelleTenue,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> TenueGestion:
    derniere = await session.scalar(select(func.max(TenueProposee.position)))
    tenue = TenueProposee(
        nom=donnees.nom.strip(),
        description=donnees.description.strip(),
        metier=donnees.metier,
        pieces=await service.verifier(session, donnees.pieces),
        position=(derniere if derniere is not None else -1) + 1,  # à la suite des autres
    )
    session.add(tenue)
    await session.flush()
    journaliser(
        session,
        JournalAudit,
        action="tenue.proposee",
        acteur_id=principal.id,
        objet_type="tenue_proposee",
        objet_id=tenue.id,
        details={"nom": tenue.nom, "pieces": len(tenue.pieces)},
    )
    await session.commit()
    [vue] = await service.vues(session, [tenue])
    return vue


async def _tenue(session: AsyncSession, tenue_id: UUID) -> TenueProposee:
    tenue = await session.get(TenueProposee, tenue_id)
    if tenue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenue introuvable")
    return tenue


@routeur_equipe.patch("/tenues-proposees/{tenue_id}", summary="Renommer, ranger, masquer")
async def modifier(
    tenue_id: UUID,
    donnees: ModificationTenue,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> TenueGestion:
    tenue = await _tenue(session, tenue_id)
    changements = donnees.model_dump(exclude_unset=True, exclude_none=True)
    for champ, valeur in changements.items():
        setattr(tenue, champ, valeur.strip() if isinstance(valeur, str) else valeur)
    journaliser(
        session,
        JournalAudit,
        action="tenue.modifiee",
        acteur_id=principal.id,
        objet_type="tenue_proposee",
        objet_id=tenue.id,
        details={"champs": sorted(changements)},
    )
    await session.commit()
    [vue] = await service.vues(session, [tenue])
    return vue


@routeur_equipe.delete(
    "/tenues-proposees/{tenue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirer une tenue proposée",
)
async def supprimer(
    tenue_id: UUID,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> Response:
    tenue = await _tenue(session, tenue_id)
    journaliser(
        session,
        JournalAudit,
        action="tenue.retiree",
        acteur_id=principal.id,
        objet_type="tenue_proposee",
        objet_id=tenue.id,
        details={"nom": tenue.nom},
    )
    await session.delete(tenue)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
