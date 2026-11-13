"""Ce que la boutique doit rendre au client.

Elle garde le total d'une commande en cours ou remise, l'acompte gardé d'une commande annulée
(rien si la boutique a annulé), rien d'un devis refusé. Au-delà, l'argent payé est dû au
client : trop-perçu après une correction des articles, paiement en ligne arrivé après une
annulation, part de l'acompte non gardée. Un remboursement baisse le montant payé d'autant.
"""

from sqlalchemy import ColumnElement, case

from boutique.commandes.cycle import Statut
from boutique.models import Commande


def retenu(commande: Commande) -> int:
    statut = Statut(commande.statut)
    if statut == Statut.ANNULEE:
        return commande.acompte_garde
    if statut == Statut.DEVIS_REFUSE:
        return 0
    return commande.total


def du_au_client(commande: Commande) -> int:
    return max(commande.montant_paye - retenu(commande), 0)


def montant_du_sql() -> ColumnElement[int]:
    """Même règle en SQL (positif quand de l'argent reste à rendre)."""
    garde = case(
        (Commande.statut == Statut.ANNULEE, Commande.acompte_garde),
        (Commande.statut == Statut.DEVIS_REFUSE, 0),
        else_=Commande.total,
    )
    return Commande.montant_paye - garde
