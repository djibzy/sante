from pydantic_settings import SettingsConfigDict

from socle.settings import ParametresService

ROLE_ADMIN_BOUTIQUE = "boutique:admin"


class ParametresBoutique(ParametresService):
    model_config = SettingsConfigDict(env_prefix="BOUTIQUE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/boutique"
