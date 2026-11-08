"""Organisations clientes (CSCom, écoles, ONG…) et leurs membres.

Une seule fiche par organisation, partagée par la boutique, la formation et les campagnes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comptes.config import ParametresComptes
from comptes.models import Adhesion, JournalAudit, Organisation, Utilisateur
from comptes.schemas import (
    AjoutMembre,
    CreationOrganisation,
    Membre,
    MonOrganisation,
    OrganisationPublique,
)
from comptes.telephones import NumeroInvalide, normaliser_telephone
from socle.audit import journaliser
from socle.db import session_db
from socle.security import ROLE_ADMIN, Principal, principal_requis

routeur = APIRouter(prefix="/api/v1/organisations", tags=["organisations"])
_INTROUVABLE = "Organisation introuvable"


def _region(request: Request) -> str:
    parametres: ParametresComptes = request.app.state.parametres
    return parametres.region_telephone


def _vue(organisation: Organisation, role: str) -> MonOrganisation:
    return MonOrganisation(
        **OrganisationPublique.model_validate(organisation).model_dump(), mon_role=role
    )


async def _role_de(session: AsyncSession, organisation_id: UUID, principal: Principal) -> str:
    """Rôle de la personne dans l'organisation ; 404 si elle n'en est pas membre."""
    requete = select(Adhesion.role).where(
        Adhesion.organisation_id == organisation_id, Adhesion.utilisateur_id == principal.id
    )
    role = (await session.execute(requete)).scalar_one_or_none()
    if role is not None:
        return role
    if principal.a_role(ROLE_ADMIN):
        return ROLE_ADMIN
    raise HTTPException(status.HTTP_404_NOT_FOUND, _INTROUVABLE)


@routeur.post("", status_code=status.HTTP_201_CREATED, summary="Créer une organisation")
async def creer_organisation(
    donnees: CreationOrganisation,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> MonOrganisation:
    telephone = None
    if donnees.telephone:
        try:
            telephone = normaliser_telephone(donnees.telephone, _region(request))
        except NumeroInvalide as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    organisation = Organisation(
        **donnees.model_dump(exclude={"telephone"}), telephone=telephone, cree_par=principal.id
    )
    session.add(organisation)
    await session.flush()
    session.add(
        Adhesion(organisation_id=organisation.id, utilisateur_id=principal.id, role="gestionnaire")
    )
    journaliser(
        session,
        JournalAudit,
        action="organisation.creee",
        acteur_id=principal.id,
        objet_type="organisation",
        objet_id=organisation.id,
    )
    await session.commit()
    return _vue(organisation, "gestionnaire")


@routeur.get("", summary="Mes organisations")
async def mes_organisations(
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> list[MonOrganisation]:
    requete = (
        select(Organisation, Adhesion.role)
        .join(Adhesion, Adhesion.organisation_id == Organisation.id)
        .where(Adhesion.utilisateur_id == principal.id)
        .order_by(Organisation.nom)
    )
    return [_vue(org, role) for org, role in (await session.execute(requete)).all()]


@routeur.get("/{organisation_id}", summary="Détail d'une organisation")
async def detail_organisation(
    organisation_id: UUID,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> MonOrganisation:
    role = await _role_de(session, organisation_id, principal)
    organisation = await session.get(Organisation, organisation_id)
    if organisation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _INTROUVABLE)
    return _vue(organisation, role)


@routeur.get("/{organisation_id}/membres", summary="Membres d'une organisation")
async def membres(
    organisation_id: UUID,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> list[Membre]:
    await _role_de(session, organisation_id, principal)
    requete = (
        select(Utilisateur.id, Utilisateur.nom, Utilisateur.telephone, Adhesion.role)
        .join(Adhesion, Adhesion.utilisateur_id == Utilisateur.id)
        .where(Adhesion.organisation_id == organisation_id)
        .order_by(Utilisateur.nom)
    )
    return [
        Membre(utilisateur_id=uid, nom=nom, telephone=tel, role=role)
        for uid, nom, tel, role in (await session.execute(requete)).all()
    ]


@routeur.post(
    "/{organisation_id}/membres",
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un membre (gestionnaires seulement)",
)
async def ajouter_membre(
    organisation_id: UUID,
    donnees: AjoutMembre,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> Membre:
    role = await _role_de(session, organisation_id, principal)
    if role not in ("gestionnaire", ROLE_ADMIN):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Réservé aux gestionnaires de l'organisation"
        )
    try:
        telephone = normaliser_telephone(donnees.telephone, _region(request))
    except NumeroInvalide as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    requete = select(Utilisateur).where(Utilisateur.telephone == telephone)
    utilisateur = (await session.execute(requete)).scalar_one_or_none()
    if utilisateur is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Aucun compte avec ce numéro : la personne doit d'abord créer son compte",
        )
    deja = await session.execute(
        select(Adhesion.id).where(
            Adhesion.organisation_id == organisation_id, Adhesion.utilisateur_id == utilisateur.id
        )
    )
    if deja.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette personne est déjà membre")

    session.add(
        Adhesion(organisation_id=organisation_id, utilisateur_id=utilisateur.id, role=donnees.role)
    )
    journaliser(
        session,
        JournalAudit,
        action="organisation.membre_ajoute",
        acteur_id=principal.id,
        objet_type="organisation",
        objet_id=organisation_id,
        details={"utilisateur_id": str(utilisateur.id), "role": donnees.role},
    )
    await session.commit()
    return Membre(
        utilisateur_id=utilisateur.id,
        nom=utilisateur.nom,
        telephone=utilisateur.telephone,
        role=donnees.role,
    )
