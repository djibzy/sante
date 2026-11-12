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
    raison: str | None  # pourquoi ce n'est pas possible, à afficher au client
    moyens: list[str]
    dernier: DernierPaiement | None


class PaiementOuvert(BaseModel):
    adresse: str  # page de paiement de l'agrégateur


class Disponibilite(BaseModel):
    disponible: bool
    moyens: list[str]
