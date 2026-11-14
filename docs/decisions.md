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
| D19 | Un remboursement est une écriture à part (montant, moyen, référence, motif) qui baisse le montant payé de la commande ; il apparaît en négatif dans l'export des encaissements | La caisse exportée au comptable reste juste ; ce qui est dû au client (trop-perçu, annulation, part de l'acompte non gardée) se lit sur la commande et dans l'onglet « À rembourser » |
| D20 | Le lien « faire payer un proche » porte sa propre clé (empreinte seule en base, remplacée à chaque nouveau lien) ; il ne donne que le montant dû, les articles et le paiement en ligne | Souvent un parent ou l'employeur paie : le lien de suivi, qui permet d'annuler et montre le numéro et l'adresse, n'a pas à circuler |
| D21 | « À vos couleurs » : le logo est lu dans le navigateur et n'est jamais envoyé au serveur ; la palette et les références RAL (indicatives, à vérifier sur nuancier) se partagent par un lien sans le logo ; le projet part par WhatsApp | Aucun fichier client à stocker ni à filtrer tant que le service n'est pas lancé ; le logo définitif arrive à l'équipe avec le projet, là où la conversation commerciale a lieu |
| D22 | Les services aux structures forment un produit à part, « Prestations » (service, base et interface propres), rendus d'abord avec des partenaires : l'entretien du linge passe par des blanchisseries et pressings partenaires ; notre blanchisserie, une fois ouverte, sera un partenaire « interne » | Démarrer sans investir dans les machines ; changer de partenaire ou laver soi-même ne change ni les contrats ni les relevés ; d'autres services aux structures s'y ajoutent |
| D23 | Linge compté pièce par pièce à l'enlèvement et au retour, devant la structure, avec un SMS de bon de collecte ; la tournée se lit dans le calendrier de chaque contrat (aucune collecte planifiée d'avance en base) ; prix relevés à l'enlèvement (structure) et au dépôt (partenaire), la pièce manquante facturée à personne | Le compte est la preuve en cas de litige ; le rythme se négocie structure par structure et se change sans rien replanifier ; un tarif modifié ne réécrit pas les relevés passés |
| D24 | La charte commune porte aussi la session (jeton en mémoire, cookie de Comptes), le client des API et la politique de sécurité du contenu de toutes les interfaces | Un seul code pour la connexion et la CSP ; chaque nouvelle interface s'y branche sans copie |
| D25 | Sur un réseau lent, la saisie faite avant que la page soit prête est gardée : un petit script en tête de page retient l'envoi trop tôt d'un formulaire, et un greffon commun rétablit les champs remplis à la main puis rejoue l'envoi une fois la page interactive | En 3G, la page s'affiche des secondes avant ses scripts : sans cela, un numéro ou un mot de passe tapé pendant ce temps s'effaçait (constaté sur la connexion de Bibou) |

## Choix de mise en œuvre (novembre 2026)

- **Espace de travail uv** : un seul environnement Python pour le socle et les services.
- **Jetons** : accès de 15 minutes signé Ed25519 ; rafraîchissement de 30 jours, à usage unique,
  stocké sous forme d'empreinte ; réutilisation d'un jeton remplacé = toutes les sessions coupées.
- **Connexion** : numéro de téléphone (E.164, région par défaut ML) et mot de passe Argon2 ;
  verrouillage de 15 minutes après 5 échecs.
- **Recherche du catalogue** : `unaccent` et `pg_trgm` dans PostgreSQL, sans moteur externe.
