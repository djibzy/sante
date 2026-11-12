"""Configuration commune, lue dans les variables d'environnement."""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ParametresService(BaseSettings):
    """Paramètres partagés par tous les services.

    Chaque service en hérite et fixe son préfixe de variables (COMPTES_, BOUTIQUE_…).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environnement: str = "developpement"  # developpement | test | production
    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/postgres"
    db_pool: bool = True  # False en test : une connexion par requête
    jwt_cle_publique: str | None = None  # clé publique Ed25519 (PEM) du service Comptes
    jwt_emetteur: str = "comptes"
    jwt_audience: str = "sante"
    cors_origines: list[str] = []

    @property
    def en_production(self) -> bool:
        return self.environnement == "production"


class ParametresSms(BaseSettings):
    """Envoi de SMS, pour les services qui en envoient (préfixe du service : BOUTIQUE_, COMPTES_).

    « journal » écrit les messages dans les journaux sans rien envoyer (essais) ; « orange »
    passe par l'API SMS d'Orange (compte Orange Developer requis).
    """

    sms_fournisseur: Literal["journal", "orange"] = "journal"
    sms_expediteur: str = ""  # numéro E.164 du compte SMS, ex. +22370000000
    sms_nom_expediteur: str = ""  # nom affiché, s'il est validé par l'opérateur
    orange_client_id: str = ""
    orange_client_secret: SecretStr = SecretStr("")
