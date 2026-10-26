# -*- coding: utf-8 -*-
"""Local / prod Odoo shell: quote delivery fee for sample cart (read-only except temp SO).

Edit the CONFIG block, then pipe into odoo shell:

  Get-Content scripts\\test_delivery_fee_local_shell.py |
    docker compose run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init

Requires: pipeline keys in Settings (or System Parameters), products with pack dims.
"""
# --- CONFIG (edit me) ---
TO_POSTCODE = "3000"
# product.template ids (same as product_id in product_weights / pack dims CSV)
TEMPLATE_IDS = [863, 726]  # e.g. T14s + 24" monitor
QTY_PER_TEMPLATE = 1
# --- end CONFIG ---

Integration = env["rw.shipping.integration"]
print("=" * 72)
print("Delivery fee test cart")
print(f"  pipeline_enabled: {Integration.pipeline_enabled()}")
print(f"  packaging: {Integration._packaging_params()}")
print(f"  to_postcode: {TO_POSTCODE}")
print(f"  templates: {TEMPLATE_IDS}")
print("=" * 72)

au = env["res.country"].search([("code", "=", "AU")], limit=1)
partner = env["res.partner"].sudo().search(
    [("country_id", "=", au.id), ("zip", "=", TO_POSTCODE)], limit=1
)
if not partner:
    partner = env["res.partner"].sudo().create(
        {
            "name": "Shipping test %s" % TO_POSTCODE,
            "country_id": au.id,
            "zip": TO_POSTCODE,
        }
    )

order = env["sale.order"].sudo().create(
    {
        "partner_id": partner.id,
        "partner_shipping_id": partner.id,
    }
)
for tmpl_id in TEMPLATE_IDS:
    tmpl = env["product.template"].sudo().browse(tmpl_id)
    if not tmpl.exists():
        print(f"MISSING template id={tmpl_id}")
        continue
    product = tmpl.product_variant_ids[:1]
    if not product:
        print(f"NO VARIANT template id={tmpl_id}")
        continue
    env["sale.order.line"].sudo().create(
        {
            "order_id": order.id,
            "product_id": product.id,
            "product_uom_qty": QTY_PER_TEMPLATE,
        }
    )
    print(
        f"  line: {product.display_name[:50]} "
        f"dims={tmpl.rw_ship_length_cm}x{tmpl.rw_ship_width_cm}x{tmpl.rw_ship_height_cm} "
        f"weight={product.weight}"
    )

if not order.order_line:
    print("No lines — fix TEMPLATE_IDS")
else:
    items = Integration._build_items_from_order(order)
    print("Cartonization input (after padding):")
    for it in items:
        print(f"  {it}")
    legacy = order._rw_freight_price_legacy_ex_gst()
    print(f"Legacy $/kg ex GST: {legacy:.2f}")
    try:
        price = Integration.quote_order_freight_ex_gst(order)
        print(f"AusPost pipeline ex GST: {price:.2f}")
    except Exception as exc:
        print(f"AusPost pipeline FAILED: {type(exc).__name__}: {exc}")
    try:
        order._rw_ensure_default_freight()
        delivery = order.order_line.filtered("is_delivery")
        if delivery:
            print(
                f"_rw_ensure_default_freight delivery line: "
                f"{delivery[0].price_unit:.2f} (ex tax on line as stored)"
            )
    except Exception as exc:
        print(f"Freight hook FAILED: {exc}")

order.unlink()
print("Done (temp order removed).")
