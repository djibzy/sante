"""Paire de clés de signature jetable pour l'intégration continue, au format de $GITHUB_ENV
(valeurs sur plusieurs lignes). Jamais utilisée ailleurs : chaque exécution a la sienne."""

import secrets

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from comptes.cles import pem_prive, pem_public

cle = Ed25519PrivateKey.generate()
for nom, valeur in (
    ("COMPTES_JWT_CLE_PRIVEE", pem_prive(cle)),
    ("COMPTES_JWT_CLE_PUBLIQUE", pem_public(cle.public_key())),
    ("BOUTIQUE_JWT_CLE_PUBLIQUE", pem_public(cle.public_key())),
):
    fin = f"FIN_{secrets.token_hex(8)}"
    print(f"{nom}<<{fin}\n{valeur.strip()}\n{fin}")
