# Règles du dépôt « sante »

Écosystème de santé Mali / AES : des produits séparés (boutique, studio, formation, portail,
campagnes, puis orientation médicale) sur un socle commun. Références :
- Dossier d'architecture consolidé : https://claude.ai/artifact/3uiNEZJkPX172JFeHChgWb
- Plan d'action et plan financier : https://claude.ai/artifact/PLemzatgVRdtA53zMcZqDS
- Dossier de projet : https://claude.ai/artifact/1RG4A9vTti9ycmD12kiJ98

## Structure

- `socle/` : paquet Python partagé (base, UUID v7, jetons, journaux, audit, fabrique d'application)
- `services/comptes/` : compte unique, connexion par téléphone, organisations (port 8001)
- `services/boutique/` : catalogue, puis commandes et atelier (port 8002)
- `services/prestations/` : services aux structures avec des partenaires, d'abord l'entretien du
  linge (demandes, contrats, tournée, collectes comptées, relevés ; port 8003)
- `web/` : interfaces Nuxt ; `web/charte/` est la couche commune, `web/boutique/` l'application
- `infra/` : Docker Compose, Caddy ; `docs/` : décisions d'architecture, marque (`docs/marque.md`)

La boutique s'appelle **Bibou**, « par Yasal Santé » (marque mère). Couleurs de Bibou dans
`web/boutique/app/assets/css/bibou.css`, celles de Yasal Santé dans la charte commune.

## Commandes

```bash
uv sync                                   # installe tout l'espace de travail
uv run ruff check . && uv run ruff format --check .
uv run mypy socle/src services/comptes/src services/boutique/src services/prestations/src
uv run pytest services/comptes            # un service à la fois
uv run pytest services/boutique
uv run pytest services/prestations
cd services/<service> && uv run alembic revision --autogenerate -m "..."   # puis relire
```

Les tests utilisent une vraie base PostgreSQL 16 (`comptes_test`, `boutique_test`,
`prestations_test` sur localhost, utilisateur `postgres`) ; les URL se changent avec
`COMPTES_TEST_DATABASE_URL`, `BOUTIQUE_TEST_DATABASE_URL` et `PRESTATIONS_TEST_DATABASE_URL`.

## Règles

- **Un produit, une base** : jamais de lecture dans la base d'un autre produit ; API ou événements.
- **Noms métier en français** (modèles, routes /api/v1/produits, messages d'erreur) ; la
  plomberie technique peut rester en anglais.
- **Identifiants** : `socle.uuid7()` partout ; montants en FCFA, en entiers ; téléphones en E.164.
- **Toute écriture sensible est journalisée** avec `socle.audit.journaliser`, dans la même
  transaction.
- **Données de santé interdites** hors du futur service d'orientation médicale (infrastructure
  séparée, hébergée au Mali, après autorisation de l'APDP).
- **Boutique** : un produit de catégorie « pharmaceutique » (décret n° 04-557) n'est jamais
  vendu en ligne ni affiché avec un prix ; il passe par le pharmacien partenaire.
- **Asynchrone** : relations SQLAlchemy en `lazy="raise"`, chargées explicitement
  (`selectinload`, `contains_eager`).
- **Chaque changement arrive avec ses tests** ; ruff, mypy et pytest doivent passer.
- **Migrations** générées par Alembic puis relues ; jamais modifiées une fois publiées.
- **Aucun secret dans le dépôt** ; `.env.example` documente les variables.
- Code écrit avec Claude : petits lots, relus et compris par un développeur avant la production.
