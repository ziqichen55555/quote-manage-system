# -*- coding: utf-8 -*-
"""Zero warehouse stock on inactive refurb serial SKUs (phantom / legacy catalog).

Skips active products and *-CMOSP / *-CMOSFL keepers.
Does not touch customer-location quants (delivered units).

Default DRY_RUN=True. Set False to apply.

Production:
  Get-Content scripts/clear_phantom_obsolete_stock_shell.py -Raw |
    ssh -i $env:USERPROFILE\.ssh\id_ed25519_do root@134.199.145.67 `
    "docker compose -f /root/reware/docker-compose.yml run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init"
"""
DRY_RUN = True

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
WH = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)

cat_l = env.ref("quote_manage_ui.public_cat_laptops").id
cat_d = env.ref("quote_manage_ui.public_cat_desktops").id

INACTIVE_REFURB_DOM = [
    ("type", "=", "product"),
    ("tracking", "=", "serial"),
    ("public_categ_ids", "in", [cat_l, cat_d]),
    ("active", "=", False),
]


def wh_stock_rows(tmpl):
    rows = []
    if not WH:
        return rows
    for variant in tmpl.product_variant_ids:
        for quant in Quant.search(
            [
                ("product_id", "=", variant.id),
                ("location_id", "child_of", WH.lot_stock_id.id),
                ("quantity", ">", 0),
            ]
        ):
            rows.append(
                {
                    "serial": quant.lot_id.name if quant.lot_id else "(no-lot)",
                    "qty": float(quant.quantity),
                }
            )
    return rows


def zero_template_wh_stock(tmpl):
    zeroed = []
    if not WH:
        return zeroed
    for variant in tmpl.product_variant_ids:
        for quant in Quant.search(
            [
                ("product_id", "=", variant.id),
                ("location_id", "child_of", WH.lot_stock_id.id),
                ("quantity", ">", 0),
            ]
        ):
            label = quant.lot_id.name if quant.lot_id else "(no-lot)"
            zeroed.append(label)
            if not DRY_RUN:
                quant.with_context(inventory_mode=True).write(
                    {"inventory_quantity_auto_apply": 0.0}
                )
        for quant in Quant.search(
            [
                ("product_id", "=", variant.id),
                ("location_id", "child_of", WH.lot_stock_id.id),
                ("lot_id", "=", False),
                ("quantity", ">", 0),
            ]
        ):
            zeroed.append("(no-lot)")
            if not DRY_RUN:
                quant.with_context(inventory_mode=True).write(
                    {"inventory_quantity_auto_apply": 0.0}
                )
    if not DRY_RUN:
        tmpl.invalidate_recordset()
        tmpl.write({"website_published": False, "sale_ok": False})
    return zeroed


targets = []
for tmpl in PT.search(INACTIVE_REFURB_DOM, order="default_code, id"):
    code = (tmpl.default_code or "").strip().upper()
    if code.endswith("-CMOSP") or code.endswith("-CMOSFL"):
        continue
    oh = float(tmpl.qty_available or 0)
    wh_rows = wh_stock_rows(tmpl)
    wh_qty = sum(r["qty"] for r in wh_rows)
    if oh != 0 or wh_qty > 0:
        targets.append((tmpl, code or "(no code)", oh, wh_qty, wh_rows))

print("=" * 72)
print("CLEAR PHANTOM STOCK — INACTIVE REFURB SKUs")
print("DRY_RUN:", DRY_RUN)
print("=" * 72)
print("Targets:", len(targets))
print()

cleared = []
for tmpl, code, oh_before, wh_qty, wh_rows in targets:
    print(f"{code} [tmpl={tmpl.id}] on_hand_before={oh_before} wh_qty={wh_qty}")
    if wh_rows[:6]:
        print("  sample:", ", ".join(f"{r['serial']}:{r['qty']}" for r in wh_rows[:6]))
    if len(wh_rows) > 6:
        print(f"  ... +{len(wh_rows) - 6} more in WH")

    if code != "(no code)":
        if not DRY_RUN:
            Importer._zero_all_serial_stock(code)
            tmpl.invalidate_recordset()
            tmpl.write({"website_published": False, "sale_ok": False, "active": False})
        else:
            print("  [DRY] _zero_all_serial_stock")
    else:
        zeroed = zero_template_wh_stock(tmpl)
        print(f"  {'[DRY] would zero' if DRY_RUN else 'zeroed'}: {len(zeroed)} rows")

    tmpl.invalidate_recordset()
    oh_after = float(tmpl.qty_available or 0)
    print(f"  on_hand_after={oh_after}")
    cleared.append((code, tmpl.id, oh_before, oh_after))
    print()

if not DRY_RUN:
    env.cr.commit()
    print("Committed.")
else:
    print("Preview only. Set DRY_RUN = False and re-run to apply.")
    env.cr.rollback()

print("=" * 72)
print("Summary:", len(cleared), "templates processed")
for code, tid, before, after in cleared:
    print(f"  {code} tmpl={tid}: {before} -> {after}")
print("Done.")
