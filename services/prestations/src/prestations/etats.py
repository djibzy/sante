"""États des demandes, des contrats et des collectes, et passages autorisés d'une collecte."""

from enum import StrEnum


class StatutDemande(StrEnum):
    NOUVELLE = "nouvelle"
    EN_DISCUSSION = "en_discussion"  # rappelée, visite ou devis en cours
    SIGNEE = "signee"  # devenue un contrat
    SANS_SUITE = "sans_suite"


LIBELLES_DEMANDE: dict[StatutDemande, str] = {
    StatutDemande.NOUVELLE: "Nouvelle",
    StatutDemande.EN_DISCUSSION: "En discussion",
    StatutDemande.SIGNEE: "Signée",
    StatutDemande.SANS_SUITE: "Sans suite",
}


class StatutContrat(StrEnum):
    ACTIF = "actif"
    SUSPENDU = "suspendu"  # plus de collecte au calendrier, le contrat reste
    TERMINE = "termine"


class Formule(StrEnum):
    """Ce que paie la structure : chaque pièce rendue, ou un forfait mensuel (avec, au besoin,
    un volume compris et un prix par pièce au-delà)."""

    PIECE = "piece"
    FORFAIT = "forfait"


class TypePartenaire(StrEnum):
    BLANCHISSERIE = "blanchisserie"
    PRESSING = "pressing"


class ModeTarif(StrEnum):
    """Ce que nous facture le partenaire : à la pièce ou au kilo."""

    PIECE = "piece"
    KG = "kg"


class StatutCollecte(StrEnum):
    PREVUE = "prevue"  # collecte ponctuelle, demandée hors du calendrier du contrat
    ENLEVEE = "enlevee"  # comptée à la structure, en route vers le partenaire
    CHEZ_PARTENAIRE = "chez_partenaire"
    PRETE = "prete"  # lavée, à reprendre chez le partenaire
    RENDUE = "rendue"  # recomptée à la structure
    ANNULEE = "annulee"


LIBELLES_COLLECTE: dict[StatutCollecte, str] = {
    StatutCollecte.PREVUE: "Prévue",
    StatutCollecte.ENLEVEE: "Enlevée",
    StatutCollecte.CHEZ_PARTENAIRE: "Chez le partenaire",
    StatutCollecte.PRETE: "Prête chez le partenaire",
    StatutCollecte.RENDUE: "Rendue",
    StatutCollecte.ANNULEE: "Annulée",
}

PASSAGES: dict[StatutCollecte, frozenset[StatutCollecte]] = {
    StatutCollecte.PREVUE: frozenset({StatutCollecte.ENLEVEE, StatutCollecte.ANNULEE}),
    # Annuler une collecte enlevée : seulement pour corriger une saisie faite par erreur.
    StatutCollecte.ENLEVEE: frozenset({StatutCollecte.CHEZ_PARTENAIRE, StatutCollecte.ANNULEE}),
    StatutCollecte.CHEZ_PARTENAIRE: frozenset({StatutCollecte.PRETE, StatutCollecte.RENDUE}),
    StatutCollecte.PRETE: frozenset({StatutCollecte.RENDUE}),
    StatutCollecte.RENDUE: frozenset(),
    StatutCollecte.ANNULEE: frozenset(),
}

# Linge sorti de la structure et pas encore rendu.
EN_COURS = frozenset({StatutCollecte.ENLEVEE, StatutCollecte.CHEZ_PARTENAIRE, StatutCollecte.PRETE})


def passage_autorise(depuis: StatutCollecte, vers: StatutCollecte) -> bool:
    return vers in PASSAGES[depuis]
