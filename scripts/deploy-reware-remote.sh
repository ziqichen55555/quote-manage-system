#!/usr/bin/env bash
# Run ON the DigitalOcean server (/root/reware). No git repo required.
# GitHub Actions uploads custom_addons first, then calls this script.
set -euo pipefail

APP_DIR="${APP_DIR:-/root/reware}"
DB="${ODOO_DATABASE:-cocreativeit-quote}"
MODULE="${ODOO_MODULE:-quote_manage_ui}"
SYNC_SCRIPT="${SYNC_SCRIPT:-/tmp/sync_rw_templates.py}"

cd "$APP_DIR"
COMPOSE=(docker compose)
if [[ -f .env ]]; then
  COMPOSE+=(--env-file .env)
fi

log() { printf '[deploy-reware] %s\n' "$*"; }

mkdir -p backups
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="backups/db-${STAMP}.sql.gz"
log "Backing up ${DB} -> ${BACKUP_FILE}"
"${COMPOSE[@]}" exec -T db pg_dump -U odoo "$DB" | gzip > "$BACKUP_FILE"
find backups -name 'db-*.sql.gz' -mtime +14 -delete 2>/dev/null || true

log "Upgrading ${MODULE}..."
"${COMPOSE[@]}" run --rm web odoo \
  -c /etc/odoo/odoo.conf \
  -d "$DB" \
  -u "$MODULE" \
  --stop-after-init

if [[ -f "$SYNC_SCRIPT" ]]; then
  log "Syncing locked templates from XML..."
  "${COMPOSE[@]}" run --rm -T web odoo shell \
    -c /etc/odoo/odoo.conf \
    -d "$DB" \
    --stop-after-init < "$SYNC_SCRIPT"
else
  log "WARN: ${SYNC_SCRIPT} not found — skipping template sync"
fi

log "Restarting web + caddy..."
"${COMPOSE[@]}" restart web caddy
log "Done. Verify: https://app.reware-project.com"
