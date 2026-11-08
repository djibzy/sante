"""Vérification des jetons d'accès signés par le service Comptes.

Chaque produit vérifie la signature avec la clé publique, sans interroger Comptes à chaque
requête. Les jetons sont des JWT signés en EdDSA (Ed25519), compatibles OpenID Connect.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ROLE_ADMIN = "admin"


@dataclass(frozen=True)
class Principal:
    """La personne connectée, telle que décrite par son jeton."""

    id: UUID
    nom: str
    langue: str
    roles: frozenset[str]

    def a_role(self, role: str) -> bool:
        return role in self.roles or ROLE_ADMIN in self.roles


class JetonInvalide(Exception):
    pass


class VerificateurJetons:
    def __init__(self, cle_publique_pem: str, *, emetteur: str, audience: str) -> None:
        cle = serialization.load_pem_public_key(cle_publique_pem.encode())
        if not isinstance(cle, Ed25519PublicKey):
            raise ValueError("La clé publique doit être une clé Ed25519")
        self._cle = cle
        self._emetteur = emetteur
        self._audience = audience

    def verifier(self, jeton: str) -> Principal:
        try:
            donnees = jwt.decode(
                jeton,
                self._cle,
                algorithms=["EdDSA"],
                audience=self._audience,
                issuer=self._emetteur,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise JetonInvalide(str(exc)) from exc
        return Principal(
            id=UUID(donnees["sub"]),
            nom=donnees.get("name", ""),
            langue=donnees.get("lang", "fr"),
            roles=frozenset(donnees.get("roles", [])),
        )


_porteur = HTTPBearer(auto_error=False)


def principal_optionnel(
    request: Request, identifiants: HTTPAuthorizationCredentials | None = Depends(_porteur)
) -> Principal | None:
    if identifiants is None:
        return None
    verificateur: VerificateurJetons | None = getattr(request.app.state, "verificateur", None)
    if verificateur is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Vérification des jetons non configurée"
        )
    try:
        return verificateur.verifier(identifiants.credentials)
    except JetonInvalide as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Session expirée ou invalide",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def principal_requis(principal: Principal | None = Depends(principal_optionnel)) -> Principal:
    if principal is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Connexion requise",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def exiger_role(role: str) -> Callable[[Principal], Principal]:
    """Dépendance qui refuse l'accès aux personnes qui n'ont pas le rôle demandé."""

    def _verifier(principal: Principal = Depends(principal_requis)) -> Principal:
        if not principal.a_role(role):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès réservé")
        return principal

    return _verifier


def exiger_un_role(*roles: str) -> Callable[[Principal], Principal]:
    """Comme exiger_role, pour un écran ouvert à plusieurs rôles (atelier et gestion)."""

    def _verifier(principal: Principal = Depends(principal_requis)) -> Principal:
        if not any(principal.a_role(role) for role in roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès réservé")
        return principal

    return _verifier
