"""Identifiants UUID version 7 (RFC 9562).

Uniques, triés dans le temps et générables sur l'appareil : une saisie créée hors ligne
garde son identifiant et un renvoi ne crée jamais de doublon.
"""

import os
import time
import uuid

_MASQUE_48 = (1 << 48) - 1
_MASQUE_62 = (1 << 62) - 1


def uuid7() -> uuid.UUID:
    """Renvoie un UUID v7 : 48 bits d'horodatage en millisecondes puis 74 bits aléatoires."""
    millisecondes = time.time_ns() // 1_000_000
    alea = int.from_bytes(os.urandom(10), "big")
    valeur = (millisecondes & _MASQUE_48) << 80
    valeur |= 0x7 << 76  # version
    valeur |= ((alea >> 62) & 0xFFF) << 64  # rand_a, 12 bits
    valeur |= 0b10 << 62  # variante RFC 9562
    valeur |= alea & _MASQUE_62  # rand_b, 62 bits
    return uuid.UUID(int=valeur)
