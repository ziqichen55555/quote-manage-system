SELECT column_name FROM information_schema.columns
WHERE table_name = 'product_template'
  AND column_name LIKE '%publish%';
