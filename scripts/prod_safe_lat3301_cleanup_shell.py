# -*- coding: utf-8 -*-
"""
SAFE production cleanup for LAT3301:
  1) Print all lots (real Blancco vs auto S/N-LAT3301-NNN)
  2) Cancel ALL sale orders
  3) Remove ONLY auto-generated placeholder SNs (never touches merge serials)

Optional — if you know the 7 merge serials, set ALLOWLIST below and uncomment step 4.

PowerShell on SERVER (/root/reware) or local docker:
  Get-Content scripts/prod_safe_lat3301_cleanup_shell.py | docker compose run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init
"""
import re

SKU = "LAT3301"
# Paste your 7 Blancco serials from merge CSV (uppercase). Leave empty to skip sync.
ALLOWLIST = [
    # "SERIAL1",
    # "SERIAL2",
]

Importer = env["product.csv.importer"].sudo()
Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
SO = env["sale.order"].sudo()

AUTO = re.compile(r"^S/N-LAT3301-\d{3}$", re.I)
tmpl = Template.search([("default_code", "=", SKU)], limit=1)
v = Product.search([("default_code", "=", SKU)], limit=1)

print("=== BEFORE ===")
print(f"on_hand={tmpl.qty_available} website={tmpl._rw_website_available_qty()}")
real, auto = [], []
for lot in Lot.search([("product_id", "=", v.id)], order="name"):
    qty = sum(
        Quant.search(
            [("product_id", "=", v.id), ("lot_id", "=", lot.id), ("quantity", ">", 0)]
        ).mapped("quantity")
    )
    if qty <= 0:
        continue
    (auto if AUTO.match(lot.name) else real).append((lot.name, qty))
print(f"REAL serials in stock ({len(real)}):")
for n, q in real:
    print(f"  {n}")
print(f"AUTO placeholders in stock ({len(auto)}):")
for n, q in auto:
    print(f"  {n}")

# 1) Cancel all sale orders
cancelled = []
for order in SO.search([], order="name"):
    if order.state == "cancel":
        continue
    for p in order.picking_ids.filtered(lambda x: x.state not in ("done", "cancel")):
        p.action_cancel()
    try:
        order.action_cancel()
    except Exception:
        pass
    if order.state != "cancel":
        order.write({"state": "cancel"})
    cancelled.append(order.name)

# 2) Remove auto placeholders only
purge = Importer.purge_auto_generated_serial_stock(SKU)

# 3) Optional exact allowlist from merge CSV
sync = None
if ALLOWLIST:
    sync = Importer.sync_serial_stock_allowlist(SKU, ALLOWLIST)

env.cr.commit()

print("\n=== ACTIONS ===")
print("cancelled_orders:", cancelled)
print("purge_auto:", purge)
if sync:
    print("sync_allowlist:", sync)

print("\n=== AFTER ===")
print(f"on_hand={tmpl.qty_available} website={tmpl._rw_website_available_qty()}")
for lot in Lot.search([("product_id", "=", v.id)], order="name"):
    qty = sum(
        Quant.search(
            [("product_id", "=", v.id), ("lot_id", "=", lot.id), ("quantity", ">", 0)]
        ).mapped("quantity")
    )
    if qty > 0:
        tag = "AUTO" if AUTO.match(lot.name) else "REAL"
        print(f"  [{tag}] {lot.name} qty={qty}")
print("active_orders:", SO.search_count([("state", "!=", "cancel")]))
