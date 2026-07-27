# -*- coding: utf-8 -*-
"""
Add serial PC14S0AQ onto ThinkPad T480s CMOSP (Under 70% battery).

Blancco (reports.csv):
  MTM 20L8SDCE00, 8GB, 256GB, CMOS successful, battery 39%
  → Shop SKU 20L8SDCE00-8G-256G-T-BTU70-CMOSP
Scan file did not include this SN, so merge never imported it.

DRY_RUN=True  → inspect only (default)
DRY_RUN=False + confirm_apply="APPLY" → create lot + stock qty 1

Production (pipe via Run Odoo shell workflow, or local docker against prod DB):
  # 1) DRY RUN first — paste output, wait for OK
  # 2) Then set DRY_RUN=False and confirm_apply="APPLY"
"""
DRY_RUN = True
confirm_apply = ""  # must be "APPLY" when DRY_RUN=False

SERIAL = "PC14S0AQ"
# Prod SKUs include RAM/SSD/Touch when MTM has multiple configs.
# Blancco PC14S0AQ: 8GB / 256GB NVMe / batt 39% (BTU70) / CMOS successful.
TARGET_SKU = "20L8SDCE00-8G-256G-T-BTU70-CMOSP"

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)
Lot = env["stock.lot"].sudo()
Quant = env["stock.quant"].sudo()
wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)

print("=" * 60)
print("Add serial to product")
print("  SERIAL:", SERIAL)
print("  TARGET_SKU:", TARGET_SKU)
print("  DRY_RUN:", DRY_RUN)
print("=" * 60)

tmpl, code = Importer._find_product_by_sku(TARGET_SKU)
if not tmpl:
    # Fallback candidates if exact code drifted
    for cand in (
        TARGET_SKU,
        "20L8SDCE00-8G-256G-T-BTU70-CMOSP",
        "20L8SDCE00-BTU70-CMOSP",
        "20L8SDCE00",
    ):
        tmpl, code = Importer._find_product_by_sku(cand)
        if tmpl:
            print("Resolved SKU via fallback:", code, "tmpl_id=", tmpl.id)
            break
if not tmpl:
    raise SystemExit("Product %s not found. Import CMOSP catalog first." % TARGET_SKU)

print(
    "Product:",
    tmpl.default_code,
    "|",
    tmpl.name,
    "| id=",
    tmpl.id,
    "| published=",
    tmpl.website_published,
    "| on_hand=",
    tmpl.qty_available,
)

variant = Importer._stock_variant_for_unit(tmpl, code or tmpl.default_code)
if not variant:
    raise SystemExit("No stockable variant for %s" % tmpl.default_code)
print("Variant id=", variant.id, "code=", variant.default_code)

existing = Lot.search([("name", "=ilike", SERIAL)])
print("Existing lots named %s: %s" % (SERIAL, len(existing)))
for lot in existing:
    free = Quant._get_available_quantity(lot.product_id, wh.lot_stock_id, lot_id=lot)
    print(
        "  lot_id=%s product=%s free=%s delivered=%s"
        % (
            lot.id,
            lot.product_id.default_code,
            free,
            Importer._serial_is_delivered(SERIAL, lot.product_id.id),
        )
    )

same = existing.filtered(lambda l: l.product_id.id == variant.id)[:1]
if same:
    free = Quant._get_available_quantity(variant, wh.lot_stock_id, lot_id=same)
    print("Already on target product. free qty=", free)
    if free >= 1:
        print("Nothing to do.")
        raise SystemExit(0)

if DRY_RUN:
    print("\n[DRY_RUN] Would:")
    if same:
        print("  - set on-hand qty=1 for existing lot on", tmpl.default_code)
    elif existing:
        print(
            "  - move/create lot on",
            tmpl.default_code,
            "(other product currently has this SN)",
        )
    else:
        print("  - create stock.lot", SERIAL, "on", tmpl.default_code)
        print("  - set inventory qty=1 at", wh.lot_stock_id.complete_name)
    print("  - ensure website_published/sale_ok if on_hand>0")
    print("\nSet DRY_RUN=False and confirm_apply='APPLY' to write.")
    raise SystemExit(0)

if confirm_apply != "APPLY":
    raise SystemExit('Refusing write: set confirm_apply="APPLY" when DRY_RUN=False')

# If SN exists on another product, move it; else create + stock.
if existing and not same:
    lot = existing[0]
    ok = Importer._move_serial_lot_to_variant(lot, variant, wh)
    if not ok:
        lot = Importer._find_or_create_lot(variant, SERIAL)
        Importer._set_serial_stock_one(variant, lot, wh)
    print("Moved/stocked existing lot onto", tmpl.default_code)
else:
    lot = Importer._find_or_create_lot(variant, SERIAL)
    applied, skipped = Importer._set_serial_stock_one(variant, lot, wh)
    print("Stock apply: applied=%s skipped=%s lot_id=%s" % (applied, skipped, lot.id))

tmpl.invalidate_recordset()
variant.invalidate_recordset()
if tmpl.qty_available > 0 and not tmpl.website_published:
    tmpl.with_context(rw_skip_cmos_shop_sync=True).write(
        {"website_published": True, "sale_ok": True, "active": True}
    )

pass_lot = Lot.search(
    [("product_id", "=", variant.id), ("name", "=ilike", SERIAL)], limit=1
)
free = 0.0
if pass_lot:
    free = Quant._get_available_quantity(variant, wh.lot_stock_id, lot_id=pass_lot)

print("\n=== Result ===")
print("  SKU:", tmpl.default_code)
print("  on_hand:", tmpl.qty_available)
print("  %s free:" % SERIAL, free)
print("  published:", tmpl.website_published)
if free < 1:
    print("  WARNING: SN still not available — check Inventory -> Lots / Serial Numbers")
else:
    env.cr.commit()
    print("  COMMITTED.")
