# -*- coding: utf-8 -*-
"""Read-only: trace S00098 / S00082 — website, follow-up, who picked SN."""
ORDERS = ["S00098", "S00082"]
SERIALS = ["GM048TJA", "GM048TKM"]

SO = env["sale.order"].sudo()
Picking = env["stock.picking"].sudo()
MoveLine = env["stock.move.line"].sudo()
Message = env["mail.message"].sudo()
Tracking = env["mail.tracking.value"].sudo()
User = env["res.users"].sudo()

print("=== ORDER + SN TRACE (read-only) ===")

for name in ORDERS:
    o = SO.search([("name", "=", name)], limit=1)
    print("\n" + "#" * 70)
    print(f"# {name}")
    if not o:
        print("NOT FOUND")
        continue
    print(f"  state={o.state} date={o.date_order}")
    print(f"  partner={o.partner_id.display_name} email={o.partner_id.email or ''}")
    print(f"  website_id={o.website_id.id if o.website_id else None} website={o.website_id.name if o.website_id else '(backend)'}")
    print(f"  user_id={o.user_id.login if o.user_id else '-'} (salesperson)")
    print(f"  create_uid={o.create_uid.login} create_date={o.create_date}")
    print(f"  write_uid={o.write_uid.login} write_date={o.write_date}")
    for line in o.order_line.filtered(lambda l: not l.display_type):
        print(
            f"  line: {line.product_id.default_code} qty={line.product_uom_qty:g} "
            f"delivered={line.qty_delivered:g} name={line.name[:60]}"
        )
    for pick in o.picking_ids.sorted("id"):
        sns = pick.move_line_ids.filtered(lambda ml: ml.lot_id).mapped(lambda ml: ml.lot_id.name)
        print(
            f"  picking {pick.name} type={pick.picking_type_id.code} state={pick.state} "
            f"scheduled={pick.scheduled_date} done={pick.date_done} "
            f"create_uid={pick.create_uid.login} write_uid={pick.write_uid.login} serials={sns}"
        )
        for ml in pick.move_line_ids.filtered(lambda x: x.lot_id):
            qty = getattr(ml, "qty_done", None) or ml.quantity
            print(
                f"    ml id={ml.id} lot={ml.lot_id.name} qty={qty:g} state={ml.state} "
                f"create_uid={ml.create_uid.login} write_uid={ml.write_uid.login} date={ml.date}"
            )

    # chatter / tracking on order
    msgs = Message.search(
        [("model", "=", "sale.order"), ("res_id", "=", o.id)],
        order="id desc",
        limit=15,
    )
    print(f"  recent messages ({len(msgs)}):")
    for m in msgs:
        author = m.author_id.display_name if m.author_id else (m.email_from or "system")
        subj = (m.subject or m.body or "")[:120].replace("\n", " ")
        print(f"    {m.date} [{m.message_type}] {author}: {subj}")

    trackings = Tracking.search(
        [("mail_message_id", "in", msgs.ids)],
        order="id desc",
        limit=20,
    )
    if trackings:
        print("  field changes:")
        for t in trackings:
            print(f"    {t.field_id.name}: {t.old_value_char or t.old_value_integer} -> {t.new_value_char or t.new_value_integer}")

print("\n" + "=" * 70)
print("SERIAL history across pickings")
for sn in SERIALS:
    lot = env["stock.lot"].sudo().search([("name", "=", sn)], limit=1)
    if not lot:
        continue
    print(f"\n--- {sn} ---")
    mls = MoveLine.search([("lot_id", "=", lot.id)], order="date asc, id asc")
    for ml in mls:
        qty = getattr(ml, "qty_done", None) or ml.quantity
        pick = ml.picking_id
        sale = pick.sale_id.name if pick and pick.sale_id else ""
        print(
            f"  {ml.date} {ml.state} pick={pick.name if pick else '-'} sale={sale!r} "
            f"{ml.location_id.display_name}->{ml.location_dest_id.display_name} qty={qty:g} "
            f"by create={ml.create_uid.login} write={ml.write_uid.login}"
        )

print("\nDone.")
