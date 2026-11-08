"""Clés de signature des jetons : Ed25519, publiées au format JWKS."""

import base64
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def charger_cle_privee(pem: str | None, environnement: str) -> Ed25519PrivateKey:
    """Charge la clé privée ; en développement et en test, en génère une éphémère."""
    if pem:
        cle = serialization.load_pem_private_key(pem.encode(), password=None)
        if not isinstance(cle, Ed25519PrivateKey):
            raise ValueError("COMPTES_JWT_CLE_PRIVEE doit être une clé Ed25519")
        return cle
    if environnement == "production":
        raise RuntimeError("COMPTES_JWT_CLE_PRIVEE est obligatoire en production")
    return Ed25519PrivateKey.generate()


def pem_prive(cle: Ed25519PrivateKey) -> str:
    return cle.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def pem_public(cle: Ed25519PublicKey) -> str:
    return cle.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


def _octets_bruts(cle: Ed25519PublicKey) -> bytes:
    return cle.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def identifiant_cle(cle: Ed25519PublicKey) -> str:
    return hashlib.sha256(_octets_bruts(cle)).hexdigest()[:16]


def jwk_public(cle: Ed25519PublicKey) -> dict[str, str]:
    x = base64.urlsafe_b64encode(_octets_bruts(cle)).rstrip(b"=").decode()
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": x,
        "kid": identifiant_cle(cle),
        "use": "sig",
        "alg": "EdDSA",
    }
