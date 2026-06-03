#!/usr/bin/env bash
# Production deploy for quote_manage_ui (and mounted custom_addons).
#
# Run on the server after `git pull`, or let GitHub Actions SSH in and run this.
# Requires: docker compose, repo at $APP_DIR, .env for docker-compose.prod.yml
#
# Usage (on server):
#   cd /path/to/quote-manage-system
#   ./scripts/deploy-prod.sh
#
# Optional env:
#   APP_DIR=/home/ubuntu/quote-manage-system
#   SKIP_BACKUP=1          # skip pg_dump before upgrade
#   ODOO_DATABASE=cocreativeit-quote
#   ODOO_MODULE=quote_manage_ui
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$APP_DIR"

COMPOSE=(docker compose -f docker-compose.prod.yml)
if [[ -f .env ]]; then
  COMPOSE+=(--env-file .env)
fi

DB="${ODOO_DATABASE:-cocreativeit-quote}"
MODULE="${ODOO_MODULE:-quote_manage_ui}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/quote-manage-system}"

log() { printf '[deploy] %s\n' "$*"; }

if [[ "${SKIP_BACKUP:-0}" != "1" ]]; then
  mkdir -p "$BACKUP_DIR"
  STAMP="$(date +%Y%m%d-%H%M%S)"
  BACKUP_FILE="$BACKUP_DIR/db-${STAMP}.sql.gz"
  log "Backing up database ${DB} -> ${BACKUP_FILE}"
  "${COMPOSE[@]}" exec -T db pg_dump -U odoo "$DB" | gzip > "$BACKUP_FILE"
  find "$BACKUP_DIR" -name 'db-*.sql.gz' -mtime +14 -delete 2>/dev/null || true
else
  log "SKIP_BACKUP=1 — skipping database backup"
fi

log "Upgrading module ${MODULE} on database ${DB}..."
"${COMPOSE[@]}" run --rm web odoo \
  -c /etc/odoo/odoo.conf \
  -d "$DB" \
  -u "$MODULE" \
  --stop-after-init

log "Syncing locked website templates from XML..."
"${COMPOSE[@]}" run --rm -T web odoo shell \
  -c /etc/odoo/odoo.conf \
  -d "$DB" \
  --stop-after-init < scripts/sync_rw_templates.py

log "Restarting web + caddy..."
"${COMPOSE[@]}" restart web caddy

log "Done. Verify: https://${SITE_HOSTNAME:-your-domain}"
