# -*- coding: utf-8 -*-
"""Search for any other products that might be T490s."""
print("=== Searching for all products with 'T490s' in name ===")

products = env['product.product'].sudo().search([('name', 'ilike', 'T490s')])
for p in products:
    print(f"ID: {p.id}, Display Name: {p.display_name}, Code: {p.default_code}")
    lots = env['stock.lot'].sudo().search([('product_id', '=', p.id)])
    print(f"  - Total Lots: {len(lots)}")
    for l in lots:
        quants = env['stock.quant'].sudo().search([('lot_id', '=', l.id), ('quantity', '>', 0)])
        for q in quants:
            print(f"    - SN: {l.name}, Loc: {q.location_id.display_name}, Qty: {q.quantity:g}")

print("\nDone.")
