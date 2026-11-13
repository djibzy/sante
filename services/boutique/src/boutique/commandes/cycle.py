"""Cycle de vie d'une commande, ou d'un devis qui devient une commande une fois accepté.

Chaque passage d'un statut à l'autre est daté dans l'historique de la commande ; seuls les
passages listés dans PASSAGES sont autorisés.
"""

from enum import StrEnum


class Statut(StrEnum):
    DEVIS_DEMANDE = "devis_demande"
    DEVIS_ENVOYE = "devis_envoye"
    DEVIS_REFUSE = "devis_refuse"
    EN_ATTENTE = "en_attente"
    # Articles faits à la demande : la fabrication attend l'acompte (voir commandes.acompte).
    ACOMPTE_ATTENDU = "acompte_attendu"
    CONFIRMEE = "confirmee"
    EN_PREPARATION = "en_preparation"
    PRETE = "prete"
    EN_LIVRAISON = "en_livraison"
    LIVREE = "livree"
    ANNULEE = "annulee"


LIBELLES: dict[Statut, str] = {
    Statut.DEVIS_DEMANDE: "Devis demandé",
    Statut.DEVIS_ENVOYE: "Devis envoyé",
    Statut.DEVIS_REFUSE: "Devis refusé",
    Statut.EN_ATTENTE: "Reçue, à confirmer",
    Statut.ACOMPTE_ATTENDU: "En attente de l'acompte",
    Statut.CONFIRMEE: "Confirmée",
    Statut.EN_PREPARATION: "En préparation",
    Statut.PRETE: "Prête",
    Statut.EN_LIVRAISON: "En livraison",
    Statut.LIVREE: "Livrée",
    Statut.ANNULEE: "Annulée",
}

PASSAGES: dict[Statut, frozenset[Statut]] = {
    Statut.DEVIS_DEMANDE: frozenset({Statut.DEVIS_ENVOYE, Statut.ANNULEE}),
    Statut.DEVIS_ENVOYE: frozenset({Statut.CONFIRMEE, Statut.DEVIS_REFUSE, Statut.ANNULEE}),
    Statut.DEVIS_REFUSE: frozenset(),
    # Confirmer une commande qui demande un acompte la met « en attente de l'acompte » ; elle est
    # confirmée quand il est payé, ou plus tôt si l'équipe lance la fabrication sans l'attendre.
    Statut.EN_ATTENTE: frozenset({Statut.CONFIRMEE, Statut.ANNULEE}),
    Statut.ACOMPTE_ATTENDU: frozenset({Statut.CONFIRMEE, Statut.ANNULEE}),
    Statut.CONFIRMEE: frozenset({Statut.EN_PREPARATION, Statut.PRETE, Statut.ANNULEE}),
    Statut.EN_PREPARATION: frozenset({Statut.PRETE, Statut.ANNULEE}),
    Statut.PRETE: frozenset({Statut.EN_LIVRAISON, Statut.LIVREE, Statut.ANNULEE}),
    # Livraison manquée (client absent) : la commande revient à « Prête ».
    Statut.EN_LIVRAISON: frozenset({Statut.LIVREE, Statut.PRETE}),
    Statut.LIVREE: frozenset(),
    Statut.ANNULEE: frozenset(),
}

# Statuts que le client peut encore annuler lui-même, depuis son lien de suivi.
ANNULABLES_PAR_CLIENT = frozenset(
    {Statut.DEVIS_DEMANDE, Statut.DEVIS_ENVOYE, Statut.EN_ATTENTE, Statut.ACOMPTE_ATTENDU}
)
# Demandes pas encore traitées par l'équipe : limitées par numéro de téléphone.
EN_ATTENTE_DE_L_EQUIPE = frozenset({Statut.DEVIS_DEMANDE, Statut.EN_ATTENTE})


class ModeLivraison(StrEnum):
    RETRAIT = "retrait"
    LIVRAISON = "livraison"


class ModePaiement(StrEnum):
    # Espèces ou paiement mobile à la remise ; le paiement mobile en ligne viendra ensuite.
    A_LA_LIVRAISON = "a_la_livraison"


class Moyen(StrEnum):
    """Moyen d'encaissement : enregistré par l'équipe, ou payé en ligne par le client."""

    ESPECES = "especes"
    ORANGE_MONEY = "orange_money"
    MOOV_MONEY = "moov_money"
    MOBILE_MONEY = "mobile_money"  # paiement en ligne dont l'opérateur n'est pas reconnu
    VIREMENT = "virement"
    CHEQUE = "cheque"


def passage_autorise(depart: str, arrivee: str) -> bool:
    return Statut(arrivee) in PASSAGES[Statut(depart)]


def valeurs_sql(enumeration: type[StrEnum]) -> str:
    """« 'a', 'b' » : la liste des valeurs, pour les contraintes CHECK."""
    return ", ".join(f"'{membre.value}'" for membre in enumeration)
