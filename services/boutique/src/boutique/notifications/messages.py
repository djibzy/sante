"""Textes des SMS envoyés aux clients, courts et sans aucune donnée de santé.

Les SMS restent dans l'alphabet GSM (160 caractères par message) : les lettres qui n'y sont
pas (ê, ô, î, ç…) sont remplacées, sans quoi chaque SMS coûterait deux à trois fois plus.
"""

from boutique.commandes.cycle import ModeLivraison, Statut
from boutique.models import Commande
from socle.telephones import afficher_telephone

_HORS_GSM = str.maketrans(
    {
        "ê": "e", "ë": "e", "î": "i", "ï": "i", "ô": "o", "û": "u", "ü": "u", "â": "a",
        "ç": "c", "È": "E", "Ê": "E", "À": "A", "Â": "A", "Î": "I", "Ô": "O", "Û": "U",
        "œ": "oe", "Œ": "OE", "’": "'", "«": '"', "»": '"', " ": " ", " ": " ",
        "–": "-", "—": "-", "…": "...",
    }
)  # fmt: skip


def gsm(texte: str) -> str:
    return texte.translate(_HORS_GSM)


def _fcfa(montant: int) -> str:
    return f"{montant:,}".replace(",", " ") + " FCFA"


def creation(commande: Commande, lien: str | None) -> str:
    suivi = f" Suivi : {lien}" if lien else ""
    if commande.statut == Statut.DEVIS_DEMANDE:
        texte = f"Bibou : demande de devis {commande.reference} reçue. Nous vous appelons.{suivi}"
    else:
        texte = (
            f"Bibou : commande {commande.reference} reçue ({_fcfa(commande.total)}). "
            f"Nous vous appelons pour la confirmer.{suivi}"
        )
    return gsm(texte)


def changement(commande: Commande, statut: Statut) -> str | None:
    """Texte du SMS pour un changement de statut, ou rien quand le client n'a pas à être
    dérangé (préparation, étapes internes)."""
    ref, reste = commande.reference, _fcfa(commande.reste_a_payer)
    date = commande.date_promise.strftime("%d/%m") if commande.date_promise else None
    retrait = commande.mode_livraison == ModeLivraison.RETRAIT
    textes: dict[Statut, str | None] = {
        Statut.DEVIS_ENVOYE: (
            f"Bibou : votre devis {ref} est prêt ({_fcfa(commande.total)}). Ouvrez le lien "
            "reçu lors de votre demande pour le consulter et l'accepter."
        ),
        Statut.CONFIRMEE: f"Bibou : commande {ref} confirmée"
        + (f", prête vers le {date}." if date else "."),
        Statut.PRETE: f"Bibou : commande {ref} prête. Venez la retirer à la boutique. "
        f"A payer : {reste}."
        if retrait
        else None,
        Statut.EN_LIVRAISON: f"Bibou : commande {ref} en route"
        + (
            f" avec {commande.livreur.nom} ({afficher_telephone(commande.livreur.telephone)})"
            if commande.livreur
            else ""
        )
        + f". A payer : {reste}.",
        Statut.LIVREE: f"Bibou : commande {ref} remise. Merci de votre confiance ! "
        "Donnez votre avis depuis votre lien de suivi.",
        Statut.ANNULEE: f"Bibou : commande {ref} annulée. Une question ? Appelez-nous.",
    }
    texte = textes.get(statut)
    return gsm(texte) if texte else None


def paiement_recu(commande: Commande, montant: int) -> str:
    reste = commande.reste_a_payer
    suite = (
        "Commande entièrement payée, merci !" if reste == 0 else f"Reste à payer : {_fcfa(reste)}."
    )
    return gsm(
        f"Bibou : paiement de {_fcfa(montant)} reçu pour la commande {commande.reference}. {suite}"
    )


def pour_l_equipe(commande: Commande, zone: str | None) -> str:
    """Alerte à l'équipe : de quoi juger l'urgence sans ouvrir l'écran (aucun nom ni numéro)."""
    if commande.statut == Statut.DEVIS_DEMANDE:
        pour = f" ({commande.etablissement})" if commande.etablissement else ""
        texte = f"Bibou : demande de devis {commande.reference}{pour}. A traiter dans Gestion."
    else:
        remise = f"livraison {zone}" if zone else "retrait en boutique"
        texte = (
            f"Bibou : nouvelle commande {commande.reference}, {_fcfa(commande.total)}, {remise}. "
            "A confirmer dans Gestion."
        )
    return gsm(texte)
