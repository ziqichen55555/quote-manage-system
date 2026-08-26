# -*- coding: utf-8 -*-
"""Check all T490s SNs in WH/Stock to find what Chris is seeing."""
product_id = 2056  # From previous Lot logs: Product ID for ThinkPad T490s
sns_in_s00088 = ['PC1FVNDB', 'PC1FVGHZ', 'PC1ACMY6', 'PC1ACMYJ', 'PC1ACZJK', 'PC1ACZKQ', 'PC1ACZNF', 'PC1ACZNH']

print(f"=== Checking WH/Stock for T490s (Product ID: {product_id}) ===")

# 1. Find all quants for this product in WH/Stock
internal_locs = env['stock.location'].search([('usage', '=', 'internal')])
quants = env['stock.quant'].sudo().search([
    ('product_id', '=', product_id),
    ('location_id', 'child_of', internal_locs.ids),
    ('quantity', '>', 0)
])

print(f"Found {len(quants)} quants in internal stock.")
for q in quants:
    sn_name = q.lot_id.name if q.lot_id else "No SN"
    print(f"  - SN: {sn_name}, Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")
    if sn_name in sns_in_s00088:
        print(f"    !!! WARNING: This SN was supposedly delivered in S00088 but is still here !!!")

# 2. Check recent movements for MY6 specifically to see how it got here
my6_lot = env['stock.lot'].sudo().search([('name', '=', 'PC1ACMY6')], limit=1)
if my6_lot:
    print(f"\n--- Movement History for PC1ACMY6 ---")
    moves = env['stock.move.line'].sudo().search([('lot_id', '=', my6_lot.id)], order='date desc')
    for ml in moves:
        print(f"  - Date: {ml.date}, From: {ml.location_id.display_name}, To: {ml.location_dest_id.display_name}, Qty: {ml.quantity:g}, State: {ml.state}, Reference: {ml.reference}")

print("\nDone.")
