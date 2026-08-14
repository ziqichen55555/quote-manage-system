# -*- coding: utf-8 -*-
"""Read-only: why is GM048TMP reserved?"""
Lot = env["stock.lot"].sudo()
ML = env["stock.move.line"].sudo()
Quant = env["stock.quant"].sudo()

SN = "GM048TMP"
lot = Lot.search([("name", "=", SN)], limit=1)
print(f"=== {SN} ===")
if not lot:
    print("lot not found")
else:
    print(f"product={lot.product_id.default_code} lot_id={lot.id}")
    quants = Quant.search([("lot_id", "=", lot.id)])
    for q in quants:
        print(
            f"  quant loc={q.location_id.display_name} on_hand={q.quantity:g} "
            f"reserved={q.reserved_quantity:g} available={q.quantity - q.reserved_quantity:g}"
        )
    # open move lines reserving this lot
    open_mls = ML.search([
        ("lot_id", "=", lot.id),
        ("state", "in", ["assigned", "partially_available"]),
    ])
    print(f"\nopen move lines ({len(open_mls)}):")
    for ml in open_mls:
        pick = ml.picking_id
        sale = pick.sale_id.name if pick and pick.sale_id else ""
        qty = getattr(ml, "qty_done", None) or ml.quantity
        print(
            f"  ml={ml.id} pick={pick.name if pick else '-'} sale={sale!r} "
            f"state={ml.state} qty={qty:g} scheduled={pick.scheduled_date if pick else ''} "
            f"create={ml.create_uid.login} write={ml.write_uid.login} date={ml.date}"
        )
    print("\nfull history:")
    all_mls = ML.search([("lot_id", "=", lot.id)], order="date asc, id asc")
    for ml in all_mls:
        qty = getattr(ml, "qty_done", None) or ml.quantity
        pick = ml.picking_id
        sale = pick.sale_id.name if pick and pick.sale_id else ""
        print(
            f"  {ml.date} {ml.state} {pick.name if pick else '-'} sale={sale!r} "
            f"{ml.location_id.display_name}->{ml.location_dest_id.display_name} qty={qty:g} "
            f"by {ml.write_uid.login}"
        )

# S00098 detail
o = env["sale.order"].sudo().search([("name", "=", "S00098")], limit=1)
if o:
    print(f"\n=== S00098 state={o.state} partner={o.partner_id.display_name} ===")
    for pick in o.picking_ids:
        print(f"  {pick.name} state={pick.state} done={pick.date_done}")
        for ml in pick.move_line_ids:
            lot_name = ml.lot_id.name if ml.lot_id else "(no lot)"
            qty = getattr(ml, "qty_done", None) or ml.quantity
            print(f"    {lot_name} qty={qty:g} ml_state={ml.state}")

print("\nDone.")
