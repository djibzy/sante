from typing import Any

from fastapi import APIRouter, Request

routeur = APIRouter(tags=["connexion"])


@routeur.get("/.well-known/jwks.json", summary="Clé publique de vérification des jetons")
def jwks(request: Request) -> dict[str, list[dict[str, Any]]]:
    return {"keys": [request.app.state.jwk]}
