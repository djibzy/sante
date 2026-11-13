# Sauvegardes : outils de PostgreSQL 16, age (chiffrement) et rclone (copie hors du serveur).
FROM postgres:16
RUN apt-get update \
    && apt-get install -y --no-install-recommends age rclone ca-certificates \
    && rm -rf /var/lib/apt/lists/*
