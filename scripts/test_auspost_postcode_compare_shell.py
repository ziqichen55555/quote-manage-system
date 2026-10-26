# -*- coding: utf-8 -*-
"""PAC postcode sensitivity + website freight hook (read-only temp orders)."""
Integration = env["rw.shipping.integration"]
icp = env["ir.config_parameter"].sudo()
from_pc = (icp.get_param("quote_manage_ui.auspost_from_postcode") or "").strip()
key = (icp.get_param("quote_manage_ui.auspost_auth_key") or "").strip()
service = (icp.get_param("quote_manage_ui.auspost_service_code") or "AUS_PARCEL_REGULAR").strip()
au = env["res.country"].search([("code", "=", "AU")], limit=1)

print("=" * 72)
print("AusPost postcode compare (PAC API + checkout freight)")
print("from_postcode:", from_pc)
print("pipeline:", Integration.pipeline_enabled())
print("-" * 72)

if not key or not from_pc:
    print("SKIP — missing PAC key or from_postcode")
else:
    parcel = {"length_cm": 38, "width_cm": 28, "height_cm": 5, "weight_kg": 2.5}
    postcodes = ["2000", "3000", "4702", "6000", "0870", "9999"]
    print("PAC direct (same 38x28x5 cm, 2.5 kg) inc GST -> ex GST:")
    for to_pc in postcodes:
        try:
            inc = Integration._pac_parcel_cost_inc_gst(
                from_pc, to_pc, parcel, service, key
            )
            ex = round(inc / 1.1, 2)
            print("  %s -> %s  inc=%7.2f  ex=%7.2f" % (from_pc, to_pc, inc, ex))
        except Exception as exc:
            print("  %s -> %s  FAIL %s: %s" % (from_pc, to_pc, type(exc).__name__, exc))

print("-" * 72)
# Same product, different shipping partner zip (checkout path)
T_LAPTOP = 863
print("Checkout _rw_freight_price_ex_gst for ThinkPad T14s template id %s:" % T_LAPTOP)


def partner_zip(zip_code):
    p = env["res.partner"].sudo().search(
        [("country_id", "=", au.id), ("zip", "=", zip_code)], limit=1
    )
    if not p:
        p = env["res.partner"].sudo().create(
            {
                "name": "Postcode test %s" % zip_code,
                "country_id": au.id,
                "zip": zip_code,
                "city": "Test",
                "street": "1 Test St",
            }
        )
    return p


for to_pc in ["3000", "4702", "2000"]:
    partner = partner_zip(to_pc)
    order = env["sale.order"].sudo().create(
        {"partner_id": partner.id, "partner_shipping_id": partner.id}
    )
    tmpl = env["product.template"].sudo().browse(T_LAPTOP)
    prod = tmpl.product_variant_ids[:1]
    env["sale.order.line"].sudo().create(
        {
            "order_id": order.id,
            "product_id": prod.id,
            "product_uom_qty": 1,
        }
    )
    ship_zip = (order.partner_shipping_id.zip or "").strip()
    weight = order._rw_shipping_weight_kg()
    try:
        fee = order._rw_freight_price_ex_gst()
        err = ""
    except Exception as exc:
        fee = None
        err = "%s: %s" % (type(exc).__name__, exc)
    print(
        "  to_pc=%s  partner.zip=%r  weight=%.2f kg  freight_ex=%s  %s"
        % (to_pc, ship_zip, weight, fee, err)
    )
    order.unlink()

print("=" * 72)
print("If PAC direct rows differ but checkout fees identical, check markup/threshold.")
print("If all PAC rows identical, AusPost rate table — not a website bug.")
print("Done.")
