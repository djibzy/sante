from pydantic_settings import SettingsConfigDict

from socle.settings import ParametresService, ParametresSms

# Rôles de l'équipe : mot de passe plus long, choisi à la réinitialisation ou au changement.
ROLES_EQUIPE = frozenset({"admin", "boutique:admin", "boutique:atelier"})
LONGUEUR_EQUIPE = 12


class ParametresComptes(ParametresService, ParametresSms):
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

    # Mot de passe oublié : code à 6 chiffres envoyé par SMS.
    code_validite_minutes: int = 10
    code_essais_max: int = 5
    codes_par_heure: int = 3  # par compte : le SMS coûte, et ne doit pas servir à harceler
