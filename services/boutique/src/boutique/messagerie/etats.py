"""Qui écrit dans le fil d'une commande, et où en est une proposition."""

from enum import StrEnum


class Auteur(StrEnum):
    CLIENT = "client"
    EQUIPE = "equipe"


class EtatProposition(StrEnum):
    """Une proposition est un message de l'équipe que le client accepte ou refuse en un clic."""

    EN_ATTENTE = "en_attente"
    ACCEPTEE = "acceptee"  # fait foi : ne se retire plus
    REFUSEE = "refusee"
    ANNULEE = "annulee"  # retirée du jeu par l'équipe avant la réponse (remplacée, corrigée)


LIBELLES_PROPOSITION: dict[EtatProposition, str] = {
    EtatProposition.EN_ATTENTE: "En attente de votre réponse",
    EtatProposition.ACCEPTEE: "Acceptée",
    EtatProposition.REFUSEE: "Refusée",
    EtatProposition.ANNULEE: "Annulée par la boutique",
}
