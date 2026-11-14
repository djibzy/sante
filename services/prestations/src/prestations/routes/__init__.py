"""Routes de l'API Prestations : page publique, gestion (prestations:admin) et tournée
(prestations:terrain)."""

from fastapi import Request

from prestations.config import ROLE_ADMIN_PRESTATIONS, ROLE_TERRAIN, ParametresPrestations
from socle.security import exiger_role, exiger_un_role

GESTION = exiger_role(ROLE_ADMIN_PRESTATIONS)
TERRAIN = exiger_un_role(ROLE_TERRAIN, ROLE_ADMIN_PRESTATIONS)


def parametres(request: Request) -> ParametresPrestations:
    valeur: ParametresPrestations = request.app.state.parametres
    return valeur


def adresse_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
