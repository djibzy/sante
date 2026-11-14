"""SMS de la boîte d'envoi : écrits dans la même transaction que l'événement, expédiés ensuite
par le processus d'envoi (prestations.envoi). Courts, sans aucune donnée de santé.

Le SMS d'enlèvement et celui du retour servent de bon de collecte : la structure garde le
compte de ce qui est parti et de ce qui est revenu.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from prestations import calendrier
from prestations.linge import SERVICES, Article, Service, nommer
from prestations.models import Collecte, Demande, LigneCollecte, Notification
from socle.sms import gsm
from socle.telephones import afficher_telephone

DETAIL_MAX = 110  # au-delà, le détail se résume : le SMS reste en deux parties au plus


def deposer(
    session: AsyncSession, objet_type: str, objet_id: UUID, destinataire: str, texte: str
) -> None:
    session.add(
        Notification(
            objet_type=objet_type,
            objet_id=objet_id,
            destinataire=destinataire,
            message=gsm(texte),
            etat="a_envoyer",
        )
    )


def _pieces(nombre: int) -> str:
    return f"{nombre} pièce" if nombre == 1 else f"{nombre} pièces"


def _detail(quantites: list[tuple[LigneCollecte, int]]) -> str:
    """« 20 draps, 12 blouses et 10 taies d'oreiller », résumé s'il est trop long."""
    morceaux = [
        nommer(Article(ligne.article), quantite, ligne.precision)
        for ligne, quantite in sorted(quantites, key=lambda lq: -lq[1])
        if quantite
    ]
    texte = _enumerer(morceaux)
    if len(texte) > DETAIL_MAX and len(morceaux) > 3:
        reste = sum(q for _, q in sorted(quantites, key=lambda lq: -lq[1])[3:])
        texte = _enumerer([*morceaux[:3], f"{_pieces(reste)} d'autres articles"])
    return texte


def _enumerer(morceaux: list[str]) -> str:
    if len(morceaux) <= 1:
        return "".join(morceaux)
    return f"{', '.join(morceaux[:-1])} et {morceaux[-1]}"


def demande_recue(nom: str, demande: Demande) -> str:
    return (
        f"{nom} : demande {demande.reference} bien reçue "
        f"({SERVICES[Service(demande.service)].lower()}). "
        "Nous vous rappelons pour convenir d'une visite."
    )


def demande_pour_l_equipe(demande: Demande) -> str:
    volume = sum(demande.volumes.values())
    par_semaine = f", {volume} pièces/semaine" if volume else ""
    return (
        f"Nouvelle demande {demande.reference} : {demande.structure[:50]} "
        f"({demande.quartier[:30]}), {demande.contact[:40]}, "
        f"{afficher_telephone(demande.telephone)}{par_semaine}."
    )


def collecte_enlevee(nom: str, collecte: Collecte, corrigee: bool) -> str:
    total = sum(ligne.quantite_enlevee for ligne in collecte.lignes)
    accord = "collectée" if total == 1 else "collectées"
    detail = _detail([(ligne, ligne.quantite_enlevee) for ligne in collecte.lignes])
    retour = (
        f" Retour prévu {calendrier.date_courte(collecte.retour_prevu_le)}."
        if collecte.retour_prevu_le
        else ""
    )
    correction = " (comptage corrigé)" if corrigee else ""
    return (
        f"{nom} : {_pieces(total)} {accord} le {collecte.prevue_le:%d/%m}{correction}, "
        f"bon {collecte.reference} : {detail}.{retour}"
    )


def collecte_rendue(nom: str, collecte: Collecte) -> str:
    enlevees = sum(ligne.quantite_enlevee for ligne in collecte.lignes)
    rendues = sum(ligne.quantite_rendue or 0 for ligne in collecte.lignes)
    manque = [
        (ligne, ligne.quantite_enlevee - (ligne.quantite_rendue or 0))
        for ligne in collecte.lignes
        if (ligne.quantite_rendue or 0) < ligne.quantite_enlevee
    ]
    if not manque:
        if rendues == 1:
            texte = "votre pièce vous est rendue propre"
        else:
            texte = f"vos {rendues} pièces vous sont rendues propres"
        return f"{nom} : bon {collecte.reference}, {texte}. Merci de votre confiance !"
    accord = "rendue" if enlevees == 1 else "rendues"
    return (
        f"{nom} : bon {collecte.reference}, {rendues} sur {_pieces(enlevees)} {accord}. "
        f"Manque {_detail(manque)} : nous les recherchons et revenons vers vous."
    )


def manque_pour_l_equipe(collecte: Collecte) -> str:
    manque = [
        (ligne, ligne.quantite_enlevee - (ligne.quantite_rendue or 0))
        for ligne in collecte.lignes
        if (ligne.quantite_rendue or 0) < ligne.quantite_enlevee
    ]
    partenaire = f" Partenaire : {collecte.partenaire.nom[:40]}." if collecte.partenaire else ""
    return (
        f"Linge manquant au retour, bon {collecte.reference} "
        f"({collecte.contrat.structure[:40]}) : {_detail(manque)}.{partenaire}"
    )
