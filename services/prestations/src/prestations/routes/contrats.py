"""Contrats avec les structures : calendrier de collecte, partenaire, formule et tarifs.

Signer une demande crée son contrat. Les jours de collecte se changent à tout moment : la
tournée se lit dans le calendrier, il n'y a rien à replanifier.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces, calendrier
from prestations.etats import StatutContrat, StatutDemande
from prestations.models import Contrat, Demande, JournalAudit
from prestations.routes import GESTION, adresse_ip
from prestations.schemas import ContratVue, ModificationContrat, NouveauContrat, verifier_contrat
from prestations.vues import contrat_vue
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal

routeur = APIRouter(prefix="/api/v1/admin/contrats", tags=["contrats"])
_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


async def _partenaire_actif(session: AsyncSession, contrat: Contrat) -> None:
    if contrat.partenaire_id is not None:
        partenaire = await acces.partenaire(session, contrat.partenaire_id)
        if not partenaire.est_actif:
            raise HTTPException(_422, f"{partenaire.nom} ne reçoit plus de linge")


async def _demande_reference(session: AsyncSession, contrat: Contrat) -> str | None:
    numero = await session.scalar(select(Demande.numero).where(Demande.contrat_id == contrat.id))
    return f"DE-{numero}" if numero else None


async def _vue(session: AsyncSession, contrat: Contrat) -> ContratVue:
    relu = await session.scalar(
        select(Contrat)
        .options(*acces.CHARGEMENT_CONTRAT)
        .where(Contrat.id == contrat.id)
        .execution_options(populate_existing=True)
    )
    assert relu is not None
    return contrat_vue(relu, await _demande_reference(session, relu))


@routeur.get("", summary="Contrats, actifs d'abord")
async def lister(
    statut: list[StatutContrat] | None = Query(None),
    _: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> list[ContratVue]:
    requete = select(Contrat, Demande.numero).outerjoin(Demande, Demande.contrat_id == Contrat.id)
    if statut:
        requete = requete.where(Contrat.statut.in_(statut))
    resultat = await session.execute(
        requete.options(*acces.CHARGEMENT_CONTRAT).order_by(
            Contrat.statut != StatutContrat.ACTIF, Contrat.structure
        )
    )
    return [contrat_vue(c, f"DE-{numero}" if numero else None) for c, numero in resultat]


@routeur.post("", status_code=status.HTTP_201_CREATED, summary="Signer un contrat")
async def creer(
    donnees: NouveauContrat,
    request: Request,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> ContratVue:
    demande: Demande | None = None
    if donnees.demande_id is not None:
        demande = await session.get(Demande, donnees.demande_id, with_for_update=True)
        if demande is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable")
        if demande.contrat_id is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Cette demande a déjà son contrat")
    valeurs = donnees.model_dump(exclude={"demande_id"})
    valeurs["telephone"] = acces.telephone(donnees.telephone)
    valeurs["tarifs"] = {article.value: prix for article, prix in donnees.tarifs.items()}
    contrat = Contrat(**valeurs, statut=StatutContrat.ACTIF)
    await _partenaire_actif(session, contrat)
    session.add(contrat)
    await session.flush()
    if demande is not None:
        demande.statut = StatutDemande.SIGNEE
        demande.contrat_id = contrat.id
    journaliser(
        session,
        JournalAudit,
        action="contrat.cree",
        acteur_id=principal.id,
        objet_type="contrat",
        objet_id=contrat.reference,
        details={
            "structure": contrat.structure,
            "formule": contrat.formule,
            "demande": demande.reference if demande else None,
        },
        adresse_ip=adresse_ip(request),
    )
    await session.commit()
    return await _vue(session, contrat)


@routeur.get("/{reference}", summary="Détail d'un contrat")
async def detail(
    reference: str,
    _: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> ContratVue:
    contrat = await acces.contrat(session, reference)
    return contrat_vue(contrat, await _demande_reference(session, contrat))


@routeur.patch("/{reference}", summary="Modifier un contrat (jours, tarifs, statut…)")
async def modifier(
    reference: str,
    donnees: ModificationContrat,
    request: Request,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> ContratVue:
    contrat = await acces.contrat(session, reference, verrou=True)
    changements = donnees.model_dump(exclude_unset=True)
    for requis in (
        "statut", "structure", "type_structure", "contact", "telephone", "adresse",
        "jours_collecte", "delai_retour_jours", "formule", "tarifs", "sms_actifs", "debut_le",
        "notes",
    ):  # fmt: skip
        if requis in changements and changements[requis] is None:
            del changements[requis]
    if changements.get("telephone"):
        changements["telephone"] = acces.telephone(changements["telephone"])
    if "tarifs" in changements:
        changements["tarifs"] = {str(a): prix for a, prix in changements["tarifs"].items()}
    for champ, valeur in changements.items():
        setattr(contrat, champ, valeur)
    if changements.get("statut") == StatutContrat.TERMINE and contrat.fin_le is None:
        contrat.fin_le = max(calendrier.aujourd_hui(), contrat.debut_le)
    try:
        verifier_contrat(contrat.formule, contrat.forfait_mensuel, contrat.debut_le, contrat.fin_le)
    except ValueError as exc:
        raise HTTPException(_422, str(exc)) from exc
    if "partenaire_id" in changements:
        await _partenaire_actif(session, contrat)
    journaliser(
        session,
        JournalAudit,
        action="contrat.modifie",
        acteur_id=principal.id,
        objet_type="contrat",
        objet_id=contrat.reference,
        details={"champs": sorted(changements), "statut": contrat.statut},
        adresse_ip=adresse_ip(request),
    )
    await session.commit()
    return await _vue(session, contrat)
