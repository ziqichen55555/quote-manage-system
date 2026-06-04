#!/usr/bin/env bash
# Set web.base.url on the DigitalOcean Odoo instance.
# Usage (on server): cd /root/reware && ./scripts/set-odoo-web-base-url.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/root/reware}"
DB="${ODOO_DATABASE:-cocreativeit-quote}"
WEB_BASE_URL="${WEB_BASE_URL:-https://www.reware-project.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$APP_DIR"
COMPOSE=(docker compose)
if [[ -f .env ]]; then
  COMPOSE+=(--env-file .env)
fi

export WEB_BASE_URL
"${COMPOSE[@]}" run --rm -T web odoo shell \
  -c /etc/odoo/odoo.conf \
  -d "$DB" \
  --stop-after-init < "${SCRIPT_DIR}/set_odoo_web_base_url.py"

printf '[set-odoo-web-base-url] Done: %s\n' "$WEB_BASE_URL"
