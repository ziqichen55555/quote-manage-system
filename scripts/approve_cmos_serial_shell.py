# -*- coding: utf-8 -*-
"""
Approve CMOS for one serial (scheme B): CMOSFL -> CMOSP.

PC1FSFY8 default: battery 70%+ bucket, CMOS manually approved in warehouse.

Production:
  # copy script to server or pipe from repo
  Get-Content scripts/approve_cmos_serial_shell.py | docker compose run --rm -T web odoo shell \\
    -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init

Odoo UI (whole CMOSFL bucket — moves ALL serials on that SKU):
  Product -> 20NYS4CP00-8G-256G-T-BT70-CMOSFL -> CMOS attribute -> Successful -> Save
"""
SERIAL = "PC1FSFY8"
FAIL_SKU = "20NYS4CP00-8G-256G-T-BT70-CMOSFL"

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)
Lot = env["stock.lot"].sudo()
wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)

pass_code = Importer._cmos_pass_code_for_fail(FAIL_SKU)
fail_tmpl = PT.search([("default_code", "=", FAIL_SKU)], limit=1)

if not fail_tmpl:
    pass_tmpl = PT.search([("default_code", "=", pass_code)], limit=1)
    if pass_tmpl:
        print("Creating CMOSFL bucket from CMOSP master:", FAIL_SKU)
        fail_tmpl = pass_tmpl.copy(
            {
                "default_code": FAIL_SKU,
                "barcode": FAIL_SKU,
                "website_published": False,
                "sale_ok": False,
            }
        )
        Importer._ensure_active_variant(fail_tmpl, FAIL_SKU)
        Importer._set_cmos_attribute_value(fail_tmpl, "Failed")
    else:
        raise SystemExit(
            "Neither %s nor %s found. Upload MERGED import-ready CSV first."
            % (FAIL_SKU, pass_code)
        )

print("=" * 60)
print("CMOS approve (single serial):", SERIAL)
print("  fail:", FAIL_SKU, "tmpl_id=", fail_tmpl.id)
print("  pass:", pass_code)
print("=" * 60)

pass_tmpl, pass_code = Importer._ensure_cmos_pass_bucket_product(fail_tmpl)
fail_var = Importer._stock_variant_for_unit(fail_tmpl, FAIL_SKU)
pass_var = Importer._stock_variant_for_unit(pass_tmpl, pass_code)

lot = Lot.search([("name", "=ilike", SERIAL)], limit=1)
if lot and lot.product_id.id not in (fail_var.id, pass_var.id):
    print(
        "Warning: lot on other product %r — will move to CMOSP."
        % lot.product_id.default_code
    )

if not lot:
    print("No lot in DB; stocking on CMOSFL then moving to CMOSP...")
    lot = Importer._find_or_create_lot(fail_var, SERIAL.strip().upper())
    Importer._set_serial_stock_one(fail_var, lot, wh)

if lot.product_id.id == pass_var.id:
    print("Already on CMOSP:", pass_code)
else:
    ok = Importer._move_serial_lot_to_variant(lot, pass_var, wh)
    if not ok:
        Importer._set_serial_stock_one(pass_var, Importer._find_or_create_lot(pass_var, SERIAL), wh)
    print("Moved %s -> %s (variant %s)" % (SERIAL, pass_code, pass_var.id))

Importer._set_cmos_attribute_value(
    pass_tmpl.with_context(rw_skip_cmos_shop_sync=True), "Successful"
)
pass_tmpl.with_context(rw_skip_cmos_shop_sync=True).write(
    {"website_published": True, "sale_ok": True, "active": True}
)

pass_lot = Lot.search(
    [("product_id", "=", pass_var.id), ("name", "=ilike", SERIAL)], limit=1
)
free = 0.0
if pass_lot:
    free = env["stock.quant"].sudo()._get_available_quantity(
        pass_var, wh.lot_stock_id, lot_id=pass_lot
    )

print("\n=== Result ===")
print("  Order / delivery SKU:", pass_code)
print("  product_id:", pass_var.id)
print("  pass on_hand:", pass_var.qty_available)
print("  %s free on CMOSP:" % SERIAL, free)
if free < 1:
    print("  WARNING: SN still not available — check Inventory -> Lots")
