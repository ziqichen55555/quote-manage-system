# -*- coding: utf-8 -*-
"""Investigate products TPD and TKM."""
print("=== Searching for Products TPD and TKM ===")

# Search for products by name or code
products = env['product.product'].sudo().search([
    '|', ('default_code', 'ilike', 'TPD'), ('name', 'ilike', 'TPD'),
    '|', ('default_code', 'ilike', 'TKM'), ('name', 'ilike', 'TKM')
])

for p in products:
    print(f"\nProduct: {p.display_name} (ID: {p.id})")
    print(f"  Code: {p.default_code}")
    print(f"  On Hand: {p.qty_available:g}")
    print(f"  Reserved: {p.outgoing_qty:g}") # Reserved for outgoing moves
    
    # Check quants for negative or reserved values
    quants = env['stock.quant'].sudo().search([('product_id', '=', p.id)])
    print("  Quants:")
    for q in quants:
        if q.quantity != 0 or q.reserved_quantity != 0:
            print(f"    - Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")
            
    # Check move history if it's negative
    if p.qty_available < 0:
        print("  Checking for negative stock causes (Move lines):")
        moves = env['stock.move.line'].sudo().search([
            ('product_id', '=', p.id),
            ('state', '=', 'done')
        ], order='date desc', limit=5)
        for ml in moves:
             print(f"    - Date: {ml.date}, From: {ml.location_id.display_name}, To: {ml.location_dest_id.display_name}, Qty: {ml.quantity:g}, Picking: {ml.picking_id.name or 'N/A'}")

print("\nDone.")
