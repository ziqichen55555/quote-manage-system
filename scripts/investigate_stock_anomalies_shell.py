# -*- coding: utf-8 -*-
"""Broad search for products TPD and TKM."""
print("=== Broad Search for Products TPD and TKM ===")

# Search for products by name or code using ILIKE
products = env['product.product'].sudo().search([
    '|', ('default_code', 'ilike', 'TPD'), ('name', 'ilike', 'TPD'),
    '|', ('default_code', 'ilike', 'TKM'), ('name', 'ilike', 'TKM')
])

if not products:
    # Try even broader if nothing found
    print("No direct matches found. Trying even broader...")
    products = env['product.product'].sudo().search([
        '|', ('name', 'ilike', 'T-P-D'), ('name', 'ilike', 'T-K-M'),
        '|', ('default_code', 'ilike', 'T P D'), ('default_code', 'ilike', 'T K M')
    ])

for p in products:
    print(f"\nProduct: {p.display_name} (ID: {p.id})")
    print(f"  Code: {p.default_code}")
    print(f"  On Hand: {p.qty_available:g}")
    print(f"  Reserved: {p.outgoing_qty:g}")
    
    # Check quants
    quants = env['stock.quant'].sudo().search([('product_id', '=', p.id)])
    for q in quants:
        if q.quantity != 0 or q.reserved_quantity != 0:
            print(f"    - Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

# If still nothing, let's search for any products with negative stock or reservations
print("\n=== Checking for any products with Negative On Hand or Reserved quantities ===")
neg_quants = env['stock.quant'].sudo().search([
    '|', ('quantity', '<', 0), ('reserved_quantity', '>', 0)
], limit=20)

for q in neg_quants:
    print(f"  - Product: {q.product_id.display_name}, Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

print("\nDone.")
