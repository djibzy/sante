from typing import Literal

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from socle.settings import ParametresService, ParametresSms

ROLE_ADMIN_BOUTIQUE = "boutique:admin"
# Atelier : voit la file de fabrication (sans les téléphones des clients), rien d'autre.
ROLE_ATELIER = "boutique:atelier"
# Soignant ou structure dont le statut a été vérifié : il paie le prix professionnel.
ROLE_PRO = "boutique:pro"


class ParametresBoutique(ParametresService, ParametresSms):
    model_config = SettingsConfigDict(env_prefix="BOUTIQUE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/boutique"

    # Documents (devis, puis factures) : coordonnées et mentions à compléter avant l'ouverture.
    coordonnees: str = "Bamako, Mali"
    mentions_legales: str = ""  # RCCM, NIF, régime fiscal : à faire valider par le comptable
    conditions_devis: str = (
        "Prix en francs CFA. Paiement à la livraison. Délai de fabrication confirmé à "
        "l'acceptation du devis."
    )
    validite_devis_jours: int = 30

    # Demandes non traitées (commandes à confirmer, devis demandés) par numéro, sur 24 heures.
    demandes_max_par_telephone: int = 5

    # Adresse publique de la boutique, pour les liens de suivi envoyés par SMS.
    url_publique: str = ""

    # Photos des produits envoyées par l'équipe : dossier sur le serveur (volume Docker en
    # production) et taille maximale d'un envoi.
    dossier_medias: str = "medias"
    taille_max_photo: int = 8 * 1024 * 1024

    # Paiement mobile en ligne : « aucun » (paiement à la livraison seulement), « cinetpay », ou
    # « simulation » pour les essais (refusée en production).
    paiement_mobile: Literal["aucun", "cinetpay", "simulation"] = "aucun"
    cinetpay_apikey: SecretStr = SecretStr("")
    cinetpay_site_id: str = ""
    cinetpay_canaux: str = "MOBILE_MONEY"
