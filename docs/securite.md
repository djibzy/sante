# Sécurité : revue de novembre 2026

Revue du socle, du service Comptes, de la boutique Bibou et du déploiement, à la fin de la
semaine 4. Elle sera refaite avant l'ouverture au public, puis à chaque nouveau produit.

## Ce qui est en place

| Domaine | Mesure |
| --- | --- |
| Connexion | Mots de passe Argon2 ; compte verrouillé 15 minutes après 5 échecs ; limite de 60 essais par minute et par adresse IP |
| Droits des personnes | « Mon compte » : télécharger toutes ses données (compte, consentements, journal, commandes, avis) ; supprimer son compte (mot de passe demandé) : compte anonymisé et numéro libéré, sessions coupées, commandes terminées anonymisées, commandes facturées détachées (gardées 10 ans), avis effacés ; impossible tant qu'une commande est attendue |
| Mot de passe oublié | Code à 6 chiffres par SMS : seule son empreinte est gardée, 10 minutes, 5 essais, 3 codes par heure et par compte ; même réponse qu'un compte existe ou non (SMS envoyé après la réponse) ; nouveau mot de passe = toutes les sessions coupées ; 12 caractères au moins pour les comptes de l'équipe |
| Jetons | Accès de 15 minutes signé Ed25519 (émetteur et audience vérifiés) ; rafraîchissement à usage unique, stocké en empreinte, dans un cookie httpOnly, Secure, SameSite=Lax ; réutilisation d'un jeton remplacé = toutes les sessions coupées |
| Droits | Rôles vérifiés par l'API à chaque appel : `boutique:admin` (gestion), `boutique:atelier` (file de fabrication, sans téléphone des clients), `boutique:pro` (prix professionnel) ; attribués en ligne de commande, journalisés |
| Suivi sans compte | Clé de 128 bits tirée par l'appareil, stockée en empreinte SHA-256 ; même réponse pour une référence inconnue et une mauvaise clé ; la clé ne part pas vers les autres sites (Referrer-Policy) |
| Abus | Limites par adresse IP (commandes, devis, suivi, connexion, inscription), larges car les opérateurs mobiles partagent leurs adresses ; 5 demandes non traitées au plus par numéro sur 24 heures |
| Données | Aucune donnée de santé dans la boutique ; rappel « n'indiquez aucune information médicale » dans les champs libres ; journal d'audit sans nom ni téléphone ; numéros masqués dans les journaux d'envoi des SMS |
| Montants | Prix toujours recalculés par le serveur ; contraintes en base (totaux cohérents, montants positifs) ; factures numérotées sans trou ni doublon |
| Paiement en ligne | Montant fixé par le serveur (reste à payer) ; statut et montant toujours relus auprès de CinetPay avec notre clé, jamais pris dans la notification ; crédit sous verrou, une seule fois ; montant ou devise différents = « à vérifier », rien de crédité ; aucun nom ni téléphone transmis à l'agrégateur, ni la clé du lien de suivi ; 10 tentatives par commande et par heure ; mode simulation refusé en production |
| Avis clients | Réservés aux commandes livrées (un par produit et par commande) ; publiés seulement après relecture par l'équipe, qui refuse toute information médicale ; prénom et initiale du nom, jamais le téléphone ; note du produit recomptée sous verrou |
| Hors ligne | Le service worker ne garde que l'application, le catalogue public et les photos vues ; jamais le suivi des commandes, le compte, l'espace de l'équipe ni un envoi. Une commande préparée sans réseau reste sur le téléphone jusqu'à son envoi, puis en est effacée ; sa clé empêche tout doublon |
| Navigateur | HTTPS automatique, HSTS, `nosniff`, Referrer-Policy, Permissions-Policy, interdiction d'affichage dans un cadre (`X-Frame-Options`, `frame-ancestors`) ; aucun `v-html` dans les interfaces ; politique de sécurité du contenu (CSP) sur chaque page : scripts du site et scripts en ligne marqués d'un nonce par réponse, appels limités à l'API et au service Comptes |
| Serveur | Seul Caddy est exposé (ports 80 et 443) ; une base et un rôle PostgreSQL par produit ; conteneurs sans droits root ; aucun secret dans le dépôt |
| Sauvegardes | `pg_dump` de chaque base et archive des photos chaque nuit, 14 jours gardés (service `sauvegarde`) ; copie chiffrée (age) hors du serveur avec rclone, 90 jours, dès qu'un stockage est renseigné ; essai de restauration outillé |
| Photos | Format vérifié, image réencodée en WebP (aucune métadonnée, ni position GPS), 8 Mo et 8 photos par produit au plus |
| Intégration continue | Style, types, tests sur une vraie base PostgreSQL, construction des images ; audit des dépendances (informatif) |

