"""Le fil d'une commande ou d'un devis : messages entre le client et l'équipe, propositions à
accepter, étapes et paiements, au même endroit.

Le client y accède comme à sa commande : par la clé de son lien de suivi (/suivi/…), ou
connecté (/mes-commandes/…). L'équipe y accède depuis la gestion. Les images jointes ne sont
servies que par ces routes.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.commandes import acces
from boutique.config import ROLE_ADMIN_BOUTIQUE, ParametresBoutique
from boutique.messagerie import operations
from boutique.messagerie.etats import Auteur
from boutique.messagerie.operations import Acteur
from boutique.messagerie.schemas import TEXTE_MAX, EntreeFil, Fil, Reponse, Retrait
from boutique.models import Commande
from boutique.routes.commandes import CLE, LIMITE_LECTURES
from socle.db import session_db
from socle.limites import LimiteDebit
from socle.security import Principal, exiger_role, principal_requis

routeur = APIRouter(prefix="/api/v1", tags=["messagerie"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)
# Par adresse IP ; la vraie limite est celle des messages par commande et par jour.
LIMITE_MESSAGES = Depends(LimiteDebit("messages", nombre=40, secondes=600))


def _parametres(request: Request) -> ParametresBoutique:
    parametres: ParametresBoutique = request.app.state.parametres
    return parametres


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _contenu(image: UploadFile | None, parametres: ParametresBoutique) -> bytes | None:
    if image is None or not image.filename:
        return None
    contenu = await image.read(parametres.taille_max_photo + 1)
    if len(contenu) > parametres.taille_max_photo:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Image trop lourde : {parametres.taille_max_photo // (1024 * 1024)} Mo au plus",
        )
    return contenu


def _image(fichier: Path) -> FileResponse:
    # Privée : les caches partagés ne la gardent pas.
    return FileResponse(
        fichier,
        media_type="image/webp",
        headers={"Cache-Control": "private, max-age=3600", "X-Robots-Tag": "noindex"},
    )


# --- Le client --------------------------------------------------------------------------------


@dataclass
class Acces:
    commande: Commande
    compte_id: UUID | None  # vide : venu par le lien de suivi


async def par_le_lien(
    reference: str, cle: str | None = CLE, session: AsyncSession = Depends(session_db)
) -> Acces:
    return Acces(await acces.charger_pour_client(session, reference, cle), None)


async def par_le_compte(
    reference: str,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> Acces:
    commande = await acces.charger_pour_compte(session, reference, principal.id)
    return Acces(commande, principal.id)


def _routes_du_client(prefixe: str, acces_client: Callable[..., Awaitable[Acces]]) -> None:
    """Les mêmes routes pour les deux façons d'arriver à sa commande."""

    @routeur.get(f"{prefixe}/fil", summary="Le fil de ma commande", dependencies=[LIMITE_LECTURES])
    async def lire(
        client: Acces = Depends(acces_client), session: AsyncSession = Depends(session_db)
    ) -> Fil:
        return await operations.fil(session, client.commande, Auteur.CLIENT)

    @routeur.post(
        f"{prefixe}/messages",
        status_code=status.HTTP_201_CREATED,
        summary="Écrire à la boutique (texte, et une image si besoin)",
        dependencies=[LIMITE_MESSAGES],
    )
    async def ecrire(
        request: Request,
        texte: str = Form("", max_length=TEXTE_MAX),
        image: UploadFile | None = File(None),
        client: Acces = Depends(acces_client),
        session: AsyncSession = Depends(session_db),
    ) -> EntreeFil:
        parametres = _parametres(request)
        message = await operations.envoyer(
            session,
            parametres,
            client.commande,
            Acteur(Auteur.CLIENT, client.compte_id),
            texte,
            await _contenu(image, parametres),
        )
        return operations.entree(message, Auteur.CLIENT)

    @routeur.post(
        f"{prefixe}/messages/lecture",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="J'ai lu les messages de la boutique",
    )
    async def lu(
        client: Acces = Depends(acces_client), session: AsyncSession = Depends(session_db)
    ) -> None:
        await operations.marquer_lus(session, client.commande, Auteur.CLIENT)
        await session.commit()

    @routeur.post(
        f"{prefixe}/propositions/{{message_id}}/reponse",
        summary="Accepter ou refuser une proposition de la boutique",
        dependencies=[LIMITE_MESSAGES],
    )
    async def repondre(
        message_id: UUID,
        donnees: Reponse,
        request: Request,
        client: Acces = Depends(acces_client),
        session: AsyncSession = Depends(session_db),
    ) -> EntreeFil:
        message = await operations.repondre(
            session,
            _parametres(request),
            client.commande,
            message_id,
            donnees.accepte,
            compte_id=client.compte_id,
            adresse_ip=_ip(request),
        )
        return operations.entree(message, Auteur.CLIENT)

    @routeur.get(
        f"{prefixe}/messages/{{message_id}}/image",
        summary="Image jointe à un message",
        response_class=FileResponse,
        dependencies=[LIMITE_LECTURES],
    )
    async def voir(
        message_id: UUID,
        request: Request,
        client: Acces = Depends(acces_client),
        session: AsyncSession = Depends(session_db),
    ) -> FileResponse:
        return _image(
            await operations.image(session, _parametres(request), client.commande, message_id)
        )


