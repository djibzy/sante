"""Acompte des articles faits à la demande.

Un article brodé à votre nom, ou fabriqué par l'atelier, ne se revend pas : la fabrication ne
commence qu'une fois l'acompte payé (statut « En attente de l'acompte »), et l'acompte reste
acquis si le client annule ensuite. Ce qui a été payé au-delà de l'acompte lui est rendu, et
tout lui est rendu si l'annulation vient de la boutique.
"""

import math
from collections.abc import Iterable
from uuid import UUID

from boutique.commandes.tarifs import LigneTarifee
from boutique.config import ParametresBoutique
from boutique.models import Commande, LigneCommande, Produit

ARRONDI = 100  # FCFA


def a_la_demande(poste: str | None, personnalisation: str | None, postes: list[str]) -> bool:
    return poste in postes or bool(personnalisation and personnalisation.strip())


def calculer(montant_a_la_demande: int, total: int, pourcent: int) -> int:
    """Pourcentage du prix des articles faits à la demande, arrondi à la centaine supérieure,
    jamais plus que le total."""
    if pourcent <= 0 or montant_a_la_demande <= 0:
        return 0
    return min(total, math.ceil(montant_a_la_demande * pourcent / 100 / ARRONDI) * ARRONDI)


def pour_panier(lignes: Iterable[LigneTarifee], total: int, regle: ParametresBoutique) -> int:
    montant = sum(
        ligne.montant
        for ligne in lignes
        if ligne.commandable
        and a_la_demande(ligne.poste, ligne.personnalisation, regle.acompte_postes)
    )
    return calculer(montant, total, regle.acompte_pourcent)


def pour_lignes(
    lignes: Iterable[LigneCommande],
    produits: dict[UUID, Produit],
    total: int,
    regle: ParametresBoutique,
) -> int:
    """Lignes d'une commande ou d'un devis (lignes libres : à la demande si personnalisées)."""
    montant = 0
    for ligne in lignes:
        produit = produits.get(ligne.produit_id) if ligne.produit_id else None
        poste = produit.poste_atelier if produit else None
        if a_la_demande(poste, ligne.personnalisation, regle.acompte_postes):
            montant += ligne.montant
    return calculer(montant, total, regle.acompte_pourcent)


def restant(commande: Commande) -> int:
    """Ce qu'il reste à payer de l'acompte."""
    return max(commande.acompte - commande.montant_paye, 0)


def a_garder(commande: Commande) -> int:
    """Ce que la boutique garde si le client annule : ce qu'il a payé, dans la limite de
    l'acompte."""
    return min(commande.montant_paye, commande.acompte)


def a_rendre(commande: Commande) -> int:
    """Commande annulée : ce qui revient au client (tout ce qui n'est pas l'acompte gardé)."""
    return commande.montant_paye - commande.acompte_garde
