# -*- coding: utf-8 -*-
count = env['product.template'].search_count([])
print(f"CURRENT_PRODUCT_COUNT: {count}")
