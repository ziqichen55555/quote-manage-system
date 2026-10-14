#!/bin/bash
cd /root/reware
OUT=/root/reware/backups/preimport_sn_clean_20260911_0420.csv
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
COPY (
SELECT
  pt.id AS tmpl_id,
  pp.id AS variant_id,
  pt.default_code AS sku,
  pt.name->>'en_US' AS product_name,
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
  AND sl.name NOT LIKE '%_INVALID%'
  AND sl.name NOT LIKE '%-OLD'
ORDER BY pt.default_code NULLS LAST, sl.name
) TO STDOUT WITH CSV HEADER;
" > "$OUT"
echo "lines=$(wc -l < "$OUT")"
docker compose exec -T db psql -U odoo -d preimport_sep11 -t -c "
SELECT SUM(sq.quantity)::int FROM stock_quant sq
JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
JOIN stock_location loc ON loc.id = sq.location_id
WHERE sq.quantity > 0 AND loc.usage = 'internal' AND pt.active = true
  AND sl.name NOT LIKE '%_INVALID%' AND sl.name NOT LIKE '%-OLD';
"
