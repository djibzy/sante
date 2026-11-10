# Sécurité : revue de novembre 2026

Revue du socle, du service Comptes, de la boutique Bibou et du déploiement, à la fin de la
semaine 4. Elle sera refaite avant l'ouverture au public, puis à chaque nouveau produit.

## Ce qui est en place

| Domaine | Mesure |
| --- | --- |
| Connexion | Mots de passe Argon2 ; compte verrouillé 15 minutes après 5 échecs ; limite de 60 essais par minute et par adresse IP |
| Jetons | Accès de 15 minutes signé Ed25519 (émetteur et audience vérifiés) ; rafraîchissement à usage unique, stocké en empreinte, dans un cookie httpOnly, Secure, SameSite=Lax ; réutilisation d'un jeton remplacé = toutes les sessions coupées |
| Droits | Rôles vérifiés par l'API à chaque appel : `boutique:admin` (gestion), `boutique:atelier` (file de fabrication, sans téléphone des clients), `boutique:pro` (prix professionnel) ; attribués en ligne de commande, journalisés |
| Suivi sans compte | Clé de 128 bits tirée par l'appareil, stockée en empreinte SHA-256 ; même réponse pour une référence inconnue et une mauvaise clé ; la clé ne part pas vers les autres sites (Referrer-Policy) |
| Abus | Limites par adresse IP (commandes, devis, suivi, connexion, inscription), larges car les opérateurs mobiles partagent leurs adresses ; 5 demandes non traitées au plus par numéro sur 24 heures |
| Données | Aucune donnée de santé dans la boutique ; rappel « n'indiquez aucune information médicale » dans les champs libres ; journal d'audit sans nom ni téléphone ; numéros masqués dans les journaux d'envoi des SMS |
| Montants | Prix toujours recalculés par le serveur ; contraintes en base (totaux cohérents, montants positifs) ; factures numérotées sans trou ni doublon |
| Navigateur | HTTPS automatique, HSTS, `nosniff`, Referrer-Policy, Permissions-Policy, interdiction d'affichage dans un cadre (`X-Frame-Options`, `frame-ancestors`) ; aucun `v-html` dans les interfaces |
| Serveur | Seul Caddy est exposé (ports 80 et 443) ; une base et un rôle PostgreSQL par produit ; conteneurs sans droits root ; aucun secret dans le dépôt |
| Sauvegardes | `pg_dump` de chaque base et archive des photos chaque nuit, 14 jours gardés (service `sauvegarde`) |
| Photos | Format vérifié, image réencodée en WebP (aucune métadonnée, ni position GPS), 8 Mo et 8 photos par produit au plus |
| Intégration continue | Style, types, tests sur une vraie base PostgreSQL, construction des images ; audit des dépendances (informatif) |

## Corrigé pendant cette revue

- Limites de débit ajoutées sur les actions du lien de suivi (annuler, accepter, PDF).
- En-têtes contre le détournement de clic (`X-Frame-Options`, `frame-ancestors 'none'`).
- Sauvegarde nocturne des bases, qui manquait.
- Audit des dépendances Python et npm dans l'intégration continue.
- Un livreur actif ne peut pas être créé deux fois avec le même numéro.

## Reste à faire, par priorité

1. **Avant l'ouverture** : recopier les sauvegardes hors du serveur (stockage S3 ou disque
   chiffré), et faire un essai de restauration (`pg_restore --dbname=boutique fichier.dump`).
2. **Avant l'ouverture** : renseigner les mentions légales (RCCM, NIF, régime de TVA) avec le
   comptable ; déclarer le traitement des données clients à l'APDP (loi n° 2013-015).
3. **Comptes de l'équipe** : mot de passe d'au moins 12 caractères pour les rôles de gestion,
   puis second facteur (code par SMS) au premier trimestre 2027.
4. **Politique de sécurité du contenu (CSP)** complète pour l'interface Nuxt (scripts et
   styles), avec le module `nuxt-security`, une fois les pages stabilisées.
5. **Durées de conservation** : factures 10 ans (obligation comptable OHADA) ; commandes non
   facturées et SMS anonymisés après 3 ans ; à écrire dans la politique de confidentialité.
6. **Limites partagées** : les limites de débit vivent dans chaque processus ; à passer dans
   PostgreSQL ou Redis si l'on fait tourner plusieurs copies d'un service.
7. **Rotation des clés** : procédure écrite pour changer la clé de signature des jetons
   (publier la nouvelle clé dans le JWKS avant de signer avec elle).

## Exploitation

- Donner un rôle : `docker compose exec comptes python -m comptes.outils attribuer-role
  --telephone "76…" --role boutique:admin` (retirer : `retirer-role`).
- Restaurer une base : arrêter le service concerné, puis `docker compose exec sauvegarde
  pg_restore --clean --dbname=boutique /sauvegardes/boutique-AAAA-MM-JJ.dump`.
- Les journaux des services sont en JSON sur la sortie standard (`docker compose logs`).