## Corrigé pendant cette revue

- Limites de débit ajoutées sur les actions du lien de suivi (annuler, accepter, PDF).
- En-têtes contre le détournement de clic (`X-Frame-Options`, `frame-ancestors 'none'`).
- Sauvegarde nocturne des bases, qui manquait.
- Audit des dépendances Python et npm dans l'intégration continue.
- Un livreur actif ne peut pas être créé deux fois avec le même numéro.

## Reste à faire, par priorité

1. **Avant l'ouverture** : renseigner la copie chiffrée hors du serveur (`SAUVEGARDE_*` et
   `S3_*` dans `.env`, clé « age » créée hors du serveur), puis lancer l'essai de restauration
   chaque mois (outils prêts, voir « Exploitation »).
2. **Avant l'ouverture** : renseigner les mentions légales (RCCM, NIF, régime de TVA) avec le
   comptable ; déclarer le traitement des données clients à l'APDP (loi n° 2013-015).
3. **Comptes de l'équipe** : 12 caractères exigés à chaque nouveau mot de passe (fait) ;
   second facteur (code par SMS, sur la même base que « mot de passe oublié ») au premier
   trimestre 2027.
4. **Politique de sécurité du contenu (CSP)** : en place pour les scripts (nonce par
   réponse, plugin Nitro `web/charte/server/plugins/securite-contenu.ts`, commun aux
   interfaces) ; les styles restent permis en
   ligne (attributs `style` des composants) : à resserrer avec des nonces si besoin.
5. **Durées de conservation** : appliquées chaque nuit (boutique.entretien, comptes.entretien) :
   commandes facturées anonymisées après 10 ans (obligation comptable OHADA), commandes sans
   suite après 3 ans, SMS effacés après 3 ans, avis refusés après 30 jours, tentatives de
   paiement abandonnées après 90 jours, codes SMS le lendemain, sessions fermées après
   30 jours, adresses IP du journal après un an. Prestations (prestations.conservation) :
   demandes classées sans suite et SMS effacés après un an, adresses IP du journal après un
   an ; contrats et collectes gardés pour les relevés et la facturation. Reste à les écrire
   dans la politique de confidentialité.
8. **Prestations** : l'équipe de terrain (rôle `prestations:terrain`) voit adresses et
   téléphones des structures, jamais les prix ni les relevés ; les comptes du linge ne portent
   aucune donnée de santé (rappel sur chaque champ d'observation). Le linge souillé des
   structures relève de leur protocole d'hygiène : à décrire dans chaque contrat avec la
   blanchisserie partenaire (tri, sacs, température de lavage).
6. **Limites partagées** : les limites de débit vivent dans chaque processus ; à passer dans
   PostgreSQL ou Redis si l'on fait tourner plusieurs copies d'un service.
7. **Rotation des clés** : procédure écrite pour changer la clé de signature des jetons
   (publier la nouvelle clé dans le JWKS avant de signer avec elle).

## Exploitation

- Donner un rôle : `docker compose exec comptes python -m comptes.outils attribuer-role
  --telephone "76…" --role boutique:admin` (retirer : `retirer-role`).
- Sauvegarde immédiate : `docker compose exec sauvegarde env UNE_FOIS=1 sh /sauvegarde.sh`.
- Essai de restauration (chaque mois) : `docker compose exec sauvegarde sh
  /essai-restauration.sh` restaure la dernière sauvegarde de chaque base dans une base
  temporaire, compte tables et lignes, relit l'archive des photos, puis efface la base d'essai.
- Restaurer une base : arrêter le service concerné, puis `docker compose exec sauvegarde
  pg_restore --clean --dbname=boutique /sauvegardes/boutique-AAAA-MM-JJ.dump`.
- Restaurer depuis la copie distante : `rclone copy distant:… .`, puis
  `age --decrypt -i cle-privee.txt -o boutique.dump boutique-AAAA-MM-JJ.dump.age`.
- Les journaux des services sont en JSON sur la sortie standard (`docker compose logs`).
