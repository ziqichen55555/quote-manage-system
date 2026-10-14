#!/bin/bash
set -euo pipefail
cd /root/reware
OUT=/root/reware/backups/preimport_inventory_20260911_0420.csv

echo "=== Product counts ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
SELECT
  COUNT(*) FILTER (WHERE active) AS active_all,
  COUNT(*) FILTER (WHERE active AND sale_ok) AS active_sale_ok,
  COUNT(*) FILTER (WHERE active AND default_code IS NOT NULL AND default_code != '') AS active_with_sku
FROM product_template;
"

echo "=== Export CSV ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
COPY (
SELECT
  pp.id AS variant_id,
  pt.default_code AS sku,
  pt.name->>'en_US' AS product_name,
  pt.sale_ok,
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
  AND sl.name NOT LIKE '%_INVALID%'
  AND sl.name NOT LIKE '%-OLD'
ORDER BY pt.default_code, sl.name
) TO STDOUT WITH CSV HEADER;
" > "$OUT"

echo "Lines: $(wc -l < "$OUT")"
echo "=== Totals ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
SELECT COUNT(DISTINCT pt.id) AS products, COUNT(DISTINCT sl.name) AS serials, SUM(sq.quantity)::int AS units
FROM stock_quant sq
JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
JOIN stock_location loc ON loc.id = sq.location_id
WHERE sq.quantity > 0 AND loc.usage = 'internal' AND pt.active = true
  AND pt.default_code IS NOT NULL AND pt.default_code != ''
  AND sl.name NOT LIKE '%_INVALID%' AND sl.name NOT LIKE '%-OLD';
"

echo "=== By SKU ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
SELECT pt.default_code AS sku, COUNT(DISTINCT sl.name) AS sn_count, SUM(sq.quantity)::int AS qty
FROM stock_quant sq
JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
JOIN stock_location loc ON loc.id = sq.location_id
WHERE sq.quantity > 0 AND loc.usage = 'internal' AND pt.active = true
  AND pt.default_code IS NOT NULL AND pt.default_code != ''
  AND sl.name NOT LIKE '%_INVALID%' AND sl.name NOT LIKE '%-OLD'
GROUP BY pt.default_code ORDER BY pt.default_code;
"
