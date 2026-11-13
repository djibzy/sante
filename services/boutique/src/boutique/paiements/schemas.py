from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DernierPaiement(BaseModel):
    """Dernière tentative de paiement en ligne, telle que le client la voit."""

    statut: Literal["en_cours", "acceptee", "refusee", "a_verifier"]
    montant: int
    cree_le: datetime


class EtatPaiement(BaseModel):
    disponible: bool  # la boutique a ouvert le paiement en ligne
    possible: bool  # cette commande peut être payée en ligne maintenant
    montant: int  # ce que le client paierait : le reste à payer
    acompte: int | None = None  # en attente de l'acompte : payer l'acompte seulement
    raison: str | None  # pourquoi ce n'est pas possible, à afficher au client
    moyens: list[str]
    dernier: DernierPaiement | None


class PaiementOuvert(BaseModel):
    adresse: str  # page de paiement de l'agrégateur


class Disponibilite(BaseModel):
    disponible: bool
    moyens: list[str]


class LienDePaiement(BaseModel):
    """Lien à envoyer à un proche : il voit le montant dû et paie, rien d'autre."""

    adresse: str
    cle: str


class ArticleAPayer(BaseModel):
    libelle: str
    quantite: int


class CommandeAPayer(BaseModel):
    """Ce qu'un proche voit avec le lien de paiement : de quoi payer en confiance, sans le
    téléphone, l'adresse, le texte brodé ni l'historique du client."""

    reference: str
    statut_libelle: str
    pour: str  # prénom et initiale du nom
    articles: list[ArticleAPayer]
    total: int
    montant_paye: int
    reste_a_payer: int
    acompte_restant: int


class ChoixPaiement(BaseModel):
    objet: Literal["acompte", "solde"] = "solde"
