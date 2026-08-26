# -*- coding: utf-8 -*-
"""Search by product name and find all its lots."""
product_name = "[20NYS4CP00-8G-256G-T-BT70-CMOSP] ThinkPad T490s"

print(f"=== Searching for Product: {product_name} ===")

product = env['product.product'].sudo().search([('display_name', '=', product_name)], limit=1)
if not product:
    # Try searching for the part of the name
    product = env['product.product'].sudo().search([('name', 'ilike', 'T490s')], limit=1)

if not product:
    print("Product not found!")
else:
    print(f"Found Product ID: {product.id}, Name: {product.display_name}")
    lots = env['stock.lot'].sudo().search([('product_id', '=', product.id)])
    print(f"Found {len(lots)} lots for this product.")
    for lot in lots:
        quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id), ('quantity', '!=', 0)])
        for q in quants:
            print(f"  - SN: {lot.name}, Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

print("\nDone.")
