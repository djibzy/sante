#!/bin/sh
# Essai de restauration : chaque base est restaurée depuis sa dernière sauvegarde dans une base
# temporaire, contrôlée (tables, version des migrations, lignes), puis effacée ; l'archive des
# photos est relue. À lancer au moins une fois par mois :
#   docker compose exec sauvegarde sh /essai-restauration.sh
set -eu
DOSSIER=${DOSSIER:-/sauvegardes}
statut=0
compter() { psql -tAc "SELECT count(*) FROM $1" "$2"; }

for base in $BASES; do
  dernier=$(ls -1t "$DOSSIER/${base}-"*.dump 2>/dev/null | head -n 1 || true)
  if [ -z "$dernier" ]; then
    echo "ÉCHEC ${base} : aucune sauvegarde dans ${DOSSIER}" >&2
    statut=1
    continue
  fi
  essai="essai_restauration_${base}"
  PGOPTIONS="-c client_min_messages=warning" dropdb --if-exists "$essai"
  createdb "$essai"
  if pg_restore --no-owner --no-privileges --exit-on-error --dbname="$essai" "$dernier"; then
    tables=$(psql -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" "$essai")
    version=$(psql -tAc "SELECT version_num FROM alembic_version" "$essai")
    echo "OK ${base} : $(basename "$dernier"), ${tables} tables, migration ${version}"
    case "$base" in
      comptes) echo "   comptes : $(compter utilisateurs "$essai")" ;;
      boutique) echo "   produits : $(compter produits "$essai"), commandes : $(compter commandes "$essai"), factures : $(compter factures "$essai")" ;;
    esac
  else
    echo "ÉCHEC ${base} : la restauration de $(basename "$dernier") a échoué" >&2
    statut=1
  fi
  PGOPTIONS="-c client_min_messages=warning" dropdb --if-exists "$essai"
done

photos=$(ls -1t "$DOSSIER"/medias-*.tar.gz 2>/dev/null | head -n 1 || true)
if [ -n "$photos" ]; then
  if nombre=$(tar -tzf "$photos" | grep -c '\.webp$'); then
    echo "OK photos : $(basename "$photos"), ${nombre} photo(s)"
  else
    echo "OK photos : $(basename "$photos"), aucune photo encore"
  fi
fi
exit $statut