_routes_du_client("/suivi/{reference}", par_le_lien)
_routes_du_client("/mes-commandes/{reference}", par_le_compte)


# --- L'équipe ---------------------------------------------------------------------------------

GESTION = "/admin/commandes/{reference}"


@routeur.get(f"{GESTION}/fil", summary="Le fil d'une commande, étapes internes comprises")
async def lire_en_gestion(
    reference: str, _: Principal = Depends(equipe), session: AsyncSession = Depends(session_db)
) -> Fil:
    return await operations.fil(session, await acces.charger(session, reference), Auteur.EQUIPE)


@routeur.post(
    f"{GESTION}/messages",
    status_code=status.HTTP_201_CREATED,
    summary="Écrire au client, ou lui faire une proposition à accepter",
)
async def ecrire_au_client(
    reference: str,
    request: Request,
    texte: str = Form("", max_length=TEXTE_MAX),
    proposition: bool = Form(False),
    image: UploadFile | None = File(None),
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> EntreeFil:
    parametres = _parametres(request)
    message = await operations.envoyer(
        session,
        parametres,
        await acces.charger(session, reference),
        Acteur(Auteur.EQUIPE, principal.id, principal.nom or ""),
        texte,
        await _contenu(image, parametres),
        proposition=proposition,
    )
    return operations.entree(message, Auteur.EQUIPE)


@routeur.post(
    f"{GESTION}/messages/lecture",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="L'équipe a lu les messages du client",
)
async def lu_par_l_equipe(
    reference: str, _: Principal = Depends(equipe), session: AsyncSession = Depends(session_db)
) -> None:
    await operations.marquer_lus(session, await acces.charger(session, reference), Auteur.EQUIPE)
    await session.commit()


@routeur.post(
    f"{GESTION}/messages/{{message_id}}/retrait",
    summary="Retirer un message qui n'a rien à faire ici (information de santé…)",
)
async def retirer(
    reference: str,
    message_id: UUID,
    donnees: Retrait,
    request: Request,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> EntreeFil:
    message = await operations.retirer(
        session,
        _parametres(request),
        await acces.charger(session, reference),
        message_id,
        donnees.motif,
        acteur_id=principal.id,
        adresse_ip=_ip(request),
    )
    return operations.entree(message, Auteur.EQUIPE)


@routeur.post(
    f"{GESTION}/propositions/{{message_id}}/annulation",
    summary="Annuler une proposition restée sans réponse",
)
async def annuler_proposition(
    reference: str,
    message_id: UUID,
    request: Request,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> EntreeFil:
    message = await operations.annuler_proposition(
        session,
        await acces.charger(session, reference),
        message_id,
        acteur_id=principal.id,
        adresse_ip=_ip(request),
    )
    return operations.entree(message, Auteur.EQUIPE)


@routeur.get(
    f"{GESTION}/messages/{{message_id}}/image",
    summary="Image jointe à un message",
    response_class=FileResponse,
)
async def voir_en_gestion(
    reference: str,
    message_id: UUID,
    request: Request,
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> FileResponse:
    commande = await acces.charger(session, reference)
    return _image(await operations.image(session, _parametres(request), commande, message_id))
