#!/usr/bin/env bash
# Remove catalog products (draft SO/PO, open pickings, quants, then unlink templates).
# Destructive. Default DB: cocreativeit-quote
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB="${ODOO_DATABASE:-cocreativeit-quote}"
echo "Wiping product catalog on ${DB} (draft sale orders will be deleted)..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d "$DB" <<'PY'
exec(open("/mnt/custom-addons/quote_manage_ui/scripts/wipe_catalog_products.py").read())
PY
echo "Done."
