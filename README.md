# Yasal Santé : écosystème de santé (Mali, puis AES)

Information, formation et équipement de santé, en produits séparés reliés par un socle commun.
Ce dépôt contient, pour commencer, le socle, le service de comptes, **Bibou**, la boutique
(tenues brodées, imprimés, kits et matériel), et les **prestations** aux structures de santé, à
commencer par l'entretien du linge avec des blanchisseries partenaires. Marque et logos :
[docs/marque.md](docs/marque.md).

| Dossier | Contenu | Port local |
| --- | --- | --- |
| `socle/` | Code partagé : base de données, identifiants, jetons, journaux, audit | |
| `services/comptes/` | Compte unique : inscription et connexion par téléphone, organisations | 8001 |
| `services/boutique/` | Catalogue, panier, commandes, devis PDF, paiements, zones de livraison | 8002 |
| `services/prestations/` | Services aux structures : demandes, contrats, tournée, collectes comptées, relevés | 8003 |
| `web/boutique/` | Interface de Bibou (Nuxt), avec la charte commune de `web/charte/` | 3000 |
| `web/prestations/` | Offre aux structures et espace de l'équipe des prestations (Nuxt) | 3001 |
| `infra/` | Mise en production : Docker Compose, Caddy, PostgreSQL | |

Documents de référence : [dossier de projet](https://claude.ai/artifact/1RG4A9vTti9ycmD12kiJ98),
[plan d'action et financier](https://claude.ai/artifact/PLemzatgVRdtA53zMcZqDS),
[dossier d'architecture](https://claude.ai/artifact/3uiNEZJkPX172JFeHChgWb),
[décisions](docs/decisions.md), [sécurité](docs/securite.md).

## Lancer en local

Prérequis : [uv](https://docs.astral.sh/uv/), PostgreSQL 16 (utilisateur `postgres` sans mot de
passe sur localhost, bases `comptes`, `boutique` et `prestations`), Node.js 22.

```bash
uv sync
uv run python -m comptes.outils generer-cles        # copier les lignes dans un fichier .env
(cd services/comptes && uv run alembic upgrade head)
(cd services/boutique && uv run alembic upgrade head)
(cd services/prestations && uv run alembic upgrade head)
uv run python -m boutique.donnees_demo               # catalogue de démonstration
uv run python -m prestations.donnees_demo            # partenaires et contrats fictifs

uv run uvicorn comptes.main:creer_app --factory --port 8001
uv run uvicorn boutique.main:creer_app --factory --port 8002
uv run uvicorn prestations.main:creer_app --factory --port 8003
cd web/boutique && npm install && npm run dev        # http://localhost:3000
cd web/prestations && npm install && npm run dev     # http://localhost:3001
```

Pour que les interfaces parlent aux API en local, ajouter au `.env` :
`COMPTES_COOKIE_SECURISE=false`,
`COMPTES_CORS_ORIGINES=["http://localhost:3000", "http://localhost:3001"]`,
`BOUTIQUE_CORS_ORIGINES=["http://localhost:3000"]`, `PRESTATIONS_CORS_ORIGINES=["http://localhost:3001"]`
et la clé publique de Comptes dans `BOUTIQUE_JWT_CLE_PUBLIQUE` et `PRESTATIONS_JWT_CLE_PUBLIQUE`.

Documentation des API : http://localhost:8001/docs, http://localhost:8002/docs et
http://localhost:8003/docs.

## Vérifier

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy socle/src services/comptes/src services/boutique/src services/prestations/src
uv run pytest services/comptes
uv run pytest services/boutique
uv run pytest services/prestations
```

Les tests utilisent les bases `comptes_test`, `boutique_test` et `prestations_test`.
L'intégration continue (GitHub Actions) lance tout cela à chaque envoi, parcourt les deux
interfaces dans un vrai navigateur (`web/*/essais/`), puis construit les images Docker.

## Mettre en production

Sur un serveur avec Docker, et les sous-domaines `comptes.`, `boutique.` et `prestations.`
pointés vers lui :

```bash
cd infra
cp .env.example .env      # remplir : domaine, mots de passe, clés, numéro WhatsApp
docker compose up -d --build
docker compose exec comptes python -m comptes.outils creer-admin --telephone "76…" --nom "…"
# Équipe de la boutique (gestion des commandes) et soignants vérifiés (prix professionnel) :
docker compose exec comptes python -m comptes.outils attribuer-role --telephone "76…" --role boutique:admin
docker compose exec comptes python -m comptes.outils attribuer-role --telephone "66…" --role boutique:pro
docker compose exec comptes python -m comptes.outils attribuer-role --telephone "65…" --role boutique:atelier
# Prestations : la gestion (demandes, contrats, partenaires, relevés) et les agents de collecte.
docker compose exec comptes python -m comptes.outils attribuer-role --telephone "76…" --role prestations:admin
docker compose exec comptes python -m comptes.outils attribuer-role --telephone "77…" --role prestations:terrain
```

Un serveur déjà installé avant l'arrivée des prestations n'a pas encore leur base : la créer une
fois (`PRESTATIONS_DB_MOT_DE_PASSE` ajouté au `.env`), puis relancer `docker compose up -d` :

```bash
docker compose exec postgres psql -U postgres \
  -c "CREATE ROLE prestations LOGIN PASSWORD '…'" -c "CREATE DATABASE prestations OWNER prestations"
```

Avant le premier devis, renseigner dans `.env` l'adresse de la boutique (`BOUTIQUE_COORDONNEES`)
et les mentions légales (`BOUTIQUE_MENTIONS_LEGALES` : RCCM, NIF, régime fiscal).

Caddy obtient les certificats HTTPS tout seul. Les migrations s'appliquent au démarrage de
chaque service. Le service `boutique-envoi` expédie les SMS (fournisseur `journal` par défaut :
rien n'est envoyé tant que le compte Orange n'est pas configuré, voir `SMS_*` et `ORANGE_*` dans
`.env`) ; le service Comptes envoie avec le même compte les codes « mot de passe oublié » ; le
service `sauvegarde` sauvegarde les bases chaque nuit.

Le paiement mobile en ligne reste éteint (`BOUTIQUE_PAIEMENT_MOBILE=aucun`) tant que le compte
marchand CinetPay n'est pas ouvert : le client paie à la livraison. Pour l'ouvrir, renseigner
`BOUTIQUE_PAIEMENT_MOBILE=cinetpay`, `BOUTIQUE_CINETPAY_APIKEY` et `BOUTIQUE_CINETPAY_SITE_ID`,
puis faire un premier paiement réel de 100 FCFA. En local, `simulation` accepte tout paiement
sans argent réel (refusé en production).

Les articles faits à la demande (postes `broderie` et `impression` de l'atelier, ou tout article
personnalisé) demandent un acompte non remboursable de `BOUTIQUE_ACOMPTE_POURCENT` % de leur
prix (50 par défaut, 0 pour n'en demander aucun) ; la page des conditions de vente cite ce taux.
Le service `boutique-envoi` envoie en journée un rappel SMS quand l'acompte est attendu depuis 2
puis 7 jours (`BOUTIQUE_RELANCES_ACOMPTE_JOURS`), quand un devis sans réponse expire dans 3
jours (`BOUTIQUE_RELANCE_DEVIS_JOURS`), et quand une commande prête attend son retrait à la
boutique depuis 3 puis 7 jours (`BOUTIQUE_RELANCES_RETRAIT_JOURS`).

## État d'avancement

- [x] Socle, comptes, organisations, catalogue, interface de consultation, déploiement
- [x] Vitrine de tenues médicales : menu par métier et par type, filtres et facettes, pastilles de couleur, guide des tailles, broderie, nos autres services
- [x] Panier, commande, suivi par lien, devis PDF, paiement à la livraison, gestion (semaine 2)
- [x] File d'atelier sur tablette, capacité des postes, dates promises selon la charge, stock (semaine 3)
- [x] Livreurs et feuille de route, factures sans trou, SMS aux clients, revue de sécurité (semaine 4)
- [x] Paiement mobile en ligne par CinetPay (Orange Money, Moov Money), éteint jusqu'à l'ouverture du compte marchand
- [x] Avis clients vérifiés : réservés aux clients livrés, relus par l'équipe avant publication, note moyenne sur les fiches et les cartes
- [x] Mode hors ligne : application et catalogue enregistrés sur le téléphone, pages déjà vues, commande préparée sans réseau et envoyée à son retour
- [x] Mot de passe oublié (code par SMS) et « Mon compte » (changement du mot de passe)
- [x] Tableau de bord de l'équipe : ventes, encaissements, délais, devis, avis, meilleures ventes, alertes du jour
- [x] Durées de conservation appliquées chaque nuit (anonymisation, effacement), alertes SMS à l'équipe
- [x] Droits des personnes : téléchargement de ses données et suppression du compte
- [x] Projets de conditions de vente, politique de confidentialité et mentions légales (à faire valider)
- [x] Découverte visuelle : page « Explorer par couleur » (mur de couleurs, familles, métier, type, coupe), articles dessinés dans leur vraie couleur en attendant les photos, photo qui suit la couleur choisie
- [x] Recherche par la couleur d'une photo (calculée sur le téléphone, la photo n'est pas envoyée) ou d'une couleur choisie
- [x] Idées de tenues composées par l'équipe (« la tenue du bloc »…), sur la page Explorer et dans le composeur, gérées dans « Tenues proposées »
- [x] « Composer ma tenue » : haut, pantalon, blouse, chaussures et calot sur un mannequin, couleurs assorties, toute la tenue au panier, partage par WhatsApp
- [x] Exports CSV pour le comptable (factures, encaissements, commandes), depuis le tableau de bord
- [x] Codes promo : saisis au panier (motif affiché s'ils ne s'appliquent pas), vérifiés de nouveau à la commande, gérés par l'équipe (utilisations, remises accordées)
- [x] Correction des articles d'une commande par l'équipe avant la fabrication (taille, quantité, ajout, retrait) : prix d'origine gardé, tarif professionnel repris, total, acompte et code promo recalculés, trop-perçu signalé
- [x] Remboursements enregistrés (trop-perçu, annulation) : onglet « À rembourser », alerte du tableau de bord, SMS au client, sorties de caisse dans l'export des encaissements
- [x] Lien de paiement à envoyer à un proche (WhatsApp, partage, copie) : il voit le montant et les articles, ni téléphone ni adresse, et paie en ligne ; un nouveau lien remplace l'ancien
- [x] Tableau de bord : tailles (toute la gamme, zéros compris) et couleurs commandées sur la période, pour couper d'avance et réassortir
- [x] « Commander à nouveau » depuis une commande remise ou annulée : les articles encore proposés reviennent au panier (même broderie), le reste est signalé avec sa raison
- [x] Page d'une commande (équipe) : les autres commandes du même numéro (remises, annulées, montant, depuis quand)
- [x] Reçu par SMS de chaque paiement enregistré par l'équipe (espèces, transfert, chèque), preuve écrite pour l'argent remis en main propre
- [x] Atelier : étiquettes de fabrication en PDF (huit par page A4), une par pièce de la file, taille et couleur sur leur ligne, texte à broder ou à imprimer en entier
- [x] Taille habituelle retenue par rayon sur le téléphone, proposée d'office sur les autres articles du rayon
- [x] « Votre structure à vos couleurs » : le logo (lu sur le téléphone) donne la palette, la peinture RAL la plus proche pour les murs (façade dessinée) et l'équipe habillée à ces couleurs, logo brodé ; rendu partageable par lien, projet envoyé par WhatsApp
- [x] Rappels SMS automatiques : acompte attendu, devis bientôt expiré, commande prête pas retirée
- [x] Taille conseillée d'après ses mesures (fiche produit et guide des tailles) ; plan du site et robots.txt
- [x] Commande pour une équipe : le même article brodé au nom de chacun (liste saisie ou collée depuis un tableur), puis commande ou devis
- [x] Acompte non remboursable des articles faits à la demande : demandé à la confirmation, payé en ligne ou à la boutique, il lance la fabrication (clause à faire valider : acompte ou arrhes)
- [x] Prestations aux structures, d'abord l'entretien du linge avec des blanchisseries partenaires : demande en ligne avec estimation des volumes, contrat (jours de collecte propres à chaque structure ou sur appel, formule à la pièce ou au forfait), tournée du jour, linge compté à l'enlèvement et au retour avec un SMS de bon de collecte, pièces manquantes signalées, relevé mensuel PDF et marge par partenaire
- [ ] Pharmacien partenaire (janvier 2027)
