# -*- coding: utf-8 -*-
"""Investigate why GM048TKM is reserved and GM048TPD is -1."""
lots_to_trace = ['GM048TKM', 'GM048TPD']

for sn in lots_to_trace:
    lot = env['stock.lot'].sudo().search([('name', '=', sn)], limit=1)
    if not lot:
        print(f"Lot {sn} not found.")
        continue
    
    print(f"\n=== Detailed Audit for SN: {sn} (Lot ID: {lot.id}) ===")
    
    # 1. Check all move lines (history)
    print("Movement History:")
    mls = env['stock.move.line'].sudo().search([('lot_id', '=', lot.id)], order='date desc')
    for ml in mls:
        print(f"  - Date: {ml.date}, From: {ml.location_id.display_name}, To: {ml.location_dest_id.display_name}, Qty: {ml.quantity:g}, State: {ml.state}, Reference: {ml.reference}")
        if ml.picking_id:
             print(f"    - Picking: {ml.picking_id.name}, State: {ml.picking_id.state}, Order: {ml.picking_id.sale_id.name or 'N/A'}")

    # 2. Specifically for RESERVED, find the move that is assigned
    if sn == 'GM048TKM':
        print("\nSearching for reservation cause:")
        moves = env['stock.move'].sudo().search([
            ('lot_ids', 'in', [lot.id]),
            ('state', 'not in', ['done', 'cancel'])
        ])
        for m in moves:
            print(f"  - Move: {m.reference}, State: {m.state}, Picking: {m.picking_id.name}, Sale Order: {m.sale_line_id.order_id.name or 'N/A'}")
            
    # 3. Check for any other quants
    print("\nCurrent Quants:")
    quants = env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
    for q in quants:
        print(f"  - Quant ID: {q.id}, Loc: {q.location_id.display_name}, Qty: {q.quantity:g}, Reserved: {q.reserved_quantity:g}")

print("\nDone.")
