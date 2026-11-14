"""Page publique : l'offre (articles pris en charge, types de structure) et la demande d'une
structure, qui part à l'équipe."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces, calendrier, notifications
from prestations.linge import ARTICLES, FAMILLES, SERVICES, TYPES_STRUCTURE
from prestations.models import Demande, JournalAudit
from prestations.routes import adresse_ip, parametres
from prestations.schemas import ArticleOffre, Choix, DemandeRecue, NouvelleDemande, Offre
from socle.audit import journaliser
from socle.db import session_db
from socle.limites import LimiteDebit

routeur = APIRouter(prefix="/api/v1", tags=["page publique"])
LIMITE_DEMANDES = Depends(LimiteDebit("demandes", nombre=10, secondes=600))
MERCI = "Merci ! Nous vous rappelons pour convenir d'une visite."
# Même structure, même numéro, dans la demi-heure : la même demande envoyée deux fois.
DOUBLON = timedelta(minutes=30)


@routeur.get("/offre", summary="Services, articles pris en charge et types de structure")
async def offre() -> Offre:
    return Offre(
        services=[Choix(code=code, libelle=nom) for code, nom in SERVICES.items()],
        articles=[
            ArticleOffre(
                code=code,
                libelle=fiche.singulier[0].upper() + fiche.singulier[1:],
                pluriel=fiche.pluriel,
                famille=fiche.famille,
                libelle_famille=FAMILLES[fiche.famille],
                note=fiche.note,
            )
            for code, fiche in ARTICLES.items()
        ],
        types_structure=[Choix(code=code, libelle=nom) for code, nom in TYPES_STRUCTURE.items()],
    )


@routeur.post(
    "/demandes",
    status_code=status.HTTP_201_CREATED,
    summary="Demander un service (structures de santé)",
    dependencies=[LIMITE_DEMANDES],
)
async def demander(
    donnees: NouvelleDemande,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(session_db),
) -> DemandeRecue:
    regle = parametres(request)
    telephone = acces.telephone(donnees.telephone)
    structure = " ".join(donnees.structure.split())
    maintenant = calendrier.maintenant()
    doublon = await session.scalar(
        select(Demande)
        .where(
            Demande.telephone == telephone,
            func.lower(Demande.structure) == structure.lower(),
            Demande.cree_le > maintenant - DOUBLON,
        )
        .order_by(Demande.cree_le.desc())
        .limit(1)
    )
    if doublon is not None:
        response.status_code = status.HTTP_200_OK
        return DemandeRecue(reference=doublon.reference, message=MERCI)
    recentes = await session.scalar(
        select(func.count(Demande.id)).where(
            Demande.telephone == telephone, Demande.cree_le > maintenant - timedelta(hours=24)
        )
    )
    if (recentes or 0) >= regle.demandes_max_par_telephone:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Vos demandes sont bien enregistrées : nous vous rappelons très vite.",
        )
    demande = Demande(
        service=donnees.service,
        structure=structure,
        type_structure=donnees.type_structure,
        contact=donnees.contact.strip(),
        telephone=telephone,
        quartier=donnees.quartier.strip(),
        volumes={article.value: n for article, n in donnees.volumes.items() if n},
        collectes_par_semaine=donnees.collectes_par_semaine,
        message=donnees.message.strip(),
    )
    session.add(demande)
    await session.flush()
    journaliser(
        session,
        JournalAudit,
        action="demande.creee",
        objet_type="demande",
        objet_id=demande.reference,
        details={"service": demande.service, "structure": demande.structure},
        adresse_ip=adresse_ip(request),
    )
    notifications.deposer(
        session,
        "demande",
        demande.id,
        telephone,
        notifications.demande_recue(regle.nom_service, demande),
    )
    for numero in regle.telephones_equipe:
        notifications.deposer(
            session, "demande", demande.id, numero, notifications.demande_pour_l_equipe(demande)
        )
    await session.commit()
    return DemandeRecue(reference=demande.reference, message=MERCI)
