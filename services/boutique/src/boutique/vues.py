"""Mise en forme des produits pour l'API publique (prix masqués pour le pharmaceutique)."""

from boutique.models import Produit
from boutique.schemas import Couleur, ImagePublique, ProduitDetail, ProduitResume, VariantePublique

ORDRE_TAILLES = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "4XL"]


def rang_taille(taille: str) -> tuple[int, float, str]:
    """XS < S < M … puis les pointures dans l'ordre des nombres."""
    if taille in ORDRE_TAILLES:
        return (0, ORDRE_TAILLES.index(taille), taille)
    try:
        return (1, float(taille.replace(",", ".")), taille)
    except ValueError:
        return (2, 0, taille)


def _prix_visible(produit: Produit, prix: int | None) -> int | None:
    return prix if produit.vendable_en_ligne else None


def vers_resume(produit: Produit) -> ProduitResume:
    image = produit.images[0] if produit.images else None
    actives = [v for v in produit.variantes if v.est_active]
    couleurs: dict[str, str | None] = {}
    for variante in actives:
        if variante.couleur and variante.couleur not in couleurs:
            couleurs[variante.couleur] = variante.couleur_hex
    tailles = sorted({v.taille for v in actives if v.taille}, key=rang_taille)
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
        prix_avant_promo=_prix_visible(produit, produit.prix_avant_promo),
        image=ImagePublique(url=image.url, texte_alternatif=image.texte_alternatif)
        if image
        else None,
        genre=produit.genre,
        metiers=produit.metiers,
        collection=produit.collection,
        est_nouveau=produit.est_nouveau,
        couleurs=[Couleur(nom=nom, hex=teinte) for nom, teinte in couleurs.items()],
        tailles=tailles,
        delai_jours=produit.delai_jours,
        fabrique_sur_commande=produit.poste_atelier is not None,
        note_moyenne=round(produit.somme_notes / produit.nombre_avis, 1)
        if produit.nombre_avis
        else None,
        nombre_avis=produit.nombre_avis,
    )


def vers_detail(produit: Produit) -> ProduitDetail:
    variantes = [
        VariantePublique(
            id=v.id,
            sku=v.sku,
            libelle=v.libelle,
            taille=v.taille,
            couleur=v.couleur,
            couleur_hex=v.couleur_hex,
            prix=_prix_visible(produit, v.prix if v.prix is not None else produit.prix_public),
        )
        for v in produit.variantes
        if v.est_active
    ]
    return ProduitDetail(
        **vers_resume(produit).model_dump(),
        description=produit.description,
        manches=produit.manches,
        matiere=produit.matiere,
        entretien=produit.entretien,
        variantes=variantes,
        images=[
            ImagePublique(url=i.url, texte_alternatif=i.texte_alternatif) for i in produit.images
        ],
    )
