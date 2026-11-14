"""Blanchisseries et pressings partenaires : coordonnées, délai, tarifs (ce qu'ils nous
facturent), visite d'hygiène. L'équipe de terrain n'en voit que de quoi déposer le linge."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces
from prestations.etats import ModeTarif
from prestations.models import JournalAudit, Partenaire
from prestations.routes import GESTION, TERRAIN, adresse_ip
from prestations.schemas import (
    ModificationPartenaire,
    NouveauPartenaire,
    PartenaireResume,
    PartenaireVue,
)
from prestations.vues import partenaire_resume
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal

routeur = APIRouter(prefix="/api/v1", tags=["partenaires"])
NOM_PRIS = "Un partenaire porte déjà ce nom"


async def _enregistrer(session: AsyncSession) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, NOM_PRIS) from exc


@routeur.get("/partenaires", summary="Partenaires en activité, pour le dépôt du linge")
async def pour_la_tournee(
    _: Principal = Depends(TERRAIN), session: AsyncSession = Depends(session_db)
) -> list[PartenaireResume]:
    partenaires = await session.scalars(
        select(Partenaire).where(Partenaire.est_actif).order_by(Partenaire.nom)
    )
    return [partenaire_resume(p) for p in partenaires]


@routeur.get("/admin/partenaires", summary="Tous les partenaires et leurs tarifs")
async def lister(
    _: Principal = Depends(GESTION), session: AsyncSession = Depends(session_db)
) -> list[PartenaireVue]:
    partenaires = await session.scalars(
        select(Partenaire).order_by(Partenaire.est_actif.desc(), Partenaire.nom)
    )
    return [PartenaireVue.model_validate(p) for p in partenaires]


@routeur.post(
    "/admin/partenaires", status_code=status.HTTP_201_CREATED, summary="Ajouter un partenaire"
)
async def ajouter(
    donnees: NouveauPartenaire,
    request: Request,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> PartenaireVue:
    valeurs = donnees.model_dump()
    valeurs["telephone"] = acces.telephone(donnees.telephone)
    valeurs["tarifs"] = {article.value: prix for article, prix in donnees.tarifs.items()}
    partenaire = Partenaire(**valeurs)
    session.add(partenaire)
    await _enregistrer(session)
    journaliser(
        session,
        JournalAudit,
        action="partenaire.ajoute",
        acteur_id=principal.id,
        objet_type="partenaire",
        objet_id=partenaire.id,
        details={"nom": partenaire.nom},
        adresse_ip=adresse_ip(request),
    )
    await session.commit()
    return PartenaireVue.model_validate(partenaire)


@routeur.patch("/admin/partenaires/{identifiant}", summary="Modifier un partenaire")
async def modifier(
    identifiant: UUID,
    donnees: ModificationPartenaire,
    request: Request,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> PartenaireVue:
    partenaire = await acces.partenaire(session, identifiant)
    changements = donnees.model_dump(exclude_unset=True)
    for requis in ("nom", "type", "telephone", "delai_jours", "mode_tarif", "tarifs"):
        if requis in changements and changements[requis] is None:
            del changements[requis]
    if changements.get("telephone"):
        changements["telephone"] = acces.telephone(changements["telephone"])
    if "tarifs" in changements:
        changements["tarifs"] = {str(a): prix for a, prix in changements["tarifs"].items()}
    for champ, valeur in changements.items():
        setattr(partenaire, champ, valeur)
    if partenaire.mode_tarif == ModeTarif.KG and partenaire.tarif_kg is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Indiquez le prix au kilo de ce partenaire"
        )
    await _enregistrer(session)
    journaliser(
        session,
        JournalAudit,
        action="partenaire.modifie",
        acteur_id=principal.id,
        objet_type="partenaire",
        objet_id=partenaire.id,
        details={"champs": sorted(changements)},
        adresse_ip=adresse_ip(request),
    )
    await session.commit()
    return PartenaireVue.model_validate(partenaire)
