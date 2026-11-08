"""Outils en ligne de commande du service Comptes.

uv run python -m comptes.outils generer-cles
uv run python -m comptes.outils creer-admin --telephone "76 12 34 56" --nom "Prénom Nom"
"""

import argparse
import asyncio
import getpass
import sys

from argon2 import PasswordHasher
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select

from comptes.cles import pem_prive, pem_public
from comptes.config import ParametresComptes
from comptes.models import Utilisateur
from comptes.telephones import normaliser_telephone
from socle.db import creer_moteur, fabrique_sessions
from socle.security import ROLE_ADMIN


def generer_cles() -> None:
    """Affiche une paire de clés au format des fichiers .env (clé privée : à garder secrète)."""
    cle = Ed25519PrivateKey.generate()
    print(f'COMPTES_JWT_CLE_PRIVEE="{pem_prive(cle)}"')
    publique = pem_public(cle.public_key())
    for prefixe in ("COMPTES", "BOUTIQUE"):
        print(f'{prefixe}_JWT_CLE_PUBLIQUE="{publique}"')


async def creer_admin(telephone_brut: str, nom: str) -> None:
    p = ParametresComptes()
    telephone = normaliser_telephone(telephone_brut, p.region_telephone)
    mot_de_passe = getpass.getpass("Mot de passe (8 caractères minimum) : ")
    if len(mot_de_passe) < 8 or mot_de_passe != getpass.getpass("Confirmation : "):
        sys.exit("Mot de passe trop court ou différent de la confirmation.")
    moteur = creer_moteur(p.database_url, pool=False)
    async with fabrique_sessions(moteur)() as session:
        requete = select(Utilisateur).where(Utilisateur.telephone == telephone)
        utilisateur = (await session.execute(requete)).scalar_one_or_none()
        if utilisateur is None:
            utilisateur = Utilisateur(
                telephone=telephone,
                nom=nom,
                mot_de_passe_hash=PasswordHasher().hash(mot_de_passe),
                roles=[ROLE_ADMIN],
            )
            session.add(utilisateur)
        elif ROLE_ADMIN not in utilisateur.roles:
            utilisateur.roles = [*utilisateur.roles, ROLE_ADMIN]
        await session.commit()
    await moteur.dispose()
    print(f"Administrateur prêt : {telephone}")


def main(argv: list[str] | None = None) -> None:
    analyseur = argparse.ArgumentParser(prog="comptes.outils")
    commandes = analyseur.add_subparsers(dest="commande", required=True)
    commandes.add_parser("generer-cles", help="Générer une paire de clés de signature")
    admin = commandes.add_parser("creer-admin", help="Créer ou promouvoir un administrateur")
    admin.add_argument("--telephone", required=True)
    admin.add_argument("--nom", required=True)
    arguments = analyseur.parse_args(argv)
    if arguments.commande == "generer-cles":
        generer_cles()
    else:
        asyncio.run(creer_admin(arguments.telephone, arguments.nom))


if __name__ == "__main__":
    main()
