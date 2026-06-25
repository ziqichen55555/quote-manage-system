SELECT sq.id, pt.default_code, sl.name, sq.quantity, sloc.complete_name
FROM stock_quant sq
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
LEFT JOIN stock_lot sl ON sl.id = sq.lot_id
JOIN stock_location sloc ON sloc.id = sq.location_id
WHERE pt.default_code LIKE '30B%' OR sl.name = 'PC0MDC46';
