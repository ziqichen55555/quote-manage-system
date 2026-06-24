# -*- coding: utf-8 -*-
"""Full LAT3301 audit: lots, quants, reservations, all sale orders."""
SKU = "LAT3301"
Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
SO = env["sale.order"].sudo()

tmpl = Template.search([("default_code", "=", SKU)], limit=1)
v = Product.search([("default_code", "=", SKU)], limit=1) or tmpl.product_variant_ids[:1]

print("=== LAT3301 ===")
print(f"tmpl={tmpl.id} variant={v.id} on_hand={tmpl.qty_available} free={v.free_qty} virtual={tmpl.virtual_available}")
print(f"outgoing_qty tmpl={tmpl.outgoing_qty} v={v.outgoing_qty}")
print(f"website qty={tmpl._rw_website_available_qty()}")

lots = Lot.search([("product_id", "=", v.id)], order="name")
print(f"\nLOTS ({len(lots)}):")
for lot in lots:
    q = Quant.search(
        [("product_id", "=", v.id), ("lot_id", "=", lot.id), ("quantity", "!=", 0)],
        limit=1,
    )
    print(f"  {lot.name!r} qty={q.quantity if q else 0} loc={q.location_id.complete_name if q else '-'}")

no_lot = Quant.search(
    [
        ("product_id", "=", v.id),
        ("location_id.usage", "=", "internal"),
        ("lot_id", "=", False),
        ("quantity", ">", 0),
    ]
)
print(f"\nQuants WITHOUT lot: {sum(no_lot.mapped('quantity'))}")

print("\n=== SALE ORDERS (all) ===")
for o in SO.search([], order="name"):
    lat = o.order_line.filtered(lambda l: l.product_id.default_code == SKU)
    extra = f" LAT3301 qty={sum(lat.mapped('product_uom_qty'))}" if lat else ""
    picks = env["stock.picking"].sudo().search([("origin", "=", o.name)])
    print(
        f"  {o.name} id={o.id} state={o.state} partner={o.partner_id.name!r} "
        f"pickings={[p.name + ':' + p.state for p in picks]}{extra}"
    )

print("\n=== OPEN MOVES LAT3301 ===")
for m in env["stock.move"].sudo().search(
    [("product_id", "=", v.id), ("state", "not in", ("done", "cancel"))]
):
    print(f"  {m.origin or '-'} state={m.state} demand={m.product_uom_qty} qty={m.quantity} pick={m.picking_id.name}")
