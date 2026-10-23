# -*- coding: utf-8 -*-
"""Rename lot PC1ACZJ2 -> PC1ACZJ2-CHANGED (S00138); frees original SN for new stock."""
DRY_RUN = False

SERIAL_OLD = "PC1ACZJ2"
SERIAL_NEW = "PC1ACZJ2-CHANGED"
ORDER_NAME = "S00138"

print(f"=== Rename SN {SERIAL_OLD} -> {SERIAL_NEW} (DRY_RUN={DRY_RUN}) ===")

Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
SaleOrder = env["sale.order"].sudo()

lots = Lot.search([("name", "=", SERIAL_OLD)])
if not lots:
    already = Lot.search([("name", "=", SERIAL_NEW)], limit=1)
    if already:
        print(f"Already renamed: lot id={already.id} name={already.name!r}")
    else:
        print(f"ERROR: No lot named {SERIAL_OLD!r}")
else:
    if len(lots) > 1:
        print(f"WARNING: {len(lots)} lots named {SERIAL_OLD!r}; renaming all.")
    for lot in lots:
        print(
            f"Lot id={lot.id} product={lot.product_id.default_code or lot.product_id.display_name} "
            f"'{lot.name}' -> '{SERIAL_NEW}'"
        )
        quants = Quant.search([("lot_id", "=", lot.id)])
        for q in quants:
            print(
                f"  quant loc={q.location_id.complete_name} qty={q.quantity:g} "
                f"reserved={q.reserved_quantity:g}"
            )
            if not DRY_RUN and q.quantity == 0 and q.reserved_quantity != 0:
                ghost = q.reserved_quantity
                q.write({"reserved_quantity": 0})
                print(f"    cleared ghost reservation {ghost:g}")
        if not DRY_RUN:
            lot.write({"name": SERIAL_NEW})
            print("  renamed OK")
        else:
            print("  (dry run, no write)")

order = SaleOrder.search([("name", "=", ORDER_NAME)], limit=1)
if order and not DRY_RUN and lots:
    order.message_post(
        body=(
            f"Serial {SERIAL_OLD} renamed to {SERIAL_NEW} to free the original SN "
            f"for new inventory (order kept)."
        )
    )
    print(f"Chatter note posted on {ORDER_NAME}")

if DRY_RUN:
    print("\nDRY RUN — no commit.")
else:
    print("\nCommitting...")
    env.cr.commit()
    print("Done.")
