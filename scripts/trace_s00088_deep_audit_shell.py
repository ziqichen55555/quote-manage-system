# -*- coding: utf-8 -*-
"""Check for duplicate lot names and 0-quantity quants in WH/Stock."""
sns = ['PC1FVNDB', 'PC1FVGHZ', 'PC1ACMY6', 'PC1ACMYJ', 'PC1ACZJK', 'PC1ACZKQ', 'PC1ACZNF', 'PC1ACZNH']

print(f"=== Deep Audit for SNs: {sns} ===")

for sn in sns:
    print(f"\nAudit for SN: {sn}")
    lots = env['stock.lot'].sudo().search([('name', '=', sn)])
    print(f"  Found {len(lots)} lot record(s) with this name.")
    
    for lot in lots:
        print(f"  Lot ID: {lot.id}, Product: {lot.product_id.display_name}")
        quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
        for q in quants:
            print(f"    - Quant ID: {q.id}, Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

# Check if there are any other SNs in S00088 that I missed?
order = env['sale.order'].sudo().search([('name', '=', 'S00088')], limit=1)
if order:
    print(f"\nChecking all products in S00088 lines:")
    for line in order.order_line.filtered(lambda l: not l.display_type):
        print(f"  Product: {line.product_id.display_name}, Qty: {line.product_uom_qty:g}")
        # Find ALL delivered SNs for this product across ANY picking?
        moves = env['stock.move'].search([('sale_line_id', '=', line.id)])
        for move in moves:
            print(f"    Move: {move.reference} ({move.state})")
            for ml in move.move_line_ids:
                if ml.lot_id:
                    print(f"      - SN in move: {ml.lot_id.name}, Qty: {ml.quantity:g}")

print("\nDone.")
