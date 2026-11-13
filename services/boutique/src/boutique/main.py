"""Point d'entrée : uvicorn boutique.main:creer_app --factory"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from boutique.config import ParametresBoutique
from boutique.paiements.fournisseurs import configuration_incomplete
from boutique.routes import (
    admin,
    atelier,
    avis,
    catalogue,
    catalogue_gestion,
    commandes,
    explorer,
    gestion,
    mes_donnees,
    paiements,
    stock,
    tableau,
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
            commandes.routeur,
            paiements.routeur,
            avis.routeur,
            mes_donnees.routeur,
            admin.routeur,
            catalogue_gestion.routeur,
            gestion.routeur,
            avis.routeur_equipe,
            atelier.routeur,
            stock.routeur,
            tableau.routeur,
        ],
    )
    # Photos envoyées par l'équipe (derrière Caddy en production : /medias/…).
    medias = Path(p.dossier_medias)
    medias.mkdir(parents=True, exist_ok=True)
    application.mount("/medias", StaticFiles(directory=medias), name="medias")
    if manque := configuration_incomplete(p):
        logging.getLogger("boutique.paiements").warning(
            "Paiement mobile éteint", extra={"raison": manque}
        )
    return application
