"""Conversion des produits en réponses publiques.

Les prix des articles du domaine pharmaceutique ne sont jamais affichés : ils sont vendus
sur demande par le pharmacien partenaire.
"""

from boutique.models import Produit
from boutique.schemas import ImagePublique, ProduitDetail, ProduitResume, VariantePublique


def _prix_visible(produit: Produit, prix: int | None) -> int | None:
    return prix if produit.vendable_en_ligne else None


def vers_resume(produit: Produit) -> ProduitResume:
    image = produit.images[0] if produit.images else None
    return ProduitResume(
        id=produit.id,
        slug=produit.slug,
        nom=produit.nom,
        resume=produit.resume,
        rayon_slug=produit.rayon.slug,
        rayon_nom=produit.rayon.nom,
        categorie_reglementaire=produit.categorie_reglementaire,
        vendable_en_ligne=produit.vendable_en_ligne,
        personnalisable=produit.personnalisable,
        prix_public=_prix_visible(produit, produit.prix_public),
        prix_pro=_prix_visible(produit, produit.prix_pro),
        image=ImagePublique(url=image.url, texte_alternatif=image.texte_alternatif)
        if image
        else None,
    )


def vers_detail(produit: Produit) -> ProduitDetail:
    variantes = [
        VariantePublique(
            id=v.id,
            sku=v.sku,
            libelle=v.libelle,
            taille=v.taille,
            couleur=v.couleur,
            prix=_prix_visible(produit, v.prix if v.prix is not None else produit.prix_public),
        )
        for v in produit.variantes
        if v.est_active
    ]
    return ProduitDetail(
        **vers_resume(produit).model_dump(),
        description=produit.description,
        delai_jours=produit.delai_jours,
        variantes=variantes,
        images=[
            ImagePublique(url=i.url, texte_alternatif=i.texte_alternatif) for i in produit.images
        ],
    )
