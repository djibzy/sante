"""Point d'entrée : uvicorn comptes.main:creer_app --factory"""

from fastapi import FastAPI

from comptes.cles import charger_cle_privee, jwk_public, pem_public
from comptes.config import ParametresComptes
from comptes.jetons import Signataire
from comptes.routes import auth, cles, organisations
from socle.application import creer_application


def creer_app(parametres: ParametresComptes | None = None) -> FastAPI:
    p = parametres or ParametresComptes()
    cle_privee = charger_cle_privee(p.jwt_cle_privee, p.environnement)
    cle_publique = cle_privee.public_key()
    app = creer_application(
        service="comptes",
        titre="Comptes : connexion unique",
        parametres=p,
        routeurs=[auth.routeur, organisations.routeur, cles.routeur],
        cle_publique_pem=pem_public(cle_publique),
    )
    app.state.signataire = Signataire(
        cle_privee,
        emetteur=p.jwt_emetteur,
        audience=p.jwt_audience,
        duree_minutes=p.duree_jeton_acces_minutes,
    )
    app.state.jwk = jwk_public(cle_publique)
    return app
