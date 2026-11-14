"""Point d'entrée : uvicorn boutique.main:creer_app --factory"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from boutique import photos
from boutique.config import ParametresBoutique
from boutique.paiements.fournisseurs import configuration_incomplete
from boutique.routes import (
    admin,
    atelier,
    avis,
    catalogue,
    catalogue_gestion,
    codes_promo,
    commandes,
    explorer,
    exports,
    gestion,
    mes_donnees,
    messagerie,
    paiements,
    stock,
    tableau,
    tenues,
)
from socle.application import creer_application


def creer_app(parametres: ParametresBoutique | None = None) -> FastAPI:
    p = parametres or ParametresBoutique()
    application = creer_application(
        service="boutique",
        titre="Boutique : catalogue et commandes",
        parametres=p,
        routeurs=[
            catalogue.routeur,
            explorer.routeur,
            tenues.routeur,
            commandes.routeur,
            messagerie.routeur,
            paiements.routeur,
            avis.routeur,
            mes_donnees.routeur,
            admin.routeur,
            catalogue_gestion.routeur,
            codes_promo.routeur,
            gestion.routeur,
            avis.routeur_equipe,
            atelier.routeur,
            stock.routeur,
            tableau.routeur,
            exports.routeur,
            tenues.routeur_equipe,
        ],
    )
    # Photos des produits envoyées par l'équipe (derrière Caddy en production : /medias/…).
    # Seul ce sous-dossier est public : les images des messages, dans le même volume, ne se
    # lisent que par l'API, avec la clé du suivi ou la session (boutique.messagerie.images).
    publiques = Path(p.dossier_medias) / photos.SOUS_DOSSIER
    publiques.mkdir(parents=True, exist_ok=True)
    application.mount(
        f"/medias/{photos.SOUS_DOSSIER}", StaticFiles(directory=publiques), name="medias"
    )
    if manque := configuration_incomplete(p):
        logging.getLogger("boutique.paiements").warning(
            "Paiement mobile éteint", extra={"raison": manque}
        )
    return application
