"""File de l'atelier, sur tablette : ordres de fabrication et capacité des postes."""

from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.atelier.delais import charges_par_poste
from boutique.atelier.etats import LIBELLES_ORDRE, OUVERTS, PASSAGES_ORDRE, EtatOrdre
from boutique.atelier.etiquettes import Etiquette, etiquettes_pdf
from boutique.atelier.schemas import ChangementEtat, ModificationPoste, OrdreVue, PosteVue
from boutique.commandes import operations
from boutique.commandes.tarifs import aujourd_hui
from boutique.config import ROLE_ADMIN_BOUTIQUE, ROLE_ATELIER
from boutique.models import Commande, JournalAudit, OrdreFabrication, PosteAtelier
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role, exiger_un_role

routeur = APIRouter(prefix="/api/v1", tags=["atelier"])
atelier = exiger_un_role(ROLE_ATELIER, ROLE_ADMIN_BOUTIQUE)
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)


def _vue(ordre: OrdreFabrication, numero: int, etablissement: str | None, nom: str) -> OrdreVue:
    etat = EtatOrdre(ordre.etat)
    return OrdreVue(
        id=ordre.id,
        reference=f"BB-{numero}",
        client=etablissement or nom,
        poste=ordre.poste,
        libelle=ordre.libelle,
        personnalisation=ordre.personnalisation,
        quantite=ordre.quantite,
        etat=etat,
        etat_libelle=LIBELLES_ORDRE[etat],
        date_promise=ordre.date_promise,
        en_retard=etat in OUVERTS
        and ordre.date_promise is not None
        and ordre.date_promise < aujourd_hui(),
        note=ordre.note,
        commence_le=ordre.commence_le,
        termine_le=ordre.termine_le,
        passages_possibles=[e for e in EtatOrdre if e in PASSAGES_ORDRE[etat]],
    )


def _requete() -> Select[OrdreFabrication, int, str | None, str]:
    return select(
        OrdreFabrication, Commande.numero, Commande.etablissement, Commande.nom_client
    ).join(Commande, OrdreFabrication.commande_id == Commande.id)


@routeur.get("/atelier/ordres", summary="File de fabrication, la plus urgente d'abord")
async def file(
    poste: str | None = Query(None, max_length=20),
    etat: list[EtatOrdre] | None = Query(None, description="Par défaut : à faire, en cours"),
    _: Principal = Depends(atelier),
    session: AsyncSession = Depends(session_db),
) -> list[OrdreVue]:
    requete = (
        _requete()
        .where(OrdreFabrication.etat.in_(etat or OUVERTS))
        .order_by(
            OrdreFabrication.date_promise.asc().nulls_last(),
            Commande.numero,
            OrdreFabrication.cree_le,
        )
        .limit(300)
    )
    if poste:
        requete = requete.where(OrdreFabrication.poste == poste)
    return [_vue(o, n, e, nom) for o, n, e, nom in await session.execute(requete)]


@routeur.get(
    "/atelier/etiquettes.pdf",
    summary="Étiquettes des pièces de la file (A4, dix par page), à épingler sur les vêtements",
    response_class=Response,
)
async def etiquettes(
    poste: str | None = Query(None, max_length=20),
    etat: list[EtatOrdre] | None = Query(None, description="Par défaut : à faire, en cours"),
    _: Principal = Depends(atelier),
    session: AsyncSession = Depends(session_db),
) -> Response:
    requete = (
        _requete()
        .add_columns(PosteAtelier.nom)
        .join(PosteAtelier, PosteAtelier.code == OrdreFabrication.poste)
        .where(OrdreFabrication.etat.in_(etat or OUVERTS))
        .order_by(
            OrdreFabrication.date_promise.asc().nulls_last(),
            Commande.numero,
            OrdreFabrication.cree_le,
        )
        .limit(300)
    )
    if poste:
        requete = requete.where(OrdreFabrication.poste == poste)
    contenu = etiquettes_pdf(
        [
            Etiquette(
                reference=f"BB-{numero}",
                client=etablissement or nom,
                libelle=ordre.libelle,
                personnalisation=ordre.personnalisation,
                quantite=ordre.quantite,
                poste=nom_poste,
                poste_code=ordre.poste,
                date_promise=ordre.date_promise,
            )
            for ordre, numero, etablissement, nom, nom_poste in await session.execute(requete)
        ]
    )
    return Response(
        contenu,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="etiquettes-atelier.pdf"',
            "Cache-Control": "no-store",
        },
    )


@routeur.post("/atelier/ordres/{ordre_id}/etat", summary="Faire avancer une pièce")
async def changer_etat(
    ordre_id: UUID,
    donnees: ChangementEtat,
    principal: Principal = Depends(atelier),
    session: AsyncSession = Depends(session_db),
) -> OrdreVue:
    ordre = await session.get(OrdreFabrication, ordre_id)
    if ordre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ordre de fabrication introuvable")
    depart, arrivee = EtatOrdre(ordre.etat), donnees.etat
    if arrivee not in PASSAGES_ORDRE[depart]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Passage impossible de « {LIBELLES_ORDRE[depart]} » à « {LIBELLES_ORDRE[arrivee]} »",
        )
    ordre.etat = arrivee
    maintenant = datetime.now(UTC)
    if arrivee == EtatOrdre.EN_COURS and ordre.commence_le is None:
        ordre.commence_le = maintenant
    if arrivee == EtatOrdre.TERMINE:
        ordre.termine_le = maintenant
    if donnees.note.strip():
        ordre.note = donnees.note.strip()
    await session.flush()
    await operations.apres_changement_ordre(session, ordre, principal.id)
    journaliser(
        session,
        JournalAudit,
        action="atelier.ordre",
        acteur_id=principal.id,
        objet_type="ordre_fabrication",
        objet_id=ordre.id,
        details={"de": depart.value, "vers": arrivee.value},
    )
    await session.commit()
    ligne = (await session.execute(_requete().where(OrdreFabrication.id == ordre_id))).one()
    return _vue(*ligne)


async def _postes(session: AsyncSession) -> list[PosteVue]:
    charges = await charges_par_poste(session)
    postes = await session.scalars(select(PosteAtelier).order_by(PosteAtelier.code))
    return [
        PosteVue(
            code=p.code,
            nom=p.nom,
            capacite_jour=p.capacite_jour,
            est_actif=p.est_actif,
            charge=charges.get(p.code, 0),
            jours_de_file=ceil(charges.get(p.code, 0) / p.capacite_jour),
        )
        for p in postes
    ]


@routeur.get("/atelier/postes", summary="Postes, capacité et charge")
async def postes(
    _: Principal = Depends(atelier), session: AsyncSession = Depends(session_db)
) -> list[PosteVue]:
    return await _postes(session)


@routeur.patch("/admin/postes/{code}", summary="Modifier la capacité d'un poste")
async def modifier_poste(
    code: str,
    donnees: ModificationPoste,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> list[PosteVue]:
    poste = await session.scalar(select(PosteAtelier).where(PosteAtelier.code == code))
    if poste is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Poste introuvable")
    changements = donnees.model_dump(exclude_unset=True)
    for champ, valeur in changements.items():
        setattr(poste, champ, valeur)
    journaliser(
        session,
        JournalAudit,
        action="atelier.poste_modifie",
        acteur_id=principal.id,
        objet_type="poste_atelier",
        objet_id=poste.code,
        details=changements,
    )
    await session.commit()
    return await _postes(session)
