# -*- coding: utf-8 -*-
"""Add Touchscreen + WAN filter attributes to ThinkPad T14s Gen 2i shop SKUs.

Targets only the two active CMOSP listings:
  * 20WN0025AU-BT70-CMOSP
  * 20WNA07YAU-BT70-CMOSP

Does not touch base/CMOSFL/duplicate templates, stock, lots, prices, or merge.

Default DRY_RUN=True. Set False to apply on production.

Production (PowerShell):
  Get-Content scripts/add_t14s_gen2i_touch_wan_shell.py -Raw |
    ssh -i $env:USERPROFILE\\.ssh\\id_ed25519_do root@134.199.145.67 `
    "docker compose -f /root/reware/docker-compose.yml run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init"

Local:
  Get-Content scripts/add_t14s_gen2i_touch_wan_shell.py -Raw |
    docker compose run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init
"""
DRY_RUN = False  # set False to commit on production

SHOP_SKUS = (
    "20WN0025AU-BT70-CMOSP",
    "20WNA07YAU-BT70-CMOSP",
)

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)


def brand_from_template(tmpl):
    for line in tmpl.attribute_line_ids:
        if line.attribute_id.name == "Brand" and line.value_ids:
            return line.value_ids[0].name
    return "Lenovo"


def current_specs(tmpl):
    out = {}
    for line in tmpl.attribute_line_ids:
        if line.value_ids:
            out[line.attribute_id.name] = line.value_ids[0].name
    return out


def ensure_touch_wan_name(name):
    name = (name or "").strip()
    up = name.upper()
    parts = []
    if "TOUCH" not in up:
        parts.append("TOUCHSCREEN")
    if "WAN" not in up and " LTE" not in up:
        parts.append("WAN ENABLED")
    if not parts:
        return name
    return name.rstrip(", ") + ", " + ", ".join(parts)


def find_target_templates():
    out = []
    missing = []
    for code in SHOP_SKUS:
        tmpl = PT.search([("default_code", "=", code)], limit=1)
        if not tmpl:
            missing.append(code)
            continue
        out.append(tmpl)
    if missing:
        raise SystemExit("Missing shop SKU(s): %s" % ", ".join(missing))
    return out


def plan_update(tmpl):
    before = current_specs(tmpl)
    new_name = ensure_touch_wan_name(tmpl.name)
    brand = brand_from_template(tmpl)
    titles = [new_name, tmpl.description_sale or ""]
    specs = Importer._parse_specs(brand, titles)
    specs["touch"] = "Yes"
    specs["wan"] = "Yes"
    after = {
        "Touchscreen": "Yes",
        "WAN": "Enabled",
    }
    changed = (
        (tmpl.name or "") != new_name
        or before.get("Touchscreen") != "Yes"
        or before.get("WAN") != "Enabled"
    )
    return {
        "tmpl": tmpl,
        "before": before,
        "after": after,
        "new_name": new_name,
        "brand": brand,
        "titles": titles,
        "specs": specs,
        "changed": changed,
    }


print("=" * 72)
print("Add Touch + WAN to ThinkPad T14s Gen 2i (shop CMOSP only)")
print("  SKUs:", ", ".join(SHOP_SKUS))
print("  DRY_RUN:", DRY_RUN)
print("=" * 72)

targets = find_target_templates()
if not targets:
    raise SystemExit("No matching T14s Gen 2i templates found.")

plans = [plan_update(t) for t in targets]
to_apply = [p for p in plans if p["changed"]]
skipped = [p for p in plans if not p["changed"]]

print("\nFound %d template(s), %d need update, %d already OK" % (
    len(plans), len(to_apply), len(skipped)
))

for p in plans:
    tmpl = p["tmpl"]
    print("\n--- id=%s code=%r active=%s published=%s on_hand=%s" % (
        tmpl.id,
        tmpl.default_code,
        tmpl.active,
        tmpl.website_published,
        tmpl.qty_available,
    ))
    print("  name: %r" % (tmpl.name,))
    print("  before attrs: touch=%r wan=%r" % (
        p["before"].get("Touchscreen"),
        p["before"].get("WAN"),
    ))
    if p["changed"]:
        print("  -> new name: %r" % (p["new_name"],))
        print("  -> after attrs: touch=Yes wan=Enabled")
    else:
        print("  -> skip (already has touch + wan)")

if not to_apply:
    print("\nNothing to do.")
elif DRY_RUN:
    print("\nDRY_RUN: no changes written. Set DRY_RUN=False and re-run to apply.")
else:
    updated = 0
    for p in to_apply:
        tmpl = p["tmpl"]
        tmpl.write({"name": p["new_name"]})
        Importer._sync_template_attributes(
            tmpl,
            brand=p["brand"],
            titles=p["titles"],
            ptype=tmpl.type or "product",
            specs=p["specs"],
        )
        updated += 1
    env.cr.commit()
    print("\nCommitted %d template update(s)." % updated)

print("\nDone.")
