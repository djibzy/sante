"""Demandes reçues de la page publique : l'équipe rappelle, note, puis signe un contrat ou
classe sans suite."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces
from prestations.etats import StatutDemande
from prestations.models import Contrat, Demande, JournalAudit
from prestations.routes import GESTION, adresse_ip
from prestations.schemas import DemandeVue, ModificationDemande, PageDemandes
from prestations.vues import demande_vue
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal

routeur = APIRouter(prefix="/api/v1/admin/demandes", tags=["gestion des demandes"])


@routeur.get("", summary="Demandes des structures, les plus récentes d'abord")
async def lister(
    statut: list[StatutDemande] | None = Query(None),
    q: str | None = Query(None, max_length=100, description="Structure, contact, téléphone"),
    _: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> PageDemandes:
    filtres: list[ColumnElement[bool]] = []
    if statut:
        filtres.append(Demande.statut.in_(statut))
    if q and q.strip():
        texte = q.strip()
        chiffres = "".join(c for c in texte if c.isdigit())
        conditions: list[ColumnElement[bool]] = [
            Demande.structure.ilike(f"%{texte}%"),
            Demande.contact.ilike(f"%{texte}%"),
            Demande.quartier.ilike(f"%{texte}%"),
        ]
        if chiffres:
            conditions.append(Demande.telephone.contains(chiffres[-8:]))
            if len(chiffres) <= 9:
                conditions.append(Demande.numero == int(chiffres))
        filtres.append(or_(*conditions))
    resultat = await session.execute(
        select(Demande, Contrat.numero)
        .outerjoin(Contrat, Contrat.id == Demande.contrat_id)
        .where(*filtres)
        .order_by(Demande.cree_le.desc())
        .limit(200)
    )
    total = await session.scalar(select(func.count(Demande.id)).where(*filtres))
    nouvelles = await session.scalar(
        select(func.count(Demande.id)).where(Demande.statut == StatutDemande.NOUVELLE)
    )
    return PageDemandes(
        elements=[
            demande_vue(demande, f"CT-{numero}" if numero else None) for demande, numero in resultat
        ],
        total=total or 0,
        nouvelles=nouvelles or 0,
    )


@routeur.patch("/{reference}", summary="Noter un appel, changer le statut d'une demande")
async def modifier(
    reference: str,
    donnees: ModificationDemande,
    request: Request,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> DemandeVue:
    demande = await acces.demande(session, reference)
    changements = donnees.model_dump(exclude_unset=True, exclude_none=True)
    if "statut" in changements and demande.statut == StatutDemande.SIGNEE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Demande déjà signée : voir son contrat")
    for champ, valeur in changements.items():
        setattr(demande, champ, valeur.strip() if isinstance(valeur, str) else valeur)
    journaliser(
        session,
        JournalAudit,
        action="demande.modifiee",
        acteur_id=principal.id,
        objet_type="demande",
        objet_id=demande.reference,
        details={"champs": sorted(changements), "statut": demande.statut},
        adresse_ip=adresse_ip(request),
    )
    await session.commit()
    numero = (
        await session.scalar(select(Contrat.numero).where(Contrat.id == demande.contrat_id))
        if demande.contrat_id
        else None
    )
    return demande_vue(demande, f"CT-{numero}" if numero else None)
