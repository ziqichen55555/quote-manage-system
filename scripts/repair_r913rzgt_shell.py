# -*- coding: utf-8 -*-
"""One-off repair: R913RZGT ghost stock on obsolete 20TJS5WW00-BT70.

Safe scope — only touches the 20TJS5WW00 BT70 / CMOSP pair.
Set DRY_RUN=True to preview; False to apply.

Production:
  Get-Content scripts/repair_r913rzgt_shell.py -Raw |
    ssh -i $env:USERPROFILE\.ssh\id_ed25519_do root@134.199.145.67 `
    "docker compose -f /root/reware/docker-compose.yml run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init"
"""
DRY_RUN = False

KEEPER = "20TJS5WW00-BT70-CMOSP"
OBSOLETE = "20TJS5WW00-BT70"
SERIAL = "R913RZGT"

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
WH = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)


def snap(code):
    tmpl, c = Importer._find_product_by_sku(code)
    if not tmpl:
        return {"sku": code, "found": False}
    var = Importer._stock_variant_for_unit(tmpl, c)
    lots = []
    if var:
        for lot in Lot.search([("product_id", "=", var.id), ("name", "=", SERIAL)]):
            rows = Quant.search(
                [("lot_id", "=", lot.id), ("product_id", "=", var.id), ("quantity", "!=", 0)]
            )
            lots.append(
                {
                    "lot_id": lot.id,
                    "quants": [(q.location_id.complete_name, float(q.quantity)) for q in rows],
                }
            )
    return {
        "sku": c,
        "tmpl_id": tmpl.id,
        "active": tmpl.active,
        "sale_ok": tmpl.sale_ok,
        "is_published": tmpl.is_published,
        "on_hand": float(tmpl.qty_available),
        "lots": lots,
    }


def zero_serial_on_variant(variant, serial, force=False):
    out = []
    for lot in Lot.search([("product_id", "=", variant.id), ("name", "=", serial)]):
        if not force and Importer._serial_is_delivered(serial, variant.id):
            out.append({"serial": serial, "action": "skipped_delivered"})
            continue
        for quant in Quant.search(
            [
                ("lot_id", "=", lot.id),
                ("product_id", "=", variant.id),
                ("quantity", "!=", 0),
            ]
        ):
            loc = quant.location_id.complete_name
            before = float(quant.quantity)
            if not DRY_RUN:
                quant.with_context(inventory_mode=True).write(
                    {"inventory_quantity_auto_apply": 0.0}
                )
            out.append({"serial": serial, "location": loc, "before": before, "action": "zeroed"})
    return out


print("=" * 60)
print("REPAIR R913RZGT", "DRY_RUN=", DRY_RUN)
print("=" * 60)
print("BEFORE keeper:", snap(KEEPER))
print("BEFORE obsolete:", snap(OBSOLETE))

keeper_tmpl, keeper_code = Importer._find_product_by_sku(KEEPER)
obsolete_tmpl, obsolete_code = Importer._find_product_by_sku(OBSOLETE)
if not keeper_tmpl or not obsolete_tmpl:
    raise SystemExit("keeper or obsolete template missing")

keeper_var = Importer._stock_variant_for_unit(keeper_tmpl, keeper_code)
obsolete_var = Importer._stock_variant_for_unit(obsolete_tmpl, obsolete_code)

keeper_snap = Importer._serial_stock_snapshot(keeper_code)
keeper_has_sn = SERIAL.upper() in {s.upper() for s in (keeper_snap.get("lots_in_stock") or [])}
print("Keeper has serial in WH:", keeper_has_sn, keeper_snap)

if not keeper_has_sn:
    raise SystemExit("ABORT: keeper missing R913RZGT in warehouse — manual check needed")

zeroed = zero_serial_on_variant(obsolete_var, SERIAL, force=True)
print("Zeroed on obsolete:", zeroed)

if not DRY_RUN:
    obsolete_tmpl.invalidate_recordset()
    obsolete_var.invalidate_recordset()
    keeper_tmpl.invalidate_recordset()

    obsolete_tmpl.write(
        {"active": False, "website_published": False, "sale_ok": False}
    )
    Importer._set_cmos_attribute_value(keeper_tmpl, "Successful")
    keeper_tmpl.write(
        {
            "active": True,
            "website_published": True,
            "sale_ok": True,
        }
    )
    env.cr.commit()

print("AFTER keeper:", snap(KEEPER))
print("AFTER obsolete:", snap(OBSOLETE))
print("DONE")
