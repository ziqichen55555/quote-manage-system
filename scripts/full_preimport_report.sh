#!/bin/bash
cd /root/reware
echo "=== ALL 113 active products with on-hand SN count (pre-import backup) ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
SELECT
  pt.id AS tmpl_id,
  pp.id AS variant_id,
  pt.default_code AS sku,
  LEFT(COALESCE(pt.name->>'en_US', pt.name::text), 55) AS name,
  pt.sale_ok,
  COALESCE(SUM(sq.quantity) FILTER (WHERE loc.usage='internal' AND sl.name NOT LIKE '%_INVALID%' AND sl.name NOT LIKE '%-OLD'), 0)::int AS on_hand_qty,
  COUNT(DISTINCT sl.name) FILTER (WHERE sq.quantity > 0 AND loc.usage='internal' AND sl.name NOT LIKE '%_INVALID%' AND sl.name NOT LIKE '%-OLD') AS sn_count
FROM product_template pt
JOIN product_product pp ON pp.product_tmpl_id = pt.id
LEFT JOIN stock_quant sq ON sq.product_id = pp.id
LEFT JOIN stock_lot sl ON sl.id = sq.lot_id
LEFT JOIN stock_location loc ON loc.id = sq.location_id
WHERE pt.active = true
GROUP BY pt.id, pp.id, pt.default_code, pt.name, pt.sale_ok
ORDER BY pt.default_code NULLS LAST, pt.id;
"

echo "=== FULL SN list (121 units) ==="
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
SELECT pt.default_code AS sku, sl.name AS serial, sq.quantity::int AS qty
FROM stock_quant sq
JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
JOIN stock_location loc ON loc.id = sq.location_id
WHERE sq.quantity > 0 AND loc.usage = 'internal' AND pt.active = true
  AND sl.name NOT LIKE '%_INVALID%' AND sl.name NOT LIKE '%-OLD'
ORDER BY pt.default_code, sl.name;
"
