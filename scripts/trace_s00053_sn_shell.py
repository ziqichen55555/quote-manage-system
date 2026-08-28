# -*- coding: utf-8 -*-
"""Investigate SN PC1PQ9M8 in S00053 and current stock status."""
sn_to_fix = 'PC1PQ9M8'
order_name = 'S00053'

print(f"=== Investigating SN: {sn_to_fix} in Order: {order_name} ===")

# 1. Find the Lot
lot = env['stock.lot'].sudo().search([('name', '=', sn_to_fix)], limit=1)
if not lot:
    print(f"Lot {sn_to_fix} not found!")
else:
    print(f"Found Lot: {lot.name} (ID: {lot.id}), Product: {lot.product_id.display_name}")
    
    # Check current quants
    quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
    print("\n--- Current Stock Status ---")
    for q in quants:
        print(f"  - Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

    # 2. Find the Sale Order and Picking
    order = env['sale.order'].sudo().search([('name', '=', order_name)], limit=1)
    if not order:
        print(f"\nOrder {order_name} not found!")
    else:
        print(f"\nFound Order: {order.name}, State: {order.state}")
        # Find move lines for this lot in this order's pickings
        mls = env['stock.move.line'].sudo().search([
            ('lot_id', '=', lot.id),
            ('picking_id', 'in', order.picking_ids.ids)
        ])
        for ml in mls:
            print(f"  - Move Line ID: {ml.id}, Picking: {ml.picking_id.name}, State: {ml.state}, Qty: {ml.quantity:g}")
            print(f"    Created By: {ml.create_uid.login} at {ml.create_date}")
            print(f"    Modified By: {ml.write_uid.login} at {ml.write_date}")

    # 3. Check Audit Logs / Chatter for the Lot
    print("\n--- Lot Audit Logs (Chatter) ---")
    messages = env['mail.message'].sudo().search([
        ('model', '=', 'stock.lot'),
        ('res_id', '=', lot.id)
    ], limit=10, order='id desc')
    for m in messages:
        author = m.author_id.name or m.email_from
        body = (m.body or "")[:200].replace('\n', ' ')
        print(f"  - {m.date} [{author}]: {body}")

    # 4. Check for similar lots (maybe it was already renamed?)
    similar_lots = env['stock.lot'].sudo().search([('name', 'ilike', sn_to_fix + '%')], limit=5)
    if len(similar_lots) > 1:
        print("\n--- Similar Lots Found ---")
        for sl in similar_lots:
            if sl.id != lot.id:
                print(f"  - Lot: {sl.name} (ID: {sl.id})")

print("\nDone.")
