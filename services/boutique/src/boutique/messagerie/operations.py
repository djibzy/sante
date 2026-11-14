"""Le fil d'une commande : écrire, proposer, accepter ou refuser, lire, retirer.

Le fil est la trace de l'affaire. Un message ne se modifie pas ; il se retire seulement s'il
contient ce qui n'a rien à faire ici, et le retrait est journalisé. Une proposition acceptée
fait foi : elle ne se retire plus.

Les SMS préviennent sans jamais porter le texte du message, et sans insister : pas de nouveau
SMS tant que le précédent, de moins d'un jour, n'a pas été suivi d'une lecture.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import ColumnElement, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from boutique import photos
from boutique.commandes.cycle import LIBELLES, Moyen, Statut
from boutique.commandes.pdf import MOYENS
from boutique.config import ParametresBoutique
from boutique.entretien import ANONYME
from boutique.messagerie import images
from boutique.messagerie.etats import LIBELLES_PROPOSITION, Auteur, EtatProposition
from boutique.messagerie.schemas import TEXTE_MAX, EntreeFil, Fil
from boutique.models import Commande, JournalAudit, Message
from boutique.notifications import boite, messages
from socle.audit import journaliser

_409 = status.HTTP_409_CONFLICT
_422 = status.HTTP_422_UNPROCESSABLE_CONTENT
RAPPEL = timedelta(hours=24)
MESSAGES_CLIENT_PAR_JOUR = 20
SANS_SUITE = (Statut.ANNULEE, Statut.DEVIS_REFUSE)
LIBELLES_MOYENS = {**MOYENS, Moyen.MOBILE_MONEY: "paiement mobile"}


@dataclass(frozen=True)
class Acteur:
    auteur: Auteur
    compte_id: UUID | None = None
    nom: str = ""  # membre de l'équipe


def _maintenant() -> datetime:
    return datetime.now(UTC)


def ouvert(commande: Commande) -> bool:
    """Une commande anonymisée (durée de conservation écoulée) n'a plus de fil."""
    return commande.telephone != ANONYME


def _exiger_ouvert(commande: Commande) -> None:
    if not ouvert(commande):
        raise HTTPException(_409, "Cette commande est archivée : son fil est fermé")


def _autre(auteur: Auteur) -> Auteur:
    return Auteur.EQUIPE if auteur == Auteur.CLIENT else Auteur.CLIENT


async def _message(
    session: AsyncSession, commande: Commande, message_id: UUID, *, verrou: bool = False
) -> Message:
    requete = select(Message).where(Message.id == message_id, Message.commande_id == commande.id)
    if verrou:
        requete = requete.with_for_update()
    message = await session.scalar(requete)
    if message is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message introuvable")
    return message


def entree(message: Message, pour: Auteur) -> EntreeFil:
    etat = EtatProposition(message.etat) if message.etat else None
    return EntreeFil(
        type="proposition" if etat else "message",
        quand=message.cree_le,
        id=message.id,
        auteur=Auteur(message.auteur),
        nom_auteur=message.nom_auteur if pour == Auteur.EQUIPE else "",
        texte=message.texte,
        image=message.image is not None,
        etat=etat,
        libelle_etat=LIBELLES_PROPOSITION[etat] if etat else "",
        repondue_le=message.repondue_le,
        lu_le=message.lu_le,
        retire=message.retire_le is not None,
        motif_retrait=message.motif_retrait,
    )


async def fil(session: AsyncSession, commande: Commande, pour: Auteur) -> Fil:
    """Messages, étapes et paiements de la commande, dans l'ordre. Le client ne voit ni les
    étapes internes ni le motif d'un remboursement."""
    lus = list(
        await session.scalars(
            select(Message).where(Message.commande_id == commande.id).order_by(Message.cree_le)
        )
    )
    entrees = [entree(message, pour) for message in lus]
    entrees += [
        EntreeFil(
            type="etape",
            quand=evenement.cree_le,
            libelle=LIBELLES[Statut(evenement.statut)],
            note=evenement.note,
            interne=not evenement.visible_client,
        )
        for evenement in commande.evenements
        if evenement.visible_client or pour == Auteur.EQUIPE
    ]
    entrees += [
        EntreeFil(
            type="paiement",
            quand=paiement.encaisse_le,
            libelle=f"Paiement reçu ({LIBELLES_MOYENS[Moyen(paiement.moyen)]})",
            montant=paiement.montant,
        )
        for paiement in commande.paiements
    ]
    entrees += [
        EntreeFil(
            type="remboursement",
            quand=rendu.rembourse_le,
            libelle=f"Remboursement ({LIBELLES_MOYENS[Moyen(rendu.moyen)]})",
            note=rendu.motif if pour == Auteur.EQUIPE else "",
            montant=rendu.montant,
        )
        for rendu in commande.remboursements
    ]
    entrees.sort(key=lambda e: e.quand)
    return Fil(
        reference=commande.reference,
        ouvert=ouvert(commande),
        entrees=entrees,
        a_lire=sum(
            1 for m in lus if m.auteur == _autre(pour) and m.lu_le is None and m.retire_le is None
        ),
        propositions_en_attente=sum(1 for m in lus if m.etat == EtatProposition.EN_ATTENTE),
    )


