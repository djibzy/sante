from pydantic_settings import SettingsConfigDict

from socle.settings import ParametresService


class ParametresComptes(ParametresService):
    model_config = SettingsConfigDict(env_prefix="COMPTES_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/comptes"
    jwt_cle_privee: str | None = None  # clé privée Ed25519 (PEM) ; obligatoire en production
    duree_jeton_acces_minutes: int = 15
    duree_jeton_rafraichissement_jours: int = 30
    cookie_domaine: str | None = None  # ex. ".mondomaine.ml" pour partager entre sous-domaines
    cookie_securise: bool = True
    region_telephone: str = "ML"  # région par défaut pour lire les numéros locaux
    tentatives_max: int = 5
    verrouillage_minutes: int = 15
    version_conditions: str = "2026-11"
