"""Fabrique d'application FastAPI commune à tous les services."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from socle.db import creer_moteur, fabrique_sessions
from socle.journaux import configurer_journaux
from socle.security import VerificateurJetons
from socle.settings import ParametresService

EN_TETES_SECURITE = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def creer_application(
    *,
    service: str,
    titre: str,
    parametres: ParametresService,
    routeurs: list[APIRouter],
    cle_publique_pem: str | None = None,
    version: str = "0.1.0",
) -> FastAPI:
    """Crée l'application : base de données, vérification des jetons, CORS, santé, routes.

    Le moteur de base est créé tout de suite (il ne se connecte qu'à la première requête) et
    fermé à l'arrêt du service.
    """
    configurer_journaux(service)
    moteur = creer_moteur(parametres.database_url, pool=parametres.db_pool)

    @asynccontextmanager
    async def cycle_de_vie(_: FastAPI) -> AsyncIterator[None]:
        yield
        await moteur.dispose()

    app = FastAPI(title=titre, version=version, lifespan=cycle_de_vie)
    app.state.parametres = parametres
    app.state.moteur = moteur
    app.state.sessions = fabrique_sessions(moteur)
    cle = cle_publique_pem or parametres.jwt_cle_publique
    app.state.verificateur = (
        VerificateurJetons(cle, emetteur=parametres.jwt_emetteur, audience=parametres.jwt_audience)
        if cle
        else None
    )

    if parametres.cors_origines:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=parametres.cors_origines,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def en_tetes_securite(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        reponse = await call_next(request)
        for nom, valeur in EN_TETES_SECURITE.items():
            reponse.headers.setdefault(nom, valeur)
        return reponse

    @app.get("/sante", tags=["supervision"], summary="État du service")
    async def sante() -> dict[str, str]:
        async with app.state.sessions() as session:
            await session.execute(text("select 1"))
        return {"statut": "ok", "service": service}

    for routeur in routeurs:
        app.include_router(routeur)
    return app
