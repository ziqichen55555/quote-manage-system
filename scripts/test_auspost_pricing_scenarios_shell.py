# -*- coding: utf-8 -*-
"""AusPost PAC + pipeline pricing scenarios (read-only temp orders)."""
from odoo.exceptions import UserError

Integration = env["rw.shipping.integration"]
icp = env["ir.config_parameter"].sudo()
au = env["res.country"].search([("code", "=", "AU")], limit=1)
from_pc = (icp.get_param("quote_manage_ui.auspost_from_postcode") or "").strip()

print("=" * 80)
print("AusPost API & pricing scenario report")
print("=" * 80)
print(f"quote_manage_ui: {env['ir.module.module'].sudo().search([('name','=','quote_manage_ui')], limit=1).installed_version}")
print(f"pipeline_enabled: {Integration.pipeline_enabled()}")
print(f"from_postcode: {from_pc!r}")
if hasattr(Integration, "_packaging_params"):
    print(f"packaging: {Integration._packaging_params()}")
else:
    print("packaging: (module < 1.0.213 — no foam padding in code yet)")
print(f"cartonpilot key: {bool((icp.get_param('quote_manage_ui.cartonpilot_api_key') or '').strip())}")
print(f"products with pack dims (sale_ok): {env['product.template'].sudo().search_count([('sale_ok','=',True),('rw_ship_length_cm','>',0),('rw_ship_width_cm','>',0),('rw_ship_height_cm','>',0)])}")
print("-" * 80)

# --- Direct PAC smoke (no Odoo products) ---
key = (icp.get_param("quote_manage_ui.auspost_auth_key") or "").strip()
service = (icp.get_param("quote_manage_ui.auspost_service_code") or "AUS_PARCEL_REGULAR").strip()
if key and from_pc:
    pac_cases = [
        ("Small parcel (Bx1-ish)", 22, 16, 7.7, 1.5, "3000"),
        ("Laptop-sized", 38, 28, 5, 2.5, "3000"),
        ("24in monitor", 55, 35, 12, 5, "3000"),
        ("Same laptop -> Perth", 38, 28, 5, 2.5, "6000"),
        ("Same laptop -> rural NT", 38, 28, 5, 2.5, "0870"),
        ("Heavy 10kg box", 40, 30, 25, 10, "3000"),
    ]
    print("PAC direct (inc GST -> ex GST):")
    for label, l, w, h, kg, to_pc in pac_cases:
        parcel = {"length_cm": l, "width_cm": w, "height_cm": h, "weight_kg": kg}
        try:
            inc = Integration._pac_parcel_cost_inc_gst(
                from_pc, to_pc, parcel, service, key
            )
            ex = round(inc / 1.1, 2)
            print(f"  OK  {label:28} {from_pc}->{to_pc}  inc={inc:7.2f}  ex={ex:7.2f} AUD")
        except Exception as exc:
            print(f"  FAIL {label:28} {from_pc}->{to_pc}  {type(exc).__name__}: {exc}")
else:
    print("SKIP PAC direct — missing key or from_postcode")
print("-" * 80)


def partner_for_postcode(zip_code):
    p = env["res.partner"].sudo().search(
        [("country_id", "=", au.id), ("zip", "=", zip_code)], limit=1
    )
    if not p:
        p = env["res.partner"].sudo().create(
            {"name": "Pricing test %s" % zip_code, "country_id": au.id, "zip": zip_code}
        )
    return p


