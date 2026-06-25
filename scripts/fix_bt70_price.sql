UPDATE product_template bt
SET list_price = base.list_price,
    categ_id = base.categ_id
FROM product_template base
WHERE bt.default_code = '20TJS5WW00-BT70'
  AND base.default_code = '20TJS5WW00'
  AND bt.list_price = 0;

SELECT default_code, list_price, categ_id FROM product_template
WHERE default_code IN ('20TJS5WW00', '20TJS5WW00-BT70');
