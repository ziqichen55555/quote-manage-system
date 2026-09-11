# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

# Try to find products updated in the last 2 hours
two_hours_ago = datetime.now() - timedelta(hours=2)
products = env['product.template'].with_context(active_test=False).search([('write_date', '>=', two_hours_ago)], order='write_date desc')

print(f"Total products updated in the last 2 hours: {len(products)}")

active = products.filtered(lambda p: p.active)
archived = products.filtered(lambda p: not p.active)

print(f"Active: {len(active)}")
print(f"Archived: {len(archived)}")

# Group by write_date to see batches
batches = {}
for p in products:
    dt_str = p.write_date.strftime('%Y-%m-%d %H:%M:%S')
    if dt_str not in batches:
        batches[dt_str] = []
    batches[dt_str].append(p)

for dt_str, batch in sorted(batches.items(), reverse=True):
    active_in_batch = len([p for p in batch if p.active])
    archived_in_batch = len([p for p in batch if not p.active])
    print(f"Batch {dt_str} | Total: {len(batch)} | Active: {active_in_batch} | Archived: {archived_in_batch}")
    # Print first few names in batch
    names = ", ".join([p.name for p in batch[:3]])
    print(f"  Examples: {names}")
