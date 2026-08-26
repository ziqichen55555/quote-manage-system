# -*- coding: utf-8 -*-
"""Find correct product info using a known Lot ID."""
lot_id = 2381 # PC1ACMY6

print(f"=== Investigating Lot ID: {lot_id} ===")

lot = env['stock.lot'].sudo().browse(lot_id)
if not lot.exists():
    print("Lot not found!")
else:
    product = lot.product_id
    print(f"Lot Name: {lot.name}")
    print(f"Product ID: {product.id}")
    print(f"Product Name: {product.name}")
    print(f"Product Display Name: {product.display_name}")
    print(f"Product Default Code: {product.default_code}")
    
    print("\n--- Finding ALL Lots and Quants for this Product ---")
    lots = env['stock.lot'].sudo().search([('product_id', '=', product.id)])
    print(f"Total Lots found: {len(lots)}")
    
    for l in lots:
        quants = env['stock.quant'].sudo().search([('lot_id', '=', l.id), ('quantity', '!=', 0)])
        if quants:
            for q in quants:
                print(f"  - SN: {l.name}, Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")
        else:
            # Check for ghost reservations
            ghosts = env['stock.quant'].sudo().search([('lot_id', '=', l.id), ('quantity', '=', 0), ('reserved_quantity', '!=', 0)])
            for g in ghosts:
                print(f"  - GHOST SN: {l.name}, Loc: {g.location_id.display_name}, Reserved: {g.reserved_quantity:g}")

print("\nDone.")
