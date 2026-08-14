# -*- coding: utf-8 -*-
"""Read-only: S00093 — website, follow-up, TJA shipment."""
SO = env["sale.order"].sudo()
o = SO.search([("name", "=", "S00093")], limit=1)
print("=== S00093 ===")
if not o:
    print("NOT FOUND")
else:
    print(f"state={o.state} date={o.date_order}")
    print(f"partner={o.partner_id.display_name}")
    print(f"website_id={o.website_id.id if o.website_id else None} website={o.website_id.name if o.website_id else '(backend)'}")
    print(f"user_id={o.user_id.login if o.user_id else '-'}")
    print(f"create_uid={o.create_uid.login} write_uid={o.write_uid.login}")
    for line in o.order_line.filtered(lambda l: not l.display_type):
        print(f"  line: {line.product_id.default_code} qty={line.product_uom_qty:g} delivered={line.qty_delivered:g}")
    for pick in o.picking_ids.sorted("id"):
        sns = pick.move_line_ids.filtered(lambda ml: ml.lot_id).mapped(lambda ml: ml.lot_id.name)
        print(f"  picking {pick.name} state={pick.state} done={pick.date_done} serials={sns}")
        for ml in pick.move_line_ids.filtered(lambda x: x.lot_id):
            qty = getattr(ml, "qty_done", None) or ml.quantity
            print(f"    lot={ml.lot_id.name} qty={qty:g} create={ml.create_uid.login} write={ml.write_uid.login} date={ml.date}")
    msgs = env["mail.message"].sudo().search([("model", "=", "sale.order"), ("res_id", "=", o.id)], order="id desc", limit=10)
    for m in msgs:
        author = m.author_id.display_name if m.author_id else (m.email_from or "system")
        print(f"  msg {m.date} [{m.message_type}] {author}: {(m.subject or m.body or '')[:100].replace(chr(10),' ')}")
