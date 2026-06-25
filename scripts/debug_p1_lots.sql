SELECT pt.default_code, sl.name AS lot_name, sq.quantity, sl.id AS lot_id
FROM stock_lot sl
JOIN product_product pp ON pp.id = sl.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
LEFT JOIN stock_quant sq ON sq.lot_id = sl.id AND sq.quantity != 0
WHERE pt.default_code LIKE '20TJS5WW00%'
   OR sl.name LIKE '%20TJS5WW00%'
ORDER BY pt.default_code, sl.name;
