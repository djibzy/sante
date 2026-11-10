from typing import Literal

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from socle.settings import ParametresService

ROLE_ADMIN_BOUTIQUE = "boutique:admin"
# Atelier : voit la file de fabrication (sans les téléphones des clients), rien d'autre.
ROLE_ATELIER = "boutique:atelier"
# Soignant ou structure dont le statut a été vérifié : il paie le prix professionnel.
ROLE_PRO = "boutique:pro"


class ParametresBoutique(ParametresService):
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

    # SMS : « journal » écrit les messages dans les journaux sans rien envoyer (essais) ;
    # « orange » passe par l'API SMS d'Orange (compte Orange Developer requis).
    sms_fournisseur: Literal["journal", "orange"] = "journal"
    sms_expediteur: str = ""  # numéro E.164 du compte SMS, ex. +22370000000
    sms_nom_expediteur: str = ""  # nom affiché (« Bibou »), s'il est validé par l'opérateur
    orange_client_id: str = ""
    orange_client_secret: SecretStr = SecretStr("")

    # Photos des produits envoyées par l'équipe : dossier sur le serveur (volume Docker en
    # production) et taille maximale d'un envoi.
    dossier_medias: str = "medias"
    taille_max_photo: int = 8 * 1024 * 1024
