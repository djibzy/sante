# Décisions d'architecture

Résumé du registre du dossier d'architecture consolidé. Une décision ne se change qu'en
ajoutant une nouvelle ligne qui la remplace, avec sa raison.

| N° | Décision | Raison |
| --- | --- | --- |
| D1 | Produits séparés sur un socle commun | Chaque produit avance à son rythme sans multiplier les composants |
| D2 | Python, FastAPI et PostgreSQL pour tous les services | Compétence de l'équipe ; API documentées automatiquement |
| D3 | Tâches et événements dans PostgreSQL (Procrastinate, boîte d'envoi) | Un composant de moins à exploiter |
| D4 | Connexion maison compatible OpenID Connect (jetons EdDSA, JWKS) | Keycloak trop lourd pour un petit serveur |
| D5 | Interfaces Nuxt installables et utilisables hors ligne | Un seul code pour le web et le téléphone |
| D6 | Plateforme de formation maison | Maîtrise du hors ligne, des langues et des liens entre produits |
| D7 | Moteur d'orientation déterministe (JsonLogic) | Traçabilité et validation médicale |
| D8 | Données de santé sur une infrastructure séparée au Mali | Loi n° 2013-015 |
| D9 | Hébergement cloud à bas coût, puis au Mali en 2029 | Coût au lancement ; aucune donnée de santé avant 2028 |
| D10 | Articles réglementés vendus par un pharmacien partenaire | Décret n° 04-557 |
| D11 | Stockage de fichiers compatible S3 | Changer de fournisseur sans réécrire |
| D12 | Un seul dépôt, l'orientation dans un dépôt à part | Socle versionné une fois ; accès restreint aux données de santé |
| D13 | La boutique s'appelle Bibou, « par Yasal Santé » ; logo principal bleu | Lisible au soleil (10,9:1), distinct de la marque mère ; voir [marque.md](marque.md) |

## Choix de mise en œuvre (novembre 2026)

- **Espace de travail uv** : un seul environnement Python pour le socle et les services.
- **Jetons** : accès de 15 minutes signé Ed25519 ; rafraîchissement de 30 jours, à usage unique,
  stocké sous forme d'empreinte ; réutilisation d'un jeton remplacé = toutes les sessions coupées.
- **Connexion** : numéro de téléphone (E.164, région par défaut ML) et mot de passe Argon2 ;
  verrouillage de 15 minutes après 5 échecs.
- **Recherche du catalogue** : `unaccent` et `pg_trgm` dans PostgreSQL, sans moteur externe.
