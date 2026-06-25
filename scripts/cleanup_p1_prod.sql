-- Unpublish obsolete base MTM (stock lives on 20TJS5WW00-BT70)
UPDATE product_template
SET is_published = false,
    website_published = false,
    sale_ok = false
WHERE default_code = '20TJS5WW00';

-- Delete ghost serial lots with no non-zero quants on obsolete base MTM
DELETE FROM stock_lot sl
USING product_product pp, product_template pt
WHERE pp.id = sl.product_id
  AND pt.id = pp.product_tmpl_id
  AND pt.default_code = '20TJS5WW00'
  AND NOT EXISTS (
    SELECT 1 FROM stock_quant sq
    WHERE sq.lot_id = sl.id AND sq.quantity != 0
  );

SELECT pt.default_code, pt.is_published, pt.website_published, pt.sale_ok
FROM product_template pt
WHERE pt.default_code LIKE '20TJS5WW00%';

SELECT sl.name, pt.default_code
FROM stock_lot sl
JOIN product_product pp ON pp.id = sl.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
WHERE pt.default_code LIKE '20TJS5WW00%'
ORDER BY pt.default_code, sl.name;
