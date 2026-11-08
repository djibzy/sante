"""Configuration commune, lue dans les variables d'environnement."""

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
