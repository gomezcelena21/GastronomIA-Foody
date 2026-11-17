#!/bin/sh
# GastronomIA - restauración de un backup .sql.gz generado por deploy/backup.sh.
#
# Uso:
#   ./deploy/restore.sh /backups/gastro_ia_2026-11-09_030000.sql.gz
#   DATABASE_URL=postgresql://... ./deploy/restore.sh /ruta/backup.sql.gz
#
# ADVERTENCIA: el backup incluye DROP/CREATE (--clean). Restaurar sobre la base
# de producción reemplaza las tablas existentes. Hacé siempre un backup antes.
set -eu

ARCHIVO="${1:-}"
if [ -z "$ARCHIVO" ]; then
  echo "Uso: $0 /ruta/al/backup.sql.gz" >&2
  exit 2
fi
if [ ! -f "$ARCHIVO" ]; then
  echo "No existe el archivo: $ARCHIVO" >&2
  exit 2
fi
if [ -f "$ARCHIVO.sha256" ] && command -v sha256sum >/dev/null 2>&1; then
  (cd "$(dirname "$ARCHIVO")" && sha256sum -c "$(basename "$ARCHIVO").sha256")
fi
if ! gzip -t "$ARCHIVO"; then
  echo "El archivo no es un gzip válido." >&2
  exit 2
fi

echo "Restaurando $ARCHIVO ..."
if [ -n "${DATABASE_URL:-}" ]; then
  gunzip -c "$ARCHIVO" | psql "$DATABASE_URL" --set ON_ERROR_STOP=on
else
  : "${PGPASSWORD:?Definí PGPASSWORD o DATABASE_URL}"
  gunzip -c "$ARCHIVO" | psql \
    --host "${PGHOST:-db}" \
    --port "${PGPORT:-5432}" \
    --username "${PGUSER:-gastro}" \
    --dbname "${PGDATABASE:-gastro_ia}" \
    --set ON_ERROR_STOP=on
fi
echo "Restauración terminada. Verificá /health y el conteo de restaurants."
