# -*- coding: utf-8 -*-
"""Trace validation of picking WH/OUT/00068."""
picking_name = "WH/OUT/00068"
picking = env['stock.picking'].sudo().search([('name', '=', picking_name)], limit=1)

if not picking:
    print(f"Picking {picking_name} not found.")
else:
    print(f"=== Audit for {picking.name} ===")
    print(f"State: {picking.state}")
    print(f"Validated By: {picking.write_uid.login} at {picking.date_done}")
    
    print("\n--- Move Lines (Operations) ---")
    for ml in picking.move_line_ids:
        sn_name = ml.lot_id.name if ml.lot_id else "No SN"
        print(f"  - SN: {sn_name}, Qty: {ml.quantity:g}, Created By: {ml.create_uid.login}, Modified By: {ml.write_uid.login}")

    print("\n--- Chatter (Last 10 messages) ---")
    messages = env['mail.message'].sudo().search([
        ('model', '=', 'stock.picking'),
        ('res_id', '=', picking.id)
    ], limit=10, order='id desc')
    for m in messages:
        author = m.author_id.name or m.email_from
        body = (m.body or "")[:200].replace('\n', ' ')
        print(f"  - {m.date} [{author}]: {body}")

    print("\n--- Field Tracking (if any) ---")
    # Check for state changes specifically
    trackings = env['mail.tracking.value'].sudo().search([
        ('mail_message_id', 'in', messages.ids),
        ('field_id.name', '=', 'state')
    ])
    for t in trackings:
        print(f"  - Message ID {t.mail_message_id.id}: State {t.old_value_char} -> {t.new_value_char} by {t.mail_message_id.author_id.name}")

print("\nDone.")
