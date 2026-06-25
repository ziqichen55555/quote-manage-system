SELECT pt.id, pt.default_code, pt.active, pt.website_published,
       (SELECT sum(sq.quantity) FROM stock_quant sq
        JOIN product_product pp ON pp.id = sq.product_id
        WHERE pp.product_tmpl_id = pt.id AND sq.location_id IN (
          SELECT id FROM stock_location WHERE usage = 'internal')) AS on_hand
FROM product_template pt
WHERE pt.default_code LIKE '20TJS5WW00%'
ORDER BY pt.default_code;

SELECT pp.id, pp.default_code, sl.name AS serial, sq.quantity
FROM stock_lot sl
JOIN product_product pp ON pp.id = sl.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
LEFT JOIN stock_quant sq ON sq.lot_id = sl.id AND sq.quantity > 0
WHERE sl.name = 'R913RZGT';
