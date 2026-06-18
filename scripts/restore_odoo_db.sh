#!/usr/bin/env bash
# Restore Odoo DB from gzip pg_dump. OVERWRITES the database.
# Usage: ./scripts/restore_odoo_db.sh backups/db-....sql.gz
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BACKUP="${1:?Usage: restore_odoo_db.sh <backup.sql.gz>}"
DB="${ODOO_DATABASE:-cocreativeit-quote}"
if [[ ! -f "$BACKUP" ]]; then
  echo "Backup not found: $BACKUP" >&2
  exit 1
fi
echo "WARNING: This will REPLACE database ${DB}."
read -r -p "Type RESTORE to continue: " CONFIRM
if [[ "$CONFIRM" != "RESTORE" ]]; then
  echo "Aborted."
  exit 1
fi
docker compose stop web 2>/dev/null || true
docker compose exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB}' AND pid <> pg_backend_pid();"
docker compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS \"${DB}\";"
docker compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE \"${DB}\" OWNER odoo;"
gunzip -c "$BACKUP" | docker compose exec -T db psql -U odoo -d "$DB"
docker compose start web
echo "[restore] Done."
