# -*- coding: utf-8 -*-
"""Verify current lot names and check S00111 error context."""
sns_to_check = ['PC1ACMYJ', 'PC1ACZKQ', 'PC1ACZNF', 'PC1ACMY6']
invalid_sns = [sn + "_INVALID" for sn in sns_to_check]

print("=== Verifying Lot Names ===")
for name in sns_to_check + invalid_sns:
    lots = env['stock.lot'].sudo().search([('name', '=', name)])
    for lot in lots:
        print(f"Found Lot: '{lot.name}' (ID: {lot.id}), Product: {lot.product_id.display_name}")
        quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
        for q in quants:
            print(f"  - Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

print("\n=== Checking Move Lines for WH/OUT/00068 (S00088) ===")
picking = env['stock.picking'].sudo().search([('name', '=', 'WH/OUT/00068')], limit=1)
if picking:
    for ml in picking.move_line_ids:
        print(f"  Move Line ID {ml.id}: Lot='{ml.lot_id.name}', Qty={ml.quantity:g}")

print("\n=== Checking S00111 context ===")
order_111 = env['sale.order'].sudo().search([('name', '=', 'S00111')], limit=1)
if order_111:
    print(f"Order S00111 State: {order_111.state}")
    for pick in order_111.picking_ids:
        print(f"  Picking: {pick.name} ({pick.state})")
        for ml in pick.move_line_ids:
             print(f"    - ML: Lot='{ml.lot_id.name if ml.lot_id else 'None'}', Qty={ml.quantity:g}")

print("\nDone.")
