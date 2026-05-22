#!/usr/bin/env bash
# Upgrade quote_manage_ui via Docker (no Apps UI click).
#
# Default database: cocreativeit-quote (your single Odoo DB).
#   ./scripts/upgrade-quote-manage-ui.sh
#
# Only set ODOO_DATABASE if you really have a second database name — do not
# use placeholder values like "other_db" unless that is the actual DB name.
# 默认已指向 cocreativeit-quote；若只有一个库，直接运行脚本即可，不必设环境变量。
#
# Optional: ODOO_DATABASE=real_db_name ODOO_MODULE=quote_manage_ui ./scripts/upgrade-quote-manage-ui.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DB="${ODOO_DATABASE:-cocreativeit-quote}" 
MODULE="${ODOO_MODULE:-quote_manage_ui}"

echo "Upgrading module ${MODULE} on database ${DB}..."
docker compose run --rm web odoo -c /etc/odoo/odoo.conf -d "$DB" -u "$MODULE" --stop-after-init
echo "Syncing locked snippet/template views from XML..."
docker compose run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d "$DB" --stop-after-init < scripts/sync_rw_templates.py
docker compose restart web nginx
echo "Done."
