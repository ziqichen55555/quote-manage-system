#!/usr/bin/env bash
# 生产环境升级 quote_manage_ui（配合 docker-compose.prod.yml）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env"
DB="${ODOO_DATABASE:-cocreativeit-quote}"
MODULE="${ODOO_MODULE:-quote_manage_ui}"

if [[ ! -f .env ]]; then
  echo "缺少 .env，请先部署: ./scripts/deploy-prod-duckdns.sh"
  exit 1
fi

echo "Upgrading ${MODULE} on ${DB} ..."
eval "${COMPOSE}" run --rm web odoo \
  -c /etc/odoo/odoo.conf \
  -d "${DB}" \
  -u "${MODULE}" \
  --stop-after-init

echo "Syncing locked snippet/template views ..."
eval "${COMPOSE}" run --rm -T web odoo shell \
  -c /etc/odoo/odoo.conf \
  -d "${DB}" \
  --stop-after-init < scripts/sync_rw_templates.py

eval "${COMPOSE}" restart web caddy
echo "Done."
