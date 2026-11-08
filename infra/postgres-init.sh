#!/bin/sh
# Premier démarrage de PostgreSQL : une base et un rôle par produit (jamais de base partagée).
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<EOSQL
CREATE ROLE comptes LOGIN PASSWORD '${COMPTES_DB_MOT_DE_PASSE}';
CREATE DATABASE comptes OWNER comptes;
CREATE ROLE boutique LOGIN PASSWORD '${BOUTIQUE_DB_MOT_DE_PASSE}';
CREATE DATABASE boutique OWNER boutique;
EOSQL
