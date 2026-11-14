from pydantic import field_validator
from pydantic_settings import SettingsConfigDict

from socle.settings import ParametresService, ParametresSms
from socle.telephones import normaliser_telephone

# Gestion : demandes, contrats, partenaires, tarifs et relevés.
ROLE_ADMIN_PRESTATIONS = "prestations:admin"
# Agents de collecte : la tournée et le comptage du linge, sans les prix ni les relevés.
ROLE_TERRAIN = "prestations:terrain"


class ParametresPrestations(ParametresService, ParametresSms):
    model_config = SettingsConfigDict(env_prefix="PRESTATIONS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/prestations"

    # Nom qui signe les SMS et les relevés.
    nom_service: str = "Yasal Santé"
    # Imprimés sur les relevés mensuels : à compléter avant l'ouverture.
    coordonnees: str = "Bamako, Mali"
    mentions_legales: str = ""  # RCCM, NIF, régime fiscal : à faire valider par le comptable

    # Demandes envoyées depuis la page publique, par numéro, sur 24 heures.
    demandes_max_par_telephone: int = 3

    # Numéros de l'équipe prévenus par SMS de chaque nouvelle demande (liste JSON) ; vide :
    # personne n'est prévenu, l'équipe regarde l'écran des demandes.
    telephones_equipe: list[str] = []

    @field_validator("telephones_equipe")
    @classmethod
    def _numeros_e164(cls, numeros: list[str]) -> list[str]:
        return [normaliser_telephone(numero) for numero in numeros]
