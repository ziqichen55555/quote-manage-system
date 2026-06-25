SELECT pt.id, pt.default_code, pt.is_published, pt.website_id
FROM product_template pt
WHERE pt.default_code IN ('20TJS5WW00', '20TJS5WW00-BT70');

SELECT pp.id, pp.default_code,
       COALESCE((SELECT sum(sq.quantity) FROM stock_quant sq
        JOIN stock_location sl ON sl.id = sq.location_id
        WHERE sq.product_id = pp.id AND sl.usage = 'internal'), 0) AS on_hand
FROM product_product pp
WHERE pp.default_code IN ('20TJS5WW00', '20TJS5WW00-BT70');
