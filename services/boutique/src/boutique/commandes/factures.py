"""Factures : numérotation continue par année, sans trou ni doublon.

Le compteur de l'année est verrouillé (SELECT … FOR UPDATE) dans la transaction qui émet la
facture : si cette transaction échoue, le numéro n'est pas consommé.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.commandes.tarifs import aujourd_hui
from boutique.models import Commande, CompteurFactures, Facture


async def emettre(session: AsyncSession, commande: Commande, acteur_id: UUID | None) -> Facture:
    """Émet la facture de la commande, ou renvoie celle qui existe déjà."""
    existante = await session.scalar(select(Facture).where(Facture.commande_id == commande.id))
    if existante is not None:
        return existante
    annee = aujourd_hui().year
    await session.execute(
        insert(CompteurFactures).values(annee=annee, dernier=0).on_conflict_do_nothing()
    )
    compteur = await session.scalar(
        select(CompteurFactures).where(CompteurFactures.annee == annee).with_for_update()
    )
    assert compteur is not None
    compteur.dernier += 1
    facture = Facture(
        commande_id=commande.id,
        annee=annee,
        numero=compteur.dernier,
        montant=commande.total,
        emise_par=acteur_id,
    )
    session.add(facture)
    await session.flush()
    return facture
