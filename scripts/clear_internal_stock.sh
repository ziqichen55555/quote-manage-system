#!/usr/bin/env bash
# Zero on-hand quantities for all stock in internal + transit locations.
# Does NOT delete the database, products, website, or sale orders.
# Uses Odoo inventory adjustment (same mechanism as Inventory app).
#
# Usage (from repo root, Docker stack running or compose file present):
#   ./scripts/clear_internal_stock.sh
# Optional: ODOO_DATABASE=mydb ./scripts/clear_internal_stock.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DB="${ODOO_DATABASE:-cocreativeit-quote}"

echo "Clearing internal/transit stock.quant quantities on database: ${DB}"
echo "Press Ctrl+C within 3s to abort..."
sleep 3

docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d "$DB" <<'PY'
from odoo.tools import float_is_zero

Quant = env["stock.quant"].sudo()
quants = Quant.search([("location_id.usage", "in", ("internal", "transit"))])
to_fix = quants.filtered(
    lambda q: not float_is_zero(q.quantity, precision_rounding=q.product_uom_id.rounding)
)
n = len(to_fix)
if not n:
    print("No non-zero quants in internal/transit locations; nothing to do.")
else:
    batch = 200
    done = 0
    for i in range(0, n, batch):
        chunk = to_fix[i : i + batch]
        chunk.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 0.0})
        env.cr.commit()
        done += len(chunk)
        print(f"Adjusted {done}/{n} quant lines...")
    print(f"Finished: {n} quant line(s) zeroed via inventory adjustment.")
PY

echo "Done. Import or adjust products next."
