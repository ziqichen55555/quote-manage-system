SELECT pt.id, pt.default_code, pt.is_published, pt.tracking,
       (SELECT sum(sq.quantity) FROM stock_quant sq
        JOIN product_product pp ON pp.id = sq.product_id
        JOIN stock_location sl ON sl.id = sq.location_id
        WHERE pp.product_tmpl_id = pt.id AND sl.usage = 'internal') AS on_hand
FROM product_template pt
WHERE pt.default_code LIKE '30B4%' OR pt.default_code LIKE '30B5%'
   OR pt.default_code LIKE '10MLS15E00%'
ORDER BY pt.default_code;

SELECT sl.name, pt.default_code, sq.quantity, sloc.complete_name
FROM stock_lot sl
JOIN product_product pp ON pp.id = sl.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
LEFT JOIN stock_quant sq ON sq.lot_id = sl.id AND sq.quantity != 0
LEFT JOIN stock_location sloc ON sloc.id = sq.location_id
WHERE pt.default_code LIKE '30B4%' OR pt.default_code LIKE '30B5%'
ORDER BY pt.default_code, sl.name;
