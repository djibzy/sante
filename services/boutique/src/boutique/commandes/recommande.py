"""« Commander à nouveau » : les articles d'une commande passée, prêts pour le panier.

Le serveur décide de ce qui revient au panier : article toujours vendu en ligne, même taille
et même couleur toujours proposées. Le reste est écarté avec sa raison. Les prix sont ceux du
jour, indicatifs : le panier est de toute façon rechiffré par le serveur.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from boutique.commandes.schemas import ARecommander, LigneARecommander
from boutique.commandes.tarifs import prix_catalogue
from boutique.models import Commande, Produit


async def a_recommander(
    session: AsyncSession, commande: Commande, professionnel: bool
) -> ARecommander:
    ids = {ligne.produit_id for ligne in commande.lignes if ligne.produit_id}
    produits = {
        p.id: p
        for p in await session.scalars(
            select(Produit)
            .where(Produit.id.in_(ids))
            .options(selectinload(Produit.rayon), selectinload(Produit.variantes))
        )
    }
    lignes: list[LigneARecommander] = []
    ecartes: list[str] = []
    for ligne in commande.lignes:
        produit = produits.get(ligne.produit_id) if ligne.produit_id else None
        if produit is None:
            ecartes.append(f"{ligne.libelle} : ligne sur mesure, à redemander à l'équipe")
            continue
        if not produit.est_actif or not produit.vendable_en_ligne:
            ecartes.append(f"{ligne.libelle} : n'est plus vendu en ligne")
            continue
        variante = next((v for v in produit.variantes if v.id == ligne.variante_id), None)
        actives = [v for v in produit.variantes if v.est_active]
        if (variante is not None and not variante.est_active) or (variante is None and actives):
            ecartes.append(f"{ligne.libelle} : taille ou couleur à choisir de nouveau sur la fiche")
            continue
        lignes.append(
            LigneARecommander(
                produit_id=produit.id,
                variante_id=variante.id if variante else None,
                quantite=ligne.quantite,
                personnalisation=ligne.personnalisation if produit.personnalisable else None,
                slug=produit.slug,
                nom=produit.nom,
                variante=variante.libelle if variante else None,
                rayon_slug=produit.rayon.slug,
                prix_indicatif=prix_catalogue(produit, variante, professionnel),
            )
        )
    return ARecommander(lignes=lignes, ecartes=ecartes)
