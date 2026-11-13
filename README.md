# Yasal Santé : écosystème de santé (Mali, puis AES)

Information, formation et équipement de santé, en produits séparés reliés par un socle commun.
Ce dépôt contient, pour commencer, le socle, le service de comptes et **Bibou**, la boutique
(tenues brodées, imprimés, kits et matériel). Marque et logos : [docs/marque.md](docs/marque.md).

| Dossier | Contenu | Port local |
| --- | --- | --- |
| `socle/` | Code partagé : base de données, identifiants, jetons, journaux, audit | |
| `services/comptes/` | Compte unique : inscription et connexion par téléphone, organisations | 8001 |
| `services/boutique/` | Catalogue, panier, commandes, devis PDF, paiements, zones de livraison | 8002 |
| `web/boutique/` | Interface de Bibou (Nuxt), avec la charte commune de `web/charte/` | 3000 |
| `infra/` | Mise en production : Docker Compose, Caddy, PostgreSQL | |

Documents de référence : [dossier de projet](https://claude.ai/artifact/1RG4A9vTti9ycmD12kiJ98),
[plan d'action et financier](https://claude.ai/artifact/PLemzatgVRdtA53zMcZqDS),
[dossier d'architecture](https://claude.ai/artifact/3uiNEZJkPX172JFeHChgWb),
[décisions](docs/decisions.md), [sécurité](docs/securite.md).

## Lancer en local

Prérequis : [uv](https://docs.astral.sh/uv/), PostgreSQL 16 (utilisateur `postgres` sans mot de
passe sur localhost, bases `comptes` et `boutique`), Node.js 22.

```bash
uv sync
uv run python -m comptes.outils generer-cles        # copier les lignes dans un fichier .env
(cd services/comptes && uv run alembic upgrade head)
(cd services/boutique && uv run alembic upgrade head)
uv run python -m boutique.donnees_demo               # catalogue de démonstration

uv run uvicorn comptes.main:creer_app --factory --port 8001
uv run uvicorn boutique.main:creer_app --factory --port 8002
cd web/boutique && npm install && npm run dev        # http://localhost:3000
```

Pour que l'interface parle aux API en local, ajouter au `.env` :
`COMPTES_COOKIE_SECURISE=false`, `COMPTES_CORS_ORIGINES=["http://localhost:3000"]` et
`BOUTIQUE_CORS_ORIGINES=["http://localhost:3000"]`.

Documentation des API : http://localhost:8001/docs et http://localhost:8002/docs.

## Vérifier

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy socle/src services/comptes/src services/boutique/src
uv run pytest services/comptes
uv run pytest services/boutique
```

Les tests utilisent les bases `comptes_test` et `boutique_test`. L'intégration continue
(GitHub Actions) lance tout cela à chaque envoi, puis construit les images Docker.

## Mettre en production

Sur un serveur avec Docker, et les sous-domaines `comptes.` et `boutique.` pointés vers lui :

```bash
cd infra
cp .env.example .env      # remplir : domaine, mots de passe, clés, numéro WhatsApp
docker compose up -d --build
docker compose exec comptes python -m comptes.outils creer-admin --telephone "76…" --nom "…"
# Équipe de la boutique (gestion des commandes) et soignants vérifiés (prix professionnel) :
docker compose exec comptes python -m comptes.outils attribuer-role --telephone "76…" --role boutique:admin
docker compose exec comptes python -m comptes.outils attribuer-role --telephone "66…" --role boutique:pro
docker compose exec comptes python -m comptes.outils attribuer-role --telephone "65…" --role boutique:atelier
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
- [x] Acompte non remboursable des articles faits à la demande : demandé à la confirmation, payé en ligne ou à la boutique, il lance la fabrication (clause à faire valider : acompte ou arrhes)
- [ ] Pharmacien partenaire (janvier 2027)
