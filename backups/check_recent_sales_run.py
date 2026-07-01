# -*- coding: utf-8 -*-
"""Recent customer deliveries + cross-check not-ready serials."""
import json
from datetime import datetime, timedelta

rows = json.loads(r'''[{"serial": "PC1450A6", "shop_sku": "20L8SDCE00-BTU70", "reason": "Serial not found in Blancco", "model": "Thinkpad T480s Touch"}, {"serial": "PC1ACZKV", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFTE", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGP6", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZPJ", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACMY7", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PCIFVNGF", "shop_sku": "20NYS4CP00-BTU70", "reason": "Serial not found in Blancco", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVES6", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVNFB", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZKF", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZMK", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVERM", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVNCW", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZJ2", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGKY", "shop_sku": "20NYS4CP00-BTU70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC23W08R", "shop_sku": "20WNS1M500-BTU70-CMOSFL", "reason": "CMOS Fail", "model": "ThinkPad T14s"}, {"serial": "PC1FVEPD", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFYJ", "shop_sku": "20NYS4CP00-BTU70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVEVN", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGME", "shop_sku": "20NYS4CP00-BTU70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVEVR", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1TKK7W", "shop_sku": "20T0003UAU-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1ACMXK", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGLJ", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFXC", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1EYJWX", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZN4", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVNGN", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVND1", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVEW8", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVEQ5", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZNY", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGKN", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGKK", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVFDG", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFXF", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGHT", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACMYD", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACMXJ", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFTY", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFYS", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGMG", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1EYJY6", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVET2", "shop_sku": "20NYS4CP00-BTU70", "reason": "Serial not found in Blancco", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZPX", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFY8", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZLS", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVNFP", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGNK", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVNGE", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGJY", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVNJ9", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVGJD", "shop_sku": "20NYS4CP00-BTU70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1PQ9HS", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9MK", "shop_sku": "20T1S6C300-BTU70", "reason": "Serial not found in Blancco", "model": "Thinkpad T14s Touch"}, {"serial": "PC1TKK8L", "shop_sku": "20T0003UAU-BTU70", "reason": "Serial not found in Blancco", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9JK", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9K5", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9MD", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9MW", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9M0", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9J3", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "GM048TJZ", "shop_sku": "20WNA07YAU-BT70-CMOSFL", "reason": "CMOS Fail", "model": "ThinkPad T14s"}, {"serial": "PC27R1V2", "shop_sku": "20WN0025AU-BT70-CMOSFL", "reason": "CMOS Fail", "model": "ThinkPad T14s"}, {"serial": "PC27R1WE", "shop_sku": "20WN0025AU-BT70-CMOSFL", "reason": "CMOS Fail", "model": "ThinkPad T14s"}, {"serial": "PC27R1WK", "shop_sku": "20WN0025AU-BT70-CMOSFL", "reason": "CMOS Fail", "model": "ThinkPad T14s"}, {"serial": "PC27R3NL", "shop_sku": "20WN0025AU-BT70-CMOSFL", "reason": "CMOS Fail", "model": "ThinkPad T14s"}, {"serial": "PC27R40B", "shop_sku": "20WN0025AU-BT70-CMOSFL", "reason": "CMOS Fail", "model": "ThinkPad T14s"}, {"serial": "PC1FVEVB", "shop_sku": "20NYS4CP00-BTU70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVNDW", "shop_sku": "20NYS4CP00-BTU70", "reason": "CMOS unknown", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACMY3", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZK0", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFYG", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVFCP", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFXM", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVEVT", "shop_sku": "20NYS4CP00-BTU70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVEQJ", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1ACZJX", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FVNG2", "shop_sku": "20NYS4CP00-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T490s Touch"}, {"serial": "PC1FSFVM", "shop_sku": "20NYS4CP00-BTU70", "reason": "Serial not found in Blancco", "model": "Thinkpad T490s Touch"}, {"serial": "PC1PQ9JL", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9HV", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9GQ", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "PC1PQ9K3", "shop_sku": "20T1S6C300-BT70-CMOSFL", "reason": "CMOS Fail", "model": "Thinkpad T14s Touch"}, {"serial": "DFG4", "shop_sku": "4518PT1PBM-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "8MA", "shop_sku": "553RE5R8X1-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "PC04P6YX", "shop_sku": "10A8A1E6AU", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "PVD7", "shop_sku": "5536RE5R85-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "PTB7", "shop_sku": "5536RE5R85-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "D58R", "shop_sku": "7360NP1R88-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "VRWE", "shop_sku": "3209A93PBL-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "D26K", "shop_sku": "4518PT1R8L-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "GRDE", "shop_sku": "3209A93PBY-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "PRX4", "shop_sku": "5536RE5R85-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "DFX6", "shop_sku": "4518PT1PBM-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "HG2V", "shop_sku": "5536RE5R89-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "PC0PEDTY", "shop_sku": "30B4S1QA00", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "PC0MDC47", "shop_sku": "30B5S0PF00", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "W52F", "shop_sku": "4157NW5R8T-BTU70", "reason": "Serial not found in Blancco", "model": ""}, {"serial": "XAV5", "shop_sku": "4157NW5PBB-BTU70", "reason": "Serial not found in Blancco", "model": ""}]''')

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