def quote_cart(label, template_ids, qty, to_postcode):
    """Returns dict with legacy, pipeline, parcels info."""
    partner = partner_for_postcode(to_postcode)
    order = env["sale.order"].sudo().create(
        {"partner_id": partner.id, "partner_shipping_id": partner.id}
    )
    names = []
    for tid in template_ids:
        tmpl = env["product.template"].sudo().browse(tid)
        if not tmpl.exists():
            continue
        prod = tmpl.product_variant_ids[:1]
        if not prod:
            continue
        env["sale.order.line"].sudo().create(
            {
                "order_id": order.id,
                "product_id": prod.id,
                "product_uom_qty": qty,
            }
        )
        names.append(
            "%s (%sx%sx%s cm, %skg)"
            % (
                (tmpl.default_code or tmpl.id),
                tmpl.rw_ship_length_cm,
                tmpl.rw_ship_width_cm,
                tmpl.rw_ship_height_cm,
                prod.weight or 0,
            )
        )
    legacy = order._rw_freight_price_legacy_ex_gst()
    checkout = order._rw_freight_price_ex_gst()
    err = None
    n_parcels = None
    weight_kg = order._rw_shipping_weight_kg()
    try:
        if (
            weight_kg >= order._rw_freight_pac_min_kg()
            and Integration.pipeline_enabled()
            and order._rw_freight_product_lines()
        ):
            items = Integration._build_items_from_order(order)
            boxes = Integration._active_auspost_boxes()
            parcels = Integration._cartonize_cartonpilot(items, boxes)
            if hasattr(Integration, "_packaging_params"):
                extra = Integration._packaging_params()["extra_kg_per_parcel"]
                for p in parcels:
                    p["weight_kg"] = float(p.get("weight_kg") or 0.1) + extra
            n_parcels = len(parcels)
    except Exception as exc:
        err = "%s: %s" % (type(exc).__name__, exc)
    order.unlink()
    return {
        "label": label,
        "to": to_postcode,
        "items": "; ".join(names) or "(empty)",
        "qty": qty,
        "legacy_ex": legacy,
        "pipeline_ex": checkout,
        "weight_kg": weight_kg,
        "parcels": n_parcels,
        "error": err,
    }


# template ids from product_weights_prod.csv (common SKUs)
T = {
    "cable": 915,
    "monitor24": 726,
    "laptop_t14s": 863,
    "dock": 714,
    "dual_monitors": 719,
    "switch48": 738,
}

scenarios = [
    ("1x cable adapter", [T["cable"]], 1, "3000"),
    ("1x ThinkPad T14s Gen 2i", [T["laptop_t14s"]], 1, "3000"),
    ("1x 24in Samsung monitor", [T["monitor24"]], 1, "3000"),
    ("1x HP G3 dock", [T["dock"]], 1, "3000"),
    ("Laptop + monitor (Melb)", [T["laptop_t14s"], T["monitor24"]], 1, "3000"),
    ("2x laptops same order", [T["laptop_t14s"]], 2, "3000"),
    ("Dual monitor bundle SKU", [T["dual_monitors"]], 1, "3000"),
    ("Laptop to Perth", [T["laptop_t14s"]], 1, "6000"),
    ("Laptop to Sydney", [T["laptop_t14s"]], 1, "2000"),
    ("Monitor to Darwin (0870)", [T["monitor24"]], 1, "0870"),
    ("48-port switch (heavy)", [T["switch48"]], 1, "3000"),
]

print("Cart scenarios (legacy $/kg vs website checkout _rw_freight_price_ex_gst):")
print(
    f"{'Scenario':<32} {'To':>5} {'kg':>5} {'Parcels':>7} {'Legacy':>8} {'Checkout':>9}  Notes"
)
print("-" * 80)
for label, tids, qty, to_pc in scenarios:
    r = quote_cart(label, tids, qty, to_pc)
    pipe = f"{r['pipeline_ex']:.2f}" if r["pipeline_ex"] is not None else "—"
    par = str(r["parcels"]) if r["parcels"] is not None else "—"
    w = f"{r.get('weight_kg', 0):.1f}"
    note = r["error"] or r["items"][:40]
    print(
        f"{r['label']:<32} {r['to']:>5} {w:>5} {par:>7} {r['legacy_ex']:>8.2f} {pipe:>9}  {note}"
    )

print("-" * 80)
print("Legacy = ceil(total kg) x $25 ex GST (fallback when PAC fails/disabled).")
print("Checkout = flat $25 ex if total kg < 1; else AusPost PAC (same as website).")
print("=" * 80)
print("Done.")
