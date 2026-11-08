"""Journaux au format JSON, identiques dans tous les services."""

import json
import logging
import sys
from datetime import UTC, datetime


class FormateurJson(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        entree = {
            "horodatage": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "niveau": record.levelname,
            "service": self._service,
            "journal": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entree["exception"] = self.formatException(record.exc_info)
        return json.dumps(entree, ensure_ascii=False)


def configurer_journaux(service: str, niveau: int = logging.INFO) -> None:
    gestionnaire = logging.StreamHandler(sys.stdout)
    gestionnaire.setFormatter(FormateurJson(service))
    racine = logging.getLogger()
    racine.handlers = [gestionnaire]
    racine.setLevel(niveau)
