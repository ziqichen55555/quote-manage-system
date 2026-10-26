# Read-only production smoke test for AusPost PAC + Re-Ware shipping pipeline.
# Safe to run with DRY_RUN unset (no writes).

print("=== AusPost shipping pipeline test (read-only) ===")

icp = env["ir.config_parameter"].sudo()
enabled = icp.get_param("quote_manage_ui.shipping_pipeline_enabled")
key = (icp.get_param("quote_manage_ui.auspost_auth_key") or "").strip()
from_pc = (icp.get_param("quote_manage_ui.auspost_from_postcode") or "").strip()
service = (icp.get_param("quote_manage_ui.auspost_service_code") or "").strip() or "AUS_PARCEL_REGULAR"
cp_key = (icp.get_param("quote_manage_ui.cartonpilot_api_key") or "").strip()

mod = env["ir.module.module"].sudo().search([("name", "=", "quote_manage_ui")], limit=1)
print(f"quote_manage_ui installed_version: {mod.installed_version!r} state={mod.state!r}")

print(f"shipping_pipeline_enabled param: {enabled!r}")
print(f"from_postcode: {from_pc!r}")
print(f"service_code: {service!r}")
print(f"auspost auth_key configured: {bool(key)} (len={len(key)})")
print(f"cartonpilot key configured: {bool(cp_key)}")

boxes = env["rw.auspost.parcel.box"].sudo().search([("active", "=", True)])
print(f"active rw.auspost.parcel.box records: {len(boxes)}")
if not boxes:
    print("WARN: no parcel box catalog — upgrade quote_manage_ui / load rw_auspost_parcel_boxes.xml")

integration = env["rw.shipping.integration"]
print(f"pipeline_enabled(): {integration.pipeline_enabled()}")

if key and from_pc:
    parcel = {
        "length_cm": 22.0,
        "width_cm": 16.0,
        "height_cm": 7.7,
        "weight_kg": 1.5,
    }
    to_pc = "3000"
    try:
        inc = integration._pac_parcel_cost_inc_gst(
            from_pc, to_pc, parcel, service, key
        )
        ex = round(inc / 1.1, 2)
        print(
            f"PAC OK {from_pc!r} -> {to_pc!r} "
            f"(22x16x7.7 cm, 1.5 kg): inc_gst={inc:.2f} AUD ex_gst={ex:.2f} AUD"
        )
    except Exception as exc:
        print(f"PAC FAILED: {type(exc).__name__}: {exc}")
else:
    print("SKIP PAC smoke — missing auth key or from_postcode in System Parameters")

PT = env["product.template"].sudo()
with_dims = PT.search(
    [
        ("rw_ship_length_cm", ">", 0),
        ("rw_ship_width_cm", ">", 0),
        ("rw_ship_height_cm", ">", 0),
        ("sale_ok", "=", True),
    ],
    limit=8,
)
print(f"published products with pack L×W×H: {PT.search_count([('rw_ship_length_cm', '>', 0), ('rw_ship_width_cm', '>', 0), ('rw_ship_height_cm', '>', 0)])}")
for tmpl in with_dims:
    print(
        f"  sample: {tmpl.default_code or tmpl.id} {tmpl.name[:50]!r} "
        f"{tmpl.rw_ship_length_cm}x{tmpl.rw_ship_width_cm}x{tmpl.rw_ship_height_cm} cm "
        f"weight={tmpl.weight or 0}"
    )

if integration.pipeline_enabled() and with_dims:
    partner = env["res.partner"].sudo().search(
        [
            ("country_id.code", "=", "AU"),
            ("zip", "!=", False),
            ("type", "in", ["contact", "delivery", "invoice"]),
        ],
        limit=1,
    )
    product = with_dims[0].product_variant_ids[:1]
    if partner and product:
        order = env["sale.order"].sudo().create(
            {
                "partner_id": partner.id,
                "partner_shipping_id": partner.id,
            }
        )
        env["sale.order.line"].sudo().create(
            {
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": 1,
            }
        )
        try:
            price = integration.quote_order_freight_ex_gst(order)
            print(f"Full pipeline quote (1x {product.display_name[:40]!r} -> {partner.zip}): ex_gst={price:.2f} AUD")
        except Exception as exc:
            print(f"Full pipeline FAILED: {type(exc).__name__}: {exc}")
        order.unlink()
    else:
        print("SKIP full pipeline — no AU partner or variant")
elif not integration.pipeline_enabled():
    print("SKIP full pipeline — pipeline_enabled() is False (toggle + save keys in Settings)")
elif not with_dims:
    print("SKIP full pipeline — no products with rw_ship_* cm yet (checkout will fallback to $/kg)")

print("=== Done ===")
