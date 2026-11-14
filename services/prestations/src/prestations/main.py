"""Point d'entrée : uvicorn prestations.main:creer_app --factory"""

from fastapi import FastAPI

from prestations.config import ParametresPrestations
from prestations.routes import collectes, contrats, demandes, partenaires, public, releves
from socle.application import creer_application


def creer_app(parametres: ParametresPrestations | None = None) -> FastAPI:
    return creer_application(
        service="prestations",
        titre="Prestations : services aux structures de santé",
        parametres=parametres or ParametresPrestations(),
        routeurs=[
            public.routeur,
            collectes.routeur,
            partenaires.routeur,
            demandes.routeur,
            contrats.routeur,
            releves.routeur,
        ],
    )
