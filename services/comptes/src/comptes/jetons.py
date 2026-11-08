"""Émission des jetons d'accès (JWT signés) et des jetons de rafraîchissement."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from comptes.cles import identifiant_cle
from comptes.models import Utilisateur


class Signataire:
    def __init__(
        self, cle: Ed25519PrivateKey, *, emetteur: str, audience: str, duree_minutes: int
    ) -> None:
        self._cle = cle
        self._kid = identifiant_cle(cle.public_key())
        self._emetteur = emetteur
        self._audience = audience
        self._duree = timedelta(minutes=duree_minutes)

    @property
    def duree_secondes(self) -> int:
        return int(self._duree.total_seconds())

    def emettre(self, utilisateur: Utilisateur) -> str:
        maintenant = datetime.now(UTC)
        revendications = {
            "iss": self._emetteur,
            "aud": self._audience,
            "sub": str(utilisateur.id),
            "iat": maintenant,
            "exp": maintenant + self._duree,
            "name": utilisateur.nom,
            "lang": utilisateur.langue,
            "roles": list(utilisateur.roles),
        }
        return jwt.encode(revendications, self._cle, algorithm="EdDSA", headers={"kid": self._kid})


def empreinte(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()


def nouveau_jeton_rafraichissement() -> tuple[str, str]:
    """Renvoie le jeton à remettre au client et l'empreinte à stocker."""
    brut = secrets.token_urlsafe(32)
    return brut, empreinte(brut)
