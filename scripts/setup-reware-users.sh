#!/usr/bin/env bash
# Create Re-Ware company users on the DigitalOcean Odoo instance.
# Usage (on server): cd /root/reware && ./scripts/setup-reware-users.sh
# Optional: TEMP_PASSWORD=... ./scripts/setup-reware-users.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/root/reware}"
DB="${ODOO_DATABASE:-cocreativeit-quote}"
TEMP_PASSWORD="${TEMP_PASSWORD:-ReWare-2026!}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$APP_DIR"
COMPOSE=(docker compose)
if [[ -f .env ]]; then
  COMPOSE+=(--env-file .env)
fi

# Back up first — this touches the admin account.
mkdir -p backups
STAMP="$(date +%Y%m%d-%H%M%S)"
"${COMPOSE[@]}" exec -T db pg_dump -U odoo "$DB" | gzip > "backups/db-users-${STAMP}.sql.gz"
printf '[setup-reware-users] Backup: backups/db-users-%s.sql.gz\n' "$STAMP"

export TEMP_PASSWORD
"${COMPOSE[@]}" run --rm -T web odoo shell \
  -c /etc/odoo/odoo.conf \
  -d "$DB" \
  --stop-after-init < "${SCRIPT_DIR}/setup_reware_users.py"

printf '[setup-reware-users] Done.\n'
