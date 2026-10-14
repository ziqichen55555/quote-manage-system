#!/bin/bash
set -euo pipefail
cd /root/reware
BACKUP=/root/reware/backups/db-20260911-042017.sql.gz

docker compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS preimport_sep11;"
docker compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE preimport_sep11;"
echo "Restoring backup..."
gunzip -c "$BACKUP" | docker compose exec -T db psql -U odoo -d preimport_sep11 -q
echo "Restore complete. Product count:"
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "SELECT COUNT(*) FROM product_template;"

echo "=== SUMMARY BY SKU (pre-import 2026-09-11 04:20 UTC) ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
SELECT
  pt.default_code AS sku,
  LEFT(pt.name->>'en_US', 50) AS name,
  COUNT(DISTINCT sl.name) AS sn_count,
  SUM(sq.quantity)::int AS total_qty
FROM stock_quant sq
JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
JOIN stock_location loc ON loc.id = sq.location_id
WHERE sq.quantity > 0
  AND loc.usage = 'internal'
  AND pt.active = true
  AND pt.default_code IS NOT NULL
  AND pt.default_code != ''
GROUP BY pt.default_code, pt.name
ORDER BY pt.default_code;
"

echo "=== FULL SN LIST ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
COPY (
SELECT
  pt.default_code AS sku,
  sl.name AS serial,
  sq.quantity::int AS qty
FROM stock_quant sq
JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
JOIN stock_location loc ON loc.id = sq.location_id
WHERE sq.quantity > 0
  AND loc.usage = 'internal'
  AND pt.active = true
  AND pt.default_code IS NOT NULL
  AND pt.default_code != ''
ORDER BY pt.default_code, sl.name
) TO STDOUT WITH CSV HEADER;
"

echo "=== TOTALS ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
SELECT
  COUNT(DISTINCT pt.id) AS products,
  COUNT(DISTINCT sl.name) AS serials,
  SUM(sq.quantity)::int AS units
FROM stock_quant sq
JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
JOIN stock_location loc ON loc.id = sq.location_id
WHERE sq.quantity > 0
  AND loc.usage = 'internal'
  AND pt.active = true
  AND pt.default_code IS NOT NULL
  AND pt.default_code != '';
"
