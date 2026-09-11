# -*- coding: utf-8 -*-
from datetime import datetime

today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
created = env['product.template'].with_context(active_test=False).search([('create_date', '>=', today_start)])

print(f"Total products created today: {len(created)}")
for p in created:
    print(f"ID: {p.id} | Name: {p.name} | Active: {p.active} | Created: {p.create_date}")