def a_lire_sql(lecteur: Auteur) -> ColumnElement[bool]:
    """Condition SQL : la commande a un message de l'autre partie que le lecteur n'a pas lu."""
    return exists().where(
        Message.commande_id == Commande.id,
        Message.auteur == _autre(lecteur),
        Message.lu_le.is_(None),
        Message.retire_le.is_(None),
    )


async def a_lire(session: AsyncSession, commandes: list[UUID], lecteur: Auteur) -> dict[UUID, int]:
    """Nombre de messages à lire par commande, pour une page de la file."""
    if not commandes:
        return {}
    lignes = await session.execute(
        select(Message.commande_id, func.count(Message.id))
        .where(
            Message.commande_id.in_(commandes),
            Message.auteur == _autre(lecteur),
            Message.lu_le.is_(None),
            Message.retire_le.is_(None),
        )
        .group_by(Message.commande_id)
    )
    return {commande_id: nombre for commande_id, nombre in lignes}


async def marquer_lus(session: AsyncSession, commande: Commande, lecteur: Auteur) -> None:
    """Le lecteur a le fil sous les yeux : les messages de l'autre partie sont lus."""
    await session.execute(
        update(Message)
        .where(
            Message.commande_id == commande.id,
            Message.auteur == _autre(lecteur),
            Message.lu_le.is_(None),
        )
        .values(lu_le=_maintenant())
    )


async def _deja_prevenu(session: AsyncSession, commande: Commande, auteur: Auteur) -> bool:
    """L'autre partie a reçu, il y a moins d'un jour, un SMS pour un message de cet auteur
    qu'elle n'a pas encore lu : un second SMS n'apprendrait rien."""
    dernier = await session.scalar(
        select(func.max(Message.cree_le)).where(
            Message.commande_id == commande.id,
            Message.auteur == auteur,
            Message.notifie,
            Message.lu_le.is_(None),
            Message.retire_le.is_(None),
        )
    )
    return dernier is not None and dernier > _maintenant() - RAPPEL


async def envoyer(
    session: AsyncSession,
    parametres: ParametresBoutique,
    commande: Commande,
    acteur: Acteur,
    texte: str,
    image: bytes | None = None,
    *,
    proposition: bool = False,
) -> Message:
    _exiger_ouvert(commande)
    texte = texte.strip()
    if len(texte) > TEXTE_MAX:
        raise HTTPException(_422, f"Message trop long : {TEXTE_MAX} caractères au plus")
    if proposition and len(texte) < 5:
        raise HTTPException(_422, "Écrivez la proposition que le client acceptera")
    if not texte and image is None:
        raise HTTPException(_422, "Écrivez un message ou joignez une image")
    if acteur.auteur == Auteur.CLIENT:
        recents = await session.scalar(
            select(func.count(Message.id)).where(
                Message.commande_id == commande.id,
                Message.auteur == Auteur.CLIENT,
                Message.cree_le > _maintenant() - RAPPEL,
            )
        )
        if (recents or 0) >= MESSAGES_CLIENT_PAR_JOUR:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Beaucoup de messages aujourd'hui : appelez-nous si c'est urgent.",
            )
    dossier = Path(parametres.dossier_medias)
    nom_image: str | None = None
    if image is not None:
        try:
            nom_image = await run_in_threadpool(images.enregistrer, image, dossier)
        except photos.PhotoRefusee as exc:
            raise HTTPException(_422, str(exc)) from exc
    message = Message(
        commande_id=commande.id,
        auteur=acteur.auteur,
        auteur_id=acteur.compte_id,
        nom_auteur=acteur.nom if acteur.auteur == Auteur.EQUIPE else "",
        texte=texte,
        image=nom_image,
        etat=EtatProposition.EN_ATTENTE if proposition else None,
        cree_le=_maintenant(),
    )
    try:
        if acteur.auteur == Auteur.EQUIPE:
            # Une proposition attend une réponse : le client en est toujours prévenu.
            if proposition or not await _deja_prevenu(session, commande, Auteur.EQUIPE):
                boite.deposer(
                    session,
                    commande,
                    messages.proposition(commande)
                    if proposition
                    else messages.nouveau_message(commande),
                )
                message.notifie = True
        elif parametres.telephones_equipe and not await _deja_prevenu(
            session, commande, Auteur.CLIENT
        ):
            for numero in parametres.telephones_equipe:
                boite.deposer(session, commande, messages.message_pour_l_equipe(commande), numero)
            message.notifie = True
        session.add(message)
        # Écrire, c'est avoir lu ce qui précède.
        await marquer_lus(session, commande, acteur.auteur)
        await session.commit()
    except Exception:
        images.supprimer(dossier, nom_image)
        raise
    return message


