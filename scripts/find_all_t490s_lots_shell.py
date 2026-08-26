# -*- coding: utf-8 -*-
"""Broad search for all T490s lots to find the missing 4 units."""
product_id = 2056

print(f"=== Broad Search for ALL Lots of T490s (Product ID: {product_id}) ===")

lots = env['stock.lot'].sudo().search([('product_id', '=', product_id)])
print(f"Found {len(lots)} lots in total for this product.")

for lot in lots:
    quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id), ('quantity', '!=', 0)])
    if quants:
        for q in quants:
            print(f"  - SN: {lot.name}, Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")
    else:
        # Check if it has 0 quantity but some reservation
        ghosts = env['stock.quant'].sudo().search([('lot_id', '=', lot.id), ('quantity', '=', 0), ('reserved_quantity', '!=', 0)])
        for g in ghosts:
            print(f"  - GHOST SN: {lot.name}, Loc: {g.location_id.display_name}, Qty: 0, Reserved: {g.reserved_quantity:g}")

print("\nDone.")
