#!/usr/bin/env bash
set -euo pipefail
cd /root/reware
BACKUP="${1:-backups/db-before-import-20260618-023459.sql.gz}"
DB="cocreativeit-quote"
echo "[restore] Using backup: $BACKUP"
docker compose --env-file .env stop web
docker compose --env-file .env exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB}' AND pid <> pg_backend_pid();"
docker compose --env-file .env exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS \"${DB}\";"
docker compose --env-file .env exec -T db psql -U odoo -d postgres -c "CREATE DATABASE \"${DB}\" OWNER odoo;"
gunzip -c "$BACKUP" | docker compose --env-file .env exec -T db psql -U odoo -d "$DB" -q
docker compose --env-file .env start web
echo "[restore] Done."
