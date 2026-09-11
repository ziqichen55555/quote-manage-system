# -*- coding: utf-8 -*-
active_count = env['product.template'].search_count([])
archived_count = env['product.template'].search_count([('active', '=', False)])
total_count = env['product.template'].search_count(['|', ('active', '=', True), ('active', '=', False)])
print(f"ACTIVE_PRODUCT_COUNT: {active_count}")
print(f"ARCHIVED_PRODUCT_COUNT: {archived_count}")
print(f"TOTAL_PRODUCT_COUNT: {total_count}")
