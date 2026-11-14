"""Le fil d'un contrat : la structure y écrit depuis son lien de suivi, l'équipe depuis la
gestion."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces, messagerie
from prestations.messagerie import EntreeFil, Fil, LienDeSuivi, NouveauMessage, Retrait
from prestations.routes import GESTION, adresse_ip, parametres
from socle.db import session_db
from socle.limites import LimiteDebit
from socle.security import Principal

routeur = APIRouter(prefix="/api/v1", tags=["messagerie"])
CLE = Query(None, max_length=64, description="Clé du lien de suivi")
LIMITE_LECTURES = Depends(LimiteDebit("fil-lecture", nombre=120, secondes=600))
LIMITE_MESSAGES = Depends(LimiteDebit("fil-messages", nombre=30, secondes=600))
# Essais de clés devinées : par adresse IP.
LIMITE_ESSAIS = Depends(LimiteDebit("fil-cle", nombre=60, secondes=600))

# --- La structure -----------------------------------------------------------------------------


@routeur.get(
    "/contrat/{reference}/fil",
    summary="Le fil de mon contrat",
    dependencies=[LIMITE_LECTURES, LIMITE_ESSAIS],
)
async def lire(
    reference: str, cle: str | None = CLE, session: AsyncSession = Depends(session_db)
) -> Fil:
    contrat = await messagerie.pour_la_structure(session, reference, cle)
    return await messagerie.fil(session, contrat, "structure")


@routeur.post(
    "/contrat/{reference}/messages",
    status_code=status.HTTP_201_CREATED,
    summary="Écrire à l'équipe",
    dependencies=[LIMITE_MESSAGES, LIMITE_ESSAIS],
)
async def ecrire(
    reference: str,
    donnees: NouveauMessage,
    request: Request,
    cle: str | None = CLE,
    session: AsyncSession = Depends(session_db),
) -> EntreeFil:
    contrat = await messagerie.pour_la_structure(session, reference, cle)
    message = await messagerie.envoyer(
        session, parametres(request), contrat, "structure", donnees.texte
    )
    return messagerie.entree(message, "structure")


@routeur.post(
    "/contrat/{reference}/messages/lecture",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="J'ai lu les messages de l'équipe",
    dependencies=[LIMITE_ESSAIS],
)
async def lu(
    reference: str, cle: str | None = CLE, session: AsyncSession = Depends(session_db)
) -> None:
    contrat = await messagerie.pour_la_structure(session, reference, cle)
    await messagerie.marquer_lus(session, contrat, "structure")


# --- L'équipe ---------------------------------------------------------------------------------

GESTION_CONTRAT = "/admin/contrats/{reference}"


@routeur.get(f"{GESTION_CONTRAT}/fil", summary="Le fil d'un contrat")
async def lire_en_gestion(
    reference: str,
    _: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> Fil:
    return await messagerie.fil(session, await acces.contrat(session, reference), "equipe")


@routeur.post(
    f"{GESTION_CONTRAT}/messages",
    status_code=status.HTTP_201_CREATED,
    summary="Écrire à la structure",
)
async def ecrire_en_gestion(
    reference: str,
    donnees: NouveauMessage,
    request: Request,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> EntreeFil:
    message = await messagerie.envoyer(
        session,
        parametres(request),
        await acces.contrat(session, reference),
        "equipe",
        donnees.texte,
        auteur_id=principal.id,
        nom_auteur=principal.nom or "",
    )
    return messagerie.entree(message, "equipe")


@routeur.post(
    f"{GESTION_CONTRAT}/messages/lecture",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="L'équipe a lu les messages de la structure",
)
async def lu_en_gestion(
    reference: str,
    _: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> None:
    await messagerie.marquer_lus(session, await acces.contrat(session, reference), "equipe")


@routeur.post(
    f"{GESTION_CONTRAT}/messages/{{message_id}}/retrait",
    summary="Retirer un message qui n'a rien à faire ici (information de santé…)",
)
async def retirer(
    reference: str,
    message_id: UUID,
    donnees: Retrait,
    request: Request,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> EntreeFil:
    message = await messagerie.retirer(
        session,
        await acces.contrat(session, reference),
        message_id,
        donnees.motif,
        acteur_id=principal.id,
        adresse_ip=adresse_ip(request),
    )
    return messagerie.entree(message, "equipe")


@routeur.post(
    f"{GESTION_CONTRAT}/lien-de-suivi",
    summary="Envoyer (ou renvoyer) à la structure son lien de suivi par SMS",
)
async def lien_de_suivi(
    reference: str,
    request: Request,
    principal: Principal = Depends(GESTION),
    session: AsyncSession = Depends(session_db),
) -> LienDeSuivi:
    return await messagerie.envoyer_le_lien(
        session,
        parametres(request),
        await acces.contrat(session, reference, verrou=True),
        acteur_id=principal.id,
        adresse_ip=adresse_ip(request),
    )
