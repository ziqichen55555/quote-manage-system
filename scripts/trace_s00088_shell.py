# -*- coding: utf-8 -*-
"""Read-only: trace S00088 — investigate why SNs are still in stock."""
ORDERS = ["S00088"]

SO = env["sale.order"].sudo()
Picking = env["stock.picking"].sudo()
MoveLine = env["stock.move.line"].sudo()
Message = env["mail.message"].sudo()
Tracking = env["mail.tracking.value"].sudo()
User = env["res.users"].sudo()
Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()

print("=== S00088 ORDER + SN INVESTIGATION (read-only) ===")

all_sns = []

for name in ORDERS:
    o = SO.search([("name", "=", name)], limit=1)
    print("\n" + "#" * 70)
    print(f"# {name}")
    if not o:
        print("NOT FOUND")
        continue
    print(f"  state={o.state} date={o.date_order}")
    print(f"  partner={o.partner_id.display_name} email={o.partner_id.email or ''}")
    print(f"  delivered_status={o.delivery_status if hasattr(o, 'delivery_status') else 'N/A'}")
    
    for line in o.order_line.filtered(lambda l: not l.display_type):
        print(
            f"  line: {line.product_id.default_code} qty={line.product_uom_qty:g} "
            f"delivered={line.qty_delivered:g} name={line.name[:60]}"
        )
    
    for pick in o.picking_ids.sorted("id"):
        sns = pick.move_line_ids.filtered(lambda ml: ml.lot_id).mapped(lambda ml: ml.lot_id.name)
        all_sns.extend(sns)
        print(
            f"  picking {pick.name} type={pick.picking_type_id.code} state={pick.state} "
            f"scheduled={pick.scheduled_date} done={pick.date_done} "
            f"serials={sns}"
        )

    # chatter / tracking on order
    msgs = Message.search(
        [("model", "=", "sale.order"), ("res_id", "=", o.id)],
        order="id desc",
        limit=20,
    )
    print(f"\n  recent messages ({len(msgs)}):")
    for m in msgs:
        author = m.author_id.display_name if m.author_id else (m.email_from or "system")
        subj = (m.subject or m.body or "")[:120].replace("\n", " ")
        print(f"    {m.date} [{m.message_type}] {author}: {subj}")

    trackings = Tracking.search(
        [("mail_message_id", "in", msgs.ids)],
        order="id desc",
    )
    if trackings:
        print("\n  field changes:")
        for t in trackings:
            print(f"    {t.field_id.name}: {t.old_value_char or t.old_value_integer} -> {t.new_value_char or t.new_value_integer}")

print("\n" + "=" * 70)
print("SERIAL history and current stock")
all_sns = list(set(all_sns))
for sn in all_sns:
    lot = Lot.search([("name", "=", sn)], limit=1)
    if not lot:
        print(f"\n--- {sn} (Lot record not found) ---")
        continue
    
    # Current Stock
    quants = Quant.search([("lot_id", "=", lot.id)])
    stock_info = []
    for q in quants:
        if q.quantity > 0:
            stock_info.append(f"{q.location_id.display_name}: {q.quantity:g}")
    
    print(f"\n--- {sn} (Current Stock: {', '.join(stock_info) or 'None'}) ---")
    
    # Movement History
    mls = MoveLine.search([("lot_id", "=", lot.id)], order="date asc, id asc")
    for ml in mls:
        qty = getattr(ml, "qty_done", None) or ml.quantity
        pick = ml.picking_id
        sale = pick.sale_id.name if pick and pick.sale_id else ""
        print(
            f"  {ml.date} {ml.state} pick={pick.name if pick else '-'} sale={sale!r} "
            f"{ml.location_id.display_name}->{ml.location_dest_id.display_name} qty={qty:g} "
            f"by {ml.create_uid.login}"
        )

print("\nDone.")
