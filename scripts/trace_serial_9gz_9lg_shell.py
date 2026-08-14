# -*- coding: utf-8 -*-
"""Read-only: full lifecycle trace for PC1PQ9GZ / PC1PQ9LG."""
SERIALS = ["PC1PQ9GZ", "PC1PQ9LG"]

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
MoveLine = env["stock.move.line"].sudo()
Picking = env["stock.picking"].sudo()
SO = env["sale.order"].sudo()
SOL = env["sale.order.line"].sudo()

print("=== SERIAL LIFECYCLE TRACE (read-only) ===")

for sn in SERIALS:
    print("\n" + "#" * 72)
    print(f"# {sn}")
    print("#" * 72)

    lots = Lot.search([("name", "=", sn)])
    if not lots:
        print("NOT FOUND")
        continue

    for lot in lots:
        sku = lot.product_id.default_code or ""
        tmpl = lot.product_id.product_tmpl_id
        create_date = lot.create_date
        print(f"lot_id={lot.id} create_date={create_date}")
        print(f"product={sku!r} tmpl={tmpl.default_code!r} name={tmpl.name!r}")

        # Current quants
        print("\n[CURRENT QUANTS]")
        internal = 0.0
        for q in Quant.search([("lot_id", "=", lot.id)]):
            print(
                f"  quant={q.id} loc={q.location_id.complete_name} usage={q.location_id.usage} "
                f"qty={q.quantity:g} reserved={q.reserved_quantity:g} in_date={q.in_date}"
            )
            if q.location_id.usage == "internal":
                internal += q.quantity
        print(f"  => net internal now: {internal:g}")

        # Full move line timeline (oldest first)
        mls = MoveLine.search([("lot_id", "=", lot.id)], order="date asc, id asc")
        print(f"\n[MOVE LINE TIMELINE] count={len(mls)}")
        for ml in mls:
            qty = getattr(ml, "qty_done", None) or ml.quantity
            pick = ml.picking_id
            pick_name = pick.name if pick else "-"
            pick_type = pick.picking_type_id.code if pick and pick.picking_type_id else "?"
            pick_state = pick.state if pick else "-"
            origin = pick.origin if pick else (ml.move_id.origin if ml.move_id else "")
            partner = pick.partner_id.display_name if pick and pick.partner_id else ""
            ref = pick.sale_id.name if pick and pick.sale_id else ""
            print(
                f"  {ml.date} | ml={ml.id} state={ml.state} type={pick_type} pick={pick_name}({pick_state})"
            )
            print(
                f"    {ml.location_id.display_name} -> {ml.location_dest_id.display_name} qty={qty:g}"
            )
            print(f"    origin={origin!r} sale={ref!r} partner={partner!r}")

        # Sale order lines that ever referenced this serial
        print("\n[SALE ORDERS touching this lot]")
        orders = SO.search([("order_line.move_ids.move_line_ids.lot_id", "=", lot.id)], order="id")
        if not orders:
            print("  (none)")
        for o in orders:
            print(
                f"  {o.name} state={o.state} date={o.date_order} "
                f"partner={o.partner_id.display_name} website={bool(o.website_id)}"
            )
            for line in o.order_line.filtered(lambda l: l.product_id == lot.product_id):
                delivered = line.qty_delivered
                print(
                    f"    line qty={line.product_uom_qty:g} delivered={delivered:g} "
                    f"product={line.product_id.default_code}"
                )
                for ml in line.move_ids.move_line_ids.filtered(lambda x: x.lot_id == lot):
                    pick = ml.picking_id.name if ml.picking_id else "-"
                    qty = getattr(ml, "qty_done", None) or ml.quantity
                    print(
                        f"      move {ml.location_id.display_name}->{ml.location_dest_id.display_name} "
                        f"qty={qty:g} pick={pick} state={ml.state}"
                    )

        # Other lots same serial name on different products?
        dup = Lot.search([("name", "=", sn), ("id", "!=", lot.id)])
        if dup:
            print("\n[DUPLICATE LOT RECORDS same SN on other products]")
            for d in dup:
                print(f"  lot={d.id} product={d.product_id.default_code}")

        # Narrative
        print("\n[INTERPRETATION]")
        outbound = mls.filtered(
            lambda ml: ml.state == "done"
            and ml.location_id.usage == "internal"
            and ml.location_dest_id.usage == "customer"
        )
        inbound_cust = mls.filtered(
            lambda ml: ml.state == "done"
            and ml.location_id.usage == "customer"
            and ml.location_dest_id.usage == "internal"
        )
        inv_adj_out = mls.filtered(
            lambda ml: ml.state == "done"
            and ml.location_id.usage == "internal"
            and ml.location_dest_id.usage == "inventory"
        )
        inv_adj_in = mls.filtered(
            lambda ml: ml.state == "done"
            and ml.location_id.usage == "inventory"
            and ml.location_dest_id.usage == "internal"
        )
        print(f"  import/adj into stock: {len(inv_adj_in)} move(s), total qty={sum((getattr(m,'qty_done',None) or m.quantity) for m in inv_adj_in):g}")
        print(f"  delivered to customer: {len(outbound)} move(s), total qty={sum((getattr(m,'qty_done',None) or m.quantity) for m in outbound):g}")
        print(f"  returned from customer: {len(inbound_cust)} move(s), total qty={sum((getattr(m,'qty_done',None) or m.quantity) for m in inbound_cust):g}")
        print(f"  adj out of stock: {len(inv_adj_out)} move(s), total qty={sum((getattr(m,'qty_done',None) or m.quantity) for m in inv_adj_out):g}")
        if internal > 0 and not outbound:
            print("  => Odoo still shows IN STOCK; never delivered out via customer location.")
        elif outbound and not inbound_cust and internal > 0:
            print("  => Delivered out BUT still shows stock — likely duplicate quant / bad return data.")
        elif outbound and inbound_cust:
            print("  => Was sold and returned; check if return was processed correctly.")
        elif outbound and not inbound_cust and internal <= 0:
            print("  => Sold/shipped; should not be in warehouse (if internal=0).")

print("\nDone.")
