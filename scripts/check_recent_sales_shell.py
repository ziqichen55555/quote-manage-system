# -*- coding: utf-8 -*-
"""Recent customer deliveries + cross-check not-ready serials."""
import json
from datetime import datetime, timedelta

rows = json.loads(r'''ROWS_JSON''')

not_ready_serials = {(r.get("serial") or "").strip().upper() for r in rows if r.get("serial")}
serial_map = {(r.get("serial") or "").strip().upper(): r for r in rows}

MoveLine = env["stock.move.line"].sudo()
Picking = env["stock.picking"].sudo()
SaleOrder = env["sale.order"].sudo()

since = datetime.now() - timedelta(days=2)
print("=" * 72)
print("Recent sales / deliveries (last 48h)")
print("=" * 72)

# Recent done customer deliveries with serial lots
recent_done = MoveLine.search(
    [
        ("state", "=", "done"),
        ("location_dest_id.usage", "=", "customer"),
        ("lot_id", "!=", False),
        ("date", ">=", since.strftime("%Y-%m-%d %H:%M:%S")),
    ],
    order="date desc",
    limit=50,
)

print(f"Done customer move lines (serial) since {since}: {len(recent_done)}")
for ml in recent_done:
    sn = (ml.lot_id.name or "").strip().upper()
    so = ml.move_id.sale_line_id.order_id if ml.move_id.sale_line_id else False
    flag = " *** NOT-READY" if sn in not_ready_serials else ""
    print(
        f"  {sn:<12}  order={so.name if so else '-':<8}  "
        f"picking={ml.picking_id.name if ml.picking_id else '-':<14}  "
        f"sku={(ml.product_id.default_code or '')[:36]:<36}  "
        f"date={ml.date}{flag}"
    )

print()
print("--- Open / recent pickings (not done yet) with serial lots ---")
open_pickings = Picking.search(
    [
        ("picking_type_code", "=", "outgoing"),
        ("state", "in", ("assigned", "confirmed", "waiting")),
        ("create_date", ">=", since.strftime("%Y-%m-%d %H:%M:%S")),
    ],
    order="create_date desc",
    limit=20,
)
for p in open_pickings:
    so = p.sale_id
    lines = p.move_line_ids.filtered(lambda l: l.lot_id)
    if not lines:
        continue
    for ml in lines:
        sn = (ml.lot_id.name or "").strip().upper()
        flag = " *** NOT-READY" if sn in not_ready_serials else ""
        print(
            f"  {sn:<12}  state={p.state:<10}  order={so.name if so else '-':<8}  "
            f"picking={p.name:<14}  sku={(ml.product_id.default_code or '')[:36]}{flag}"
        )

print()
print("--- Recent sale orders (last 48h) ---")
recent_so = SaleOrder.search(
    [("create_date", ">=", since.strftime("%Y-%m-%d %H:%M:%S"))],
    order="create_date desc",
    limit=15,
)
for so in recent_so:
    serials = []
    for line in so.order_line:
        for ml in line.move_ids.move_line_ids.filtered(lambda x: x.lot_id):
            serials.append(ml.lot_id.name)
    print(
        f"  {so.name}  state={so.state}  delivery={so.delivery_status}  "
        f"customer={so.partner_id.name[:30] if so.partner_id else ''}  "
        f"serials={serials[:3]}"
    )

print()
print("Done.")
