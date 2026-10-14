#!/bin/bash
cd /root/reware
OUT=/root/reware/backups/preimport_inventory_20260911_0420.csv
set -x
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "
COPY (
SELECT pp.id, pt.default_code, sl.name, sq.quantity::int
FROM stock_quant sq
JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
JOIN stock_location loc ON loc.id = sq.location_id
WHERE sq.quantity > 0 AND loc.usage = 'internal' AND pt.active = true
ORDER BY pt.default_code, sl.name
) TO STDOUT WITH CSV HEADER;
" > "$OUT" 2>/tmp/export_err.txt
echo exit=$?
wc -l "$OUT"
cat /tmp/export_err.txt
