"""Relevés du mois : la synthèse (chiffre, coût des partenaires, marge), son export CSV, et le
relevé de chaque contrat, en PDF pour la structure. Les téléchargements sont journalisés : ils
contiennent des coordonnées."""

from fastapi import APIRouter, Depends, Path, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces, calendrier, releves
from prestations.etats import Formule
from prestations.models import JournalAudit
from prestations.releve_pdf import releve_pdf
from prestations.routes import GESTION, adresse_ip, parametres
from prestations.schemas import Releve, Synthese
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal
from socle.tableurs import en_csv

routeur = APIRouter(prefix="/api/v1/admin", tags=["relevés"])
MOIS = Path(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-11"])
FORMULES = {Formule.PIECE: "à la pièce", Formule.FORFAIT: "forfait"}


def _tracer(
    session: AsyncSession, request: Request, principal: Principal, quoi: str, mois: str
) -> None:
    journaliser(
        session,
        JournalAudit,
        action=f"releve.{quoi}",
        acteur_id=principal.id,
        objet_type="releve",
        objet_id=mois,
        adresse_ip=adresse_ip(request),
    )


@routeur.get("/releves/{mois}.csv", summary="Synthèse du mois, pour le tableur")
async def synthese_csv(
    request: Request,
    mois: str = MOIS,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> Response:
    synthese = await releves.synthese(session, mois)
    contenu = en_csv(
        [
            "Contrat", "Structure", "Formule", "Collectes", "Pièces rendues",
            "Pièces manquantes", "Montant dû (FCFA)", "Coût partenaires (FCFA)", "Marge (FCFA)",
            "Coût incomplet",
        ],
        (
            [c.reference, c.structure, FORMULES[c.formule], c.collectes, c.pieces_rendues,
             c.pieces_manquantes, c.chiffre, c.cout, c.marge, "oui" if c.cout_incomplet else ""]
            for c in synthese.contrats
        ),
    )  # fmt: skip
    _tracer(session, request, principal, "csv", mois)
    await session.commit()
    return Response(
        content=contenu.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="prestations-{mois}.csv"'},
    )


@routeur.get("/releves/{mois}", summary="Synthèse du mois : chiffre, coûts, marge")
async def synthese(
    mois: str = MOIS,
    _: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> Synthese:
    return await releves.synthese(session, mois)


@routeur.get("/contrats/{reference}/releves/{mois}.pdf", summary="Relevé PDF pour la structure")
async def releve_en_pdf(
    reference: str,
    request: Request,
    mois: str = MOIS,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> Response:
    contrat = await acces.contrat(session, reference)
    releve = await releves.releve(session, contrat, mois)
    contenu = releve_pdf(releve, parametres(request), f"{calendrier.aujourd_hui():%d/%m/%Y}")
    _tracer(session, request, principal, "pdf", f"{contrat.reference} {mois}")
    await session.commit()
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="releve-{contrat.reference}-{mois}.pdf"'
        },
    )


@routeur.get("/contrats/{reference}/releves/{mois}", summary="Relevé du mois d'un contrat")
async def releve(
    reference: str,
    mois: str = MOIS,
    _: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> Releve:
    contrat = await acces.contrat(session, reference)
    return await releves.releve(session, contrat, mois)
