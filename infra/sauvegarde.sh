#!/bin/sh
# Sauvegarde quotidienne des bases (format personnalisé de pg_dump, restaurable avec
# pg_restore) et des photos des produits, puis suppression des fichiers plus anciens que
# JOURS_CONSERVES.
set -eu
while true; do
  jour=$(date +%Y-%m-%d)
  for base in $BASES; do
    fichier="/sauvegardes/${base}-${jour}.dump"
    pg_dump --format=custom --file="${fichier}.partiel" "$base" && mv "${fichier}.partiel" "$fichier"
    echo "Sauvegarde de ${base} : ${fichier}"
  done
  if [ -d /medias ]; then
    tar -czf "/sauvegardes/medias-${jour}.tar.gz" -C /medias . && echo "Sauvegarde des photos"
  fi
  find /sauvegardes \( -name '*.dump' -o -name '*.tar.gz' \) -mtime +"$JOURS_CONSERVES" -delete
  sleep 86400
done
