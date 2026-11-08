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
[décisions](docs/decisions.md).

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
```

Avant le premier devis, renseigner dans `.env` l'adresse de la boutique (`BOUTIQUE_COORDONNEES`)
et les mentions légales (`BOUTIQUE_MENTIONS_LEGALES` : RCCM, NIF, régime fiscal).

Caddy obtient les certificats HTTPS tout seul. Les migrations s'appliquent au démarrage de
chaque service.

## État d'avancement

- [x] Socle, comptes, organisations, catalogue, interface de consultation, déploiement
- [x] Panier, commande, suivi par lien, devis PDF, paiement à la livraison, gestion (semaine 2)
- [ ] File d'atelier sur tablette et stock (semaine 3)
- [ ] Livraisons, factures, notifications, revue de sécurité (semaine 4)
- [ ] Paiement mobile (Orange Money, Moov Money) et pharmacien partenaire (janvier 2027)
