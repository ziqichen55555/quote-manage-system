UPDATE product_template
SET is_published = false, sale_ok = false
WHERE default_code = '20TJS5WW00';

SELECT default_code, is_published, sale_ok, list_price
FROM product_template
WHERE default_code LIKE '20TJS5WW00%'
ORDER BY default_code;
