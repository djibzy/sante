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
| D14 | Vitrine de boutique spécialisée en tenues médicales (menu par métier et par type, filtres couleur et taille, guide des tailles, broderie), puis nos autres services | Structure inspirée de belissa.fr ; textes, photos et noms de collections propres à Bibou |
| D15 | Paiement mobile en ligne par un agrégateur (CinetPay), ouvert une fois la commande confirmée ; statut toujours relu auprès de l'agrégateur | Un contrat pour Orange Money et Moov Money ; rien à rembourser pour une commande que l'on ne peut pas servir ; une notification falsifiée ne crédite rien |
| D16 | Avis clients réservés aux commandes livrées, publiés après relecture par l'équipe, signés du prénom et de l'initiale du nom | Avis crédibles (achat vérifié) ; aucune information médicale ni nom complet en ligne |
| D18 | Découverte visuelle par la couleur : familles calculées dans l'espace OKLab, articles dessinés dans leur couleur tant qu'il n'y a pas de photo, couleur indiquée sur chaque photo | Une couleur de service se choisit d'un coup d'œil ; le catalogue reste juste sans photos ; aucune photo d'une couleur montrée pour une autre |
| D17 | Articles faits à la demande (brodés, imprimés, personnalisés) : acompte non remboursable (50 % de leur prix, réglable), demandé à la confirmation ; la fabrication attend qu'il soit payé ; tout est rendu si la boutique annule | Un article à votre nom ne se revend pas : le tissu et le temps de l'atelier sont couverts ; les kits, assemblés à partir du stock, n'en demandent pas |

## Choix de mise en œuvre (novembre 2026)

- **Espace de travail uv** : un seul environnement Python pour le socle et les services.
- **Jetons** : accès de 15 minutes signé Ed25519 ; rafraîchissement de 30 jours, à usage unique,
  stocké sous forme d'empreinte ; réutilisation d'un jeton remplacé = toutes les sessions coupées.
- **Connexion** : numéro de téléphone (E.164, région par défaut ML) et mot de passe Argon2 ;
  verrouillage de 15 minutes après 5 échecs.
- **Recherche du catalogue** : `unaccent` et `pg_trgm` dans PostgreSQL, sans moteur externe.
