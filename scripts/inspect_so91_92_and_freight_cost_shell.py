# -*- coding: utf-8 -*-
"""Inspect sale orders 91/92 + set freight product cost to $25 ex GST.

DRY_RUN=True  → report only
DRY_RUN=False + confirm_apply=APPLY → write standard_price on shipping products
"""
DRY_RUN = True
# confirm_apply = APPLY

TARGET_COST = 25.0
SHIP_CODES = (
    "RW_SHIP_METRO_WEIGHT",
    "RW_SHIP_RURAL_QUOTE",
)

SaleOrder = env["sale.order"].sudo()
Product = env["product.product"].sudo()


def dump_order(so):
    print("-" * 72)
    print(
        f"{so.name} id={so.id} state={so.state} "
        f"invoice_status={so.invoice_status} amount_total={so.amount_total} "
        f"currency={so.currency_id.name}"
    )
    print(
        f"  partner={so.partner_id.display_name} "
        f"email={so.partner_id.email!r} phone={so.partner_id.phone!r}"
    )
    print(
        f"  shipping={so.partner_shipping_id.display_name} "
        f"street={so.partner_shipping_id.street!r} "
        f"city={so.partner_shipping_id.city!r} "
        f"zip={so.partner_shipping_id.zip!r}"
    )
    print(
        f"  salesperson={so.user_id.name if so.user_id else '-'} "
        f"team={so.team_id.name if so.team_id else '-'} "
        f"website={so.website_id.name if so.website_id else '-'} "
        f"date_order={so.date_order}"
    )
    print("  Lines:")
    for line in so.order_line:
        lot_names = []
        for ml in line.move_ids.move_line_ids.filtered(lambda x: x.lot_id):
            lot_names.append(ml.lot_id.name)
        print(
            f"    - [{line.product_id.default_code or '-'}] {line.name[:80]!r} "
            f"qty={line.product_uom_qty} price={line.price_unit} "
            f"subtotal={line.price_subtotal} "
            f"lots={lot_names or '-'}"
        )
    pickings = so.picking_ids.sorted("id")
    print(f"  Deliveries ({len(pickings)}):")
    for p in pickings:
        print(
            f"    - {p.name} state={p.state} "
            f"scheduled={p.scheduled_date} done={p.date_done}"
        )
    invoices = so.invoice_ids.sorted("id")
    print(f"  Invoices ({len(invoices)}):")
    for inv in invoices:
        print(
            f"    - {inv.name} state={inv.state} "
            f"payment_state={inv.payment_state} "
            f"amount_total={inv.amount_total} "
            f"xero={getattr(inv, 'xero_sync_status', False) or '-'}"
        )
    txs = so.transaction_ids.sorted("id") if "transaction_ids" in so._fields else []
    if txs:
        print(f"  Payment transactions ({len(txs)}):")
        for tx in txs:
            print(
                f"    - {tx.reference} state={tx.state} "
                f"provider={tx.provider_id.name if tx.provider_id else '-'} "
                f"amount={tx.amount}"
            )


print("=" * 72)
print("Sale orders S00091 / S00092 (also match by id 91/92 if needed)")
print("=" * 72)

orders = SaleOrder.search([("name", "in", ["S00091", "S00092"])], order="name")
if not orders:
    # fallback: numeric id
    orders = SaleOrder.browse([91, 92]).exists()
    print("No S00091/S00092 by name; falling back to ids 91/92")

if not orders:
    print("ERROR: orders not found")
else:
    for so in orders:
        dump_order(so)

print()
print("=" * 72)
print(f"Freight products — set standard_price (cost) to {TARGET_COST} ex GST")
print("=" * 72)

products = Product.search([("default_code", "in", list(SHIP_CODES))])
found_codes = set(products.mapped("default_code"))
for code in SHIP_CODES:
    if code not in found_codes:
        print(f"  MISSING product default_code={code}")

to_write = Product.browse()
for p in products:
    tmpl = p.product_tmpl_id
    print(
        f"  {p.default_code}: id={p.id} name={p.display_name!r} "
        f"list_price={p.list_price} standard_price={p.standard_price} "
        f"tmpl_standard_price={tmpl.standard_price}"
    )
    if float(p.standard_price or 0.0) != TARGET_COST or float(tmpl.standard_price or 0.0) != TARGET_COST:
        to_write |= p

if not to_write:
    print("Nothing to change — already at target cost.")
elif DRY_RUN:
    print(f"DRY_RUN: would set standard_price={TARGET_COST} on {len(to_write)} product(s).")
else:
    if confirm_apply != "APPLY":
        raise SystemExit("Refusing write without confirm_apply=APPLY")
    for p in to_write:
        # Cost lives on template in many setups; write both for safety.
        p.product_tmpl_id.write({"standard_price": TARGET_COST})
        p.write({"standard_price": TARGET_COST})
        print(f"  APPLY: {p.default_code} -> standard_price={p.standard_price}")
    env.cr.commit()
    print("APPLY done + committed.")
