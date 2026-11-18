#!/bin/sh
# GastronomIA - backup comprimido de PostgreSQL/PostGIS.
#
# Uso puntual:
#   ./deploy/backup.sh
#   DATABASE_URL=postgresql://... ./deploy/backup.sh
#
# Modo servicio (un backup cada BACKUP_INTERVALO segundos):
#   ./deploy/backup.sh --loop
#
# Variables:
#   DATABASE_URL       cadena completa (Neon, Supabase, etc.)
#   PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE   si no usás DATABASE_URL
#   BACKUP_DIR         carpeta destino (por defecto /backups)
#   BACKUP_RETENER_DIAS  días a conservar (por defecto 14)
#   BACKUP_INTERVALO   segundos entre backups en modo --loop (por defecto 86400)
set -eu

# Los backups contienen datos personales (usuarios, sesiones, reseñas): el
# archivo se crea solo para su dueño y la carpeta queda cerrada al resto.
umask 077

DIR="${BACKUP_DIR:-/backups}"
RETENER="${BACKUP_RETENER_DIAS:-14}"
INTERVALO="${BACKUP_INTERVALO:-86400}"
PREFIJO="${BACKUP_PREFIJO:-gastro_ia}"

mkdir -p "$DIR"
chmod 700 "$DIR" 2>/dev/null || true

hacer_backup() {
  STAMP=$(date +%Y-%m-%d_%H%M%S)
  ARCHIVO="$DIR/${PREFIJO}_${STAMP}.sql.gz"
  echo "[$(date -Iseconds)] Iniciando backup en $ARCHIVO"

  if [ -n "${DATABASE_URL:-}" ]; then
    pg_dump "$DATABASE_URL" --no-owner --no-privileges --clean --if-exists | gzip -9 > "$ARCHIVO"
  else
    : "${PGPASSWORD:?Definí PGPASSWORD o DATABASE_URL}"
    pg_dump \
      --host "${PGHOST:-db}" \
      --port "${PGPORT:-5432}" \
      --username "${PGUSER:-gastro}" \
      --dbname "${PGDATABASE:-gastro_ia}" \
      --no-owner --no-privileges --clean --if-exists | gzip -9 > "$ARCHIVO"
  fi

  # Un backup vacío es peor que no tener backup: se descarta y falla el servicio.
  if [ ! -s "$ARCHIVO" ]; then
    rm -f "$ARCHIVO"
    echo "[$(date -Iseconds)] ERROR: el backup quedó vacío" >&2
    return 1
  fi

  # Verifica que el gzip se pueda leer completo.
  if ! gzip -t "$ARCHIVO" 2>/dev/null; then
    rm -f "$ARCHIVO"
    echo "[$(date -Iseconds)] ERROR: el backup está corrupto" >&2
    return 1
  fi

  # El checksum guarda solo el nombre del archivo (no la ruta absoluta), así la
  # restauración funciona aunque el backup se haya movido de carpeta.
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$DIR" && sha256sum "$(basename "$ARCHIVO")") > "$ARCHIVO.sha256"
  elif command -v shasum >/dev/null 2>&1; then
    (cd "$DIR" && shasum -a 256 "$(basename "$ARCHIVO")") > "$ARCHIVO.sha256"
  fi

  # Borra backups viejos (solo los del mismo prefijo).
  find "$DIR" -maxdepth 1 -type f -name "${PREFIJO}_*.sql.gz*" -mtime "+$RETENER" -delete 2>/dev/null || true

  TAMANO=$(du -h "$ARCHIVO" | cut -f1)
  echo "[$(date -Iseconds)] Backup OK ($TAMANO): $ARCHIVO"
}

if [ "${1:-}" = "--loop" ]; then
  echo "Servicio de backups activo: cada $INTERVALO segundos, retención $RETENER días."
  while true; do
    hacer_backup || echo "[$(date -Iseconds)] El backup falló; se reintenta en el próximo ciclo." >&2
    sleep "$INTERVALO"
  done
else
  hacer_backup
fi
