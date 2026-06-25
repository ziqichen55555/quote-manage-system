SELECT column_name FROM information_schema.columns
WHERE table_name = 'product_template' AND column_name LIKE '%price%';

SELECT column_name FROM information_schema.columns
WHERE table_name = 'product_product' AND column_name LIKE '%price%';
