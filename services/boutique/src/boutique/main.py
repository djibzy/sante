"""Point d'entrée : uvicorn boutique.main:creer_app --factory"""

from fastapi import FastAPI

from boutique.config import ParametresBoutique
from boutique.routes import (
    admin,
    atelier,
    catalogue,
    catalogue_gestion,
    commandes,
    gestion,
    stock,
)
from socle.application import creer_application


def creer_app(parametres: ParametresBoutique | None = None) -> FastAPI:
    p = parametres or ParametresBoutique()
    return creer_application(
        service="boutique",
        titre="Boutique : catalogue et commandes",
        parametres=p,
        routeurs=[
            catalogue.routeur,
            commandes.routeur,
            admin.routeur,
            catalogue_gestion.routeur,
            gestion.routeur,
            atelier.routeur,
            stock.routeur,
        ],
    )
