"""Limites de débit par adresse IP, en mémoire : contre l'envoi massif de commandes, d'essais
de connexion ou de demandes de suivi.

Une fenêtre glissante par adresse et par limite, rangée dans l'application (chaque processus a
la sienne ; suffisant pour un serveur unique, à remplacer par un stockage partagé au-delà).
"""

import time
from collections import deque

from fastapi import HTTPException, Request, status

_MAX_ADRESSES = 50_000


class LimiteDebit:
    def __init__(self, nom: str, nombre: int, secondes: int) -> None:
        self.nom = nom
        self.nombre = nombre
        self.secondes = secondes

    def __call__(self, request: Request) -> None:
        etat: dict[str, dict[str, deque[float]]] = request.app.state.__dict__.setdefault(
            "limites_debit", {}
        )
        appels = etat.setdefault(self.nom, {})
        if len(appels) > _MAX_ADRESSES:
            appels.clear()  # protection mémoire : on repart de zéro plutôt que de saturer
        adresse = request.client.host if request.client else "inconnue"
        file = appels.setdefault(adresse, deque())
        maintenant = time.monotonic()
        while file and maintenant - file[0] > self.secondes:
            file.popleft()
        if len(file) >= self.nombre:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Trop de demandes depuis cette connexion. Réessayez dans une minute.",
                headers={"Retry-After": str(self.secondes)},
            )
        file.append(maintenant)
