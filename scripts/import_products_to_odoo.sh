#!/usr/bin/env bash
# Import products from quote_manage_ui/data/product_import_ready.csv (copy from repo root after
# running: python3 scripts/normalize_product_md.py && cp product_import_ready.csv quote-manage-system/custom_addons/quote_manage_ui/data/)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB="${ODOO_DATABASE:-cocreativeit-quote}"
echo "Importing products into ${DB} from CSV..."
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d "$DB" <<'PY'
exec(open("/mnt/custom-addons/quote_manage_ui/scripts/import_product_csv.py").read())
PY
echo "Done."
