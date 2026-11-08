"""Socle commun à tous les produits de l'écosystème.

Il ne contient que ce que tous les services partagent : configuration, accès à la base,
identifiants UUID v7, vérification des jetons signés par le service Comptes, journaux,
journal d'audit et fabrique d'application FastAPI.
"""

from socle.ids import uuid7

__all__ = ["uuid7"]
