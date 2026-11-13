#!/bin/sh
# Sauvegarde quotidienne des bases (format personnalisé de pg_dump, restaurable avec
# pg_restore) et des photos des produits, puis suppression des fichiers plus anciens que
# JOURS_CONSERVES.
#
# Copie hors du serveur (si COPIE_DISTANTE et AGE_DESTINATAIRE sont renseignés) : chaque
# fichier du jour est chiffré pour la clé publique « age » (la clé privée reste hors du
# serveur), envoyé avec rclone, et les copies distantes de plus de JOURS_DISTANTS sont effacées.
set -eu
D=${DOSSIER:-/sauvegardes}
M=${MEDIAS:-/medias}
while true; do
  jour=$(date +%Y-%m-%d)
  for base in $BASES; do
    fichier="$D/${base}-${jour}.dump"
    pg_dump --format=custom --file="${fichier}.partiel" "$base" && mv "${fichier}.partiel" "$fichier"
    echo "Sauvegarde de ${base} : ${fichier}"
  done
  if [ -d "$M" ]; then
    tar -czf "$D/medias-${jour}.tar.gz" -C "$M" . && echo "Sauvegarde des photos"
  fi
  find "$D" \( -name '*.dump' -o -name '*.tar.gz' \) -mtime +"$JOURS_CONSERVES" -delete
  if [ -n "${COPIE_DISTANTE:-}" ] && [ -n "${AGE_DESTINATAIRE:-}" ]; then
    for f in "$D"/*-"${jour}".dump "$D"/medias-"${jour}".tar.gz; do
      if [ -f "$f" ]; then
        age --recipient "$AGE_DESTINATAIRE" --output "${f}.age" "$f" || echo "ÉCHEC du chiffrement de $f" >&2
      fi
    done
    if rclone copy "$D" "$COPIE_DISTANTE" --include "*-${jour}.*.age"; then
      echo "Copie chiffrée envoyée vers ${COPIE_DISTANTE}"
      rclone delete "$COPIE_DISTANTE" --min-age "${JOURS_DISTANTS:-90}d" || true
    else
      echo "ÉCHEC de la copie hors du serveur : les sauvegardes restent sur le serveur" >&2
    fi
    rm -f "$D"/*.age
  fi
  # Sauvegarde immédiate, à la main : docker compose exec sauvegarde env UNE_FOIS=1 sh /sauvegarde.sh
  [ -n "${UNE_FOIS:-}" ] && break
  sleep 86400
done
