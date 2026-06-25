-- When was 20TJS5WW00 created, and lot history
SELECT pt.id, pt.default_code, pt.create_date, pt.write_date, pt.list_price
FROM product_template pt
WHERE pt.default_code LIKE '20TJS5WW00%'
ORDER BY pt.create_date;

SELECT sl.id, sl.name, sl.create_date, pt.default_code AS product_sku, sq.quantity, sloc.complete_name AS location
FROM stock_lot sl
JOIN product_product pp ON pp.id = sl.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
LEFT JOIN stock_quant sq ON sq.lot_id = sl.id
LEFT JOIN stock_location sloc ON sloc.id = sq.location_id
WHERE sl.name IN ('S/N-20TJS5WW00-001', 'R913RZGT')
   OR pt.default_code LIKE '20TJS5WW00%'
ORDER BY sl.create_date;
