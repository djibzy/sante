"""États d'un ordre de fabrication et motifs des mouvements de stock."""

from enum import StrEnum


class EtatOrdre(StrEnum):
    A_FAIRE = "a_faire"
    EN_COURS = "en_cours"
    CONTROLE = "controle"  # contrôle qualité : broderie lisible, orthographe du nom…
    TERMINE = "termine"
    ANNULE = "annule"


LIBELLES_ORDRE: dict[EtatOrdre, str] = {
    EtatOrdre.A_FAIRE: "À faire",
    EtatOrdre.EN_COURS: "En cours",
    EtatOrdre.CONTROLE: "Contrôle",
    EtatOrdre.TERMINE: "Terminé",
    EtatOrdre.ANNULE: "Annulé",
}

PASSAGES_ORDRE: dict[EtatOrdre, frozenset[EtatOrdre]] = {
    EtatOrdre.A_FAIRE: frozenset({EtatOrdre.EN_COURS}),
    EtatOrdre.EN_COURS: frozenset({EtatOrdre.CONTROLE, EtatOrdre.A_FAIRE}),
    # Un défaut au contrôle renvoie la pièce en fabrication.
    EtatOrdre.CONTROLE: frozenset({EtatOrdre.TERMINE, EtatOrdre.EN_COURS}),
    EtatOrdre.TERMINE: frozenset(),
    EtatOrdre.ANNULE: frozenset(),
}

OUVERTS = frozenset({EtatOrdre.A_FAIRE, EtatOrdre.EN_COURS, EtatOrdre.CONTROLE})


class MotifStock(StrEnum):
    RECEPTION = "reception"  # arrivage fournisseur
    VENTE = "vente"  # prélevé pour une commande prête
    ANNULATION = "annulation"  # remis en stock après l'annulation d'une commande prélevée
    INVENTAIRE = "inventaire"  # écart constaté au comptage
    PERTE = "perte"  # casse, vol, péremption
    RETOUR = "retour"  # article rapporté par un client