async def repondre(
    session: AsyncSession,
    parametres: ParametresBoutique,
    commande: Commande,
    message_id: UUID,
    accepte: bool,
    *,
    compte_id: UUID | None,
    adresse_ip: str | None,
) -> Message:
    """Le client accepte ou refuse une proposition : daté, journalisé, définitif."""
    _exiger_ouvert(commande)
    if commande.statut in SANS_SUITE:
        raise HTTPException(_409, "Commande annulée : il n'y a plus rien à accepter")
    message = await _message(session, commande, message_id, verrou=True)
    if message.etat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message introuvable")
    if message.etat != EtatProposition.EN_ATTENTE:
        libelle = LIBELLES_PROPOSITION[EtatProposition(message.etat)].lower()
        raise HTTPException(_409, f"Proposition déjà close ({libelle})")
    maintenant = _maintenant()
    message.etat = EtatProposition.ACCEPTEE if accepte else EtatProposition.REFUSEE
    message.repondue_le = maintenant
    message.lu_le = message.lu_le or maintenant
    journaliser(
        session,
        JournalAudit,
        action="proposition.acceptee" if accepte else "proposition.refusee",
        acteur_id=compte_id,
        objet_type="commande",
        objet_id=commande.reference,
        details={
            "message": str(message.id),
            "par": "compte du client" if compte_id else "lien de suivi",
        },
        adresse_ip=adresse_ip,
    )
    for numero in parametres.telephones_equipe:
        boite.deposer(session, commande, messages.reponse_pour_l_equipe(commande, accepte), numero)
    await session.commit()
    return message


async def annuler_proposition(
    session: AsyncSession,
    commande: Commande,
    message_id: UUID,
    *,
    acteur_id: UUID,
    adresse_ip: str | None,
) -> Message:
    """L'équipe retire du jeu une proposition sans réponse (pour la corriger) : son texte
    reste dans le fil, le client ne peut plus l'accepter."""
    message = await _message(session, commande, message_id, verrou=True)
    if message.etat != EtatProposition.EN_ATTENTE:
        raise HTTPException(_409, "Seule une proposition sans réponse s'annule")
    message.etat = EtatProposition.ANNULEE
    message.repondue_le = _maintenant()
    journaliser(
        session,
        JournalAudit,
        action="proposition.annulee",
        acteur_id=acteur_id,
        objet_type="commande",
        objet_id=commande.reference,
        details={"message": str(message.id)},
        adresse_ip=adresse_ip,
    )
    await session.commit()
    return message


async def retirer(
    session: AsyncSession,
    parametres: ParametresBoutique,
    commande: Commande,
    message_id: UUID,
    motif: str,
    *,
    acteur_id: UUID,
    adresse_ip: str | None,
) -> Message:
    """Retire un message qui contient ce qui n'a rien à faire ici (une information de santé) :
    texte et image disparaissent ; restent l'auteur, la date, le motif et qui l'a retiré."""
    message = await _message(session, commande, message_id, verrou=True)
    if message.retire_le is not None:
        raise HTTPException(_409, "Message déjà retiré")
    if message.etat == EtatProposition.ACCEPTEE:
        raise HTTPException(_409, "Une proposition acceptée fait foi : elle ne se retire pas")
    image = message.image
    message.texte = ""
    message.image = None
    message.retire_le = _maintenant()
    message.retire_par = acteur_id
    message.motif_retrait = motif.strip()
    if message.etat == EtatProposition.EN_ATTENTE:
        message.etat = EtatProposition.ANNULEE
        message.repondue_le = message.retire_le
    journaliser(
        session,
        JournalAudit,
        action="message.retire",
        acteur_id=acteur_id,
        objet_type="commande",
        objet_id=commande.reference,
        details={"message": str(message.id), "auteur": message.auteur, "motif": motif.strip()},
        adresse_ip=adresse_ip,
    )
    await session.commit()
    images.supprimer(Path(parametres.dossier_medias), image)
    return message


async def image(
    session: AsyncSession, parametres: ParametresBoutique, commande: Commande, message_id: UUID
) -> Path:
    message = await _message(session, commande, message_id)
    fichier = (
        images.chemin(Path(parametres.dossier_medias), message.image) if message.image else None
    )
    if fichier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image introuvable")
    return fichier
