#!/usr/bin/env bash
# Backup Odoo PostgreSQL database before product import.
# Usage: ./scripts/backup_odoo_db.sh [label]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB="${ODOO_DATABASE:-cocreativeit-quote}"
LABEL="${1:-manual}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p backups
OUT="backups/db-${LABEL}-${STAMP}.sql.gz"
echo "[backup] Database: ${DB}"
echo "[backup] Writing: ${OUT}"
docker compose exec -T db pg_dump -U odoo "$DB" | gzip > "$OUT"
echo "[backup] Done. Restore: ./scripts/restore_odoo_db.sh ${OUT}"
