# -*- coding: utf-8 -*-
"""Deep search for TPD and TKM shorthand."""
print("=== Deep Search for TPD and TKM ===")

# Search products by display_name or default_code
products = env['product.product'].sudo().search([
    '|', ('default_code', 'ilike', 'TPD'), ('name', 'ilike', 'TPD'),
    '|', ('default_code', 'ilike', 'TKM'), ('name', 'ilike', 'TKM')
])

# Also check for lots that might have these in their names
lots = env['stock.lot'].sudo().search([
    '|', ('name', 'ilike', 'TPD'), ('name', 'ilike', 'TKM')
])

for p in products:
    print(f"\nPRODUCT FOUND: {p.display_name} (ID: {p.id})")
    print(f"  On Hand: {p.qty_available:g}, Reserved: {p.outgoing_qty:g}")
    quants = env['stock.quant'].sudo().search([('product_id', '=', p.id)])
    for q in quants:
        if q.quantity != 0 or q.reserved_quantity != 0:
            print(f"    - Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

for l in lots:
    print(f"\nLOT FOUND: {l.name} (ID: {l.id}) for Product: {l.product_id.display_name}")
    quants = env['stock.quant'].sudo().search([('lot_id', '=', l.id)])
    for q in quants:
        print(f"    - Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

# If still nothing, search for "TPD" and "TKM" in the whole database for mail messages or move names
if not products and not lots:
    print("\nNo direct product/lot matches. Checking stock moves for references...")
    moves = env['stock.move'].sudo().search([
        '|', ('name', 'ilike', 'TPD'), ('name', 'ilike', 'TKM'),
        '|', ('reference', 'ilike', 'TPD'), ('reference', 'ilike', 'TKM')
    ], limit=10)
    for m in moves:
        print(f"  - Move: {m.reference}, Product: {m.product_id.display_name}, Qty: {m.product_uom_qty:g}")

print("\nDone.")
