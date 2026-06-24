# -*- coding: utf-8 -*-
"""Audit LAT3301 stock, reservations, and sale orders."""
SKU = "LAT3301"

Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
SO = env["sale.order"].sudo()
Move = env["stock.move"].sudo()
Picking = env["stock.picking"].sudo()

tmpl = Template.search([("default_code", "=", SKU)], limit=1)
if not tmpl:
    tmpl = Template.search([("name", "ilike", "Latitude 3301")], limit=1)

print("=" * 60)
print("PRODUCT TEMPLATE")
print("=" * 60)
if not tmpl:
    print("NOT FOUND")
else:
    print(f"id={tmpl.id} code={tmpl.default_code!r} name={tmpl.name!r}")
    print(f"tracking={tmpl.tracking} type={tmpl.type}")
    print(f"qty_available(on hand)={tmpl.qty_available}")
    print(f"virtual_available(forecast)={tmpl.virtual_available}")
    print(f"incoming_qty={tmpl.incoming_qty} outgoing_qty={tmpl.outgoing_qty}")
    print(f"_rw_website_available_qty={tmpl._rw_website_available_qty()}")

variants = Product.search(
    [
        "|",
        ("default_code", "=", SKU),
        ("product_tmpl_id", "=", tmpl.id if tmpl else 0),
    ]
)
print("\n" + "=" * 60)
print("VARIANTS & QUANTS")
print("=" * 60)
for v in variants:
    print(
        f"\nvariant id={v.id} code={v.default_code!r} active={v.active} "
        f"on_hand={v.qty_available} free_qty={v.free_qty} "
        f"virtual={v.virtual_available} outgoing={v.outgoing_qty}"
    )
    lots = Lot.search([("product_id", "=", v.id)])
    print(f"  lots registered: {len(lots)}")
    quants = Quant.search(
        [
            ("product_id", "=", v.id),
            ("location_id.usage", "=", "internal"),
        ]
    )
    pos = quants.filtered(lambda q: q.quantity > 0)
    neg = quants.filtered(lambda q: q.quantity < 0)
    no_lot = pos.filtered(lambda q: not q.lot_id)
    with_lot = pos.filtered(lambda q: q.lot_id)
    print(f"  internal quants: +qty={sum(pos.mapped('quantity'))} units={len(pos)}")
    print(f"    with lot: {sum(with_lot.mapped('quantity'))} ({len(with_lot)} rows)")
    print(f"    NO lot:   {sum(no_lot.mapped('quantity'))} ({len(no_lot)} rows)")
    print(f"  reserved on quants: {sum(quants.mapped('reserved_quantity'))}")
    for q in with_lot:
        print(
            f"    {q.location_id.complete_name}: lot={q.lot_id.name!r} "
            f"qty={q.quantity} reserved={q.reserved_quantity}"
        )

print("\n" + "=" * 60)
print("SALE ORDER LINES (LAT3301)")
print("=" * 60)
lines = env["sale.order.line"].sudo().search(
    [
        "|",
        ("product_id.default_code", "=", SKU),
        ("product_id.product_tmpl_id", "=", tmpl.id if tmpl else 0),
    ],
    order="order_id desc",
)
by_state = {}
for line in lines:
    o = line.order_id
    st = o.state
    by_state.setdefault(st, []).append(o)
    print(
        f"  {o.name} state={o.state} partner={o.partner_id.name!r} "
        f"qty={line.product_uom_qty} delivered={line.qty_delivered} "
        f"invoice={o.invoice_status} date={o.date_order}"
    )

print("\nSummary by order state:")
for st, orders in sorted(by_state.items()):
    print(f"  {st}: {len(set(orders))} orders")

print("\n" + "=" * 60)
print("OPEN STOCK MOVES / PICKINGS (LAT3301)")
print("=" * 60)
moves = Move.search(
    [
        ("product_id", "in", variants.ids),
        ("state", "not in", ("done", "cancel")),
    ]
)
for m in moves:
    print(
        f"  move id={m.id} state={m.state} qty={m.product_uom_qty} "
        f"reserved={m.quantity} picking={m.picking_id.name or '-'} "
        f"origin={m.origin or '-'} SO state?"
    )
    for ml in m.move_line_ids:
        print(f"    ml lot={ml.lot_id.name if ml.lot_id else '-'} qty={ml.quantity} reserved")

pickings = Picking.search(
    [
        ("move_ids.product_id", "in", variants.ids),
        ("state", "not in", ("done", "cancel")),
    ]
)
for p in pickings:
    print(f"  picking {p.name} state={p.state} origin={p.origin}")

print("\n" + "=" * 60)
print("ALL SALE ORDERS (recent 30)")
print("=" * 60)
for o in SO.search([], order="id desc", limit=30):
    lat_lines = o.order_line.filtered(
        lambda l: l.product_id.default_code == SKU
        or (tmpl and l.product_id.product_tmpl_id.id == tmpl.id)
    )
    flag = " *** LAT3301" if lat_lines else ""
    print(
        f"  {o.name} id={o.id} state={o.state} partner={o.partner_id.name!r} "
        f"total={o.amount_total}{flag}"
    )
