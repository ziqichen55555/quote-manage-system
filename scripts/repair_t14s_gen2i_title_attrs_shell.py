# -*- coding: utf-8 -*-
"""Repair T14s Gen 2i shop SKUs after bad touch/WAN apply.

Mistake to fix:
  * Product name was wrongly changed to include "TOUCHSCREEN, WAN ENABLED"
  * Full attribute re-sync wiped CPU / RAM / Storage (and related filter attrs)

Correct shop pattern (see T14s Gen 1 cards):
  * Title stays: ThinkPad T14s Gen 2i
  * Specs live in attributes: Touchscreen=Yes, WAN=Enabled (+ CPU/RAM/Storage/…)

Targets:
  * 20WN0025AU-BT70-CMOSP
  * 20WNA07YAU-BT70-CMOSP

Default DRY_RUN=True. Set False + workflow confirm_apply=APPLY to write.
"""
DRY_RUN = True  # set False to commit on production

# Shop display name must stay clean. Specs for attribute sync only (not written as name).
REPAIR = {
    "20WN0025AU-BT70-CMOSP": {
        "name": "ThinkPad T14s Gen 2i",
        "spec_title": (
            "ThinkPad T14s Gen 2i, i5-1145G7, 16GB RAM, 256GB SSD, "
            "TOUCHSCREEN, WAN ENABLED"
        ),
    },
    "20WNA07YAU-BT70-CMOSP": {
        "name": "ThinkPad T14s Gen 2i",
        "spec_title": (
            "ThinkPad T14s Gen 2i, i5-1135G7, 16GB RAM, 256GB SSD, "
            "TOUCHSCREEN, WAN ENABLED"
        ),
    },
}

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)


def current_specs(tmpl):
    out = {}
    for line in tmpl.attribute_line_ids:
        if line.value_ids:
            out[line.attribute_id.name] = line.value_ids[0].name
    return out


def find_battery_donor(code):
    """Prefer another active *-CMOSP of same MTM that still has Battery."""
    base = code.split("-")[0]
    for other in PT.search(
        [
            ("default_code", "=ilike", "%s-%%" % base),
            ("active", "=", True),
        ]
    ):
        if (other.default_code or "") == code:
            continue
        specs = current_specs(other)
        if specs.get("Battery"):
            return other.default_code, specs["Battery"]
    return None, None


print("=" * 72)
print("Repair T14s Gen 2i titles + restore attrs (keep touch/wan)")
print("  DRY_RUN:", DRY_RUN)
print("=" * 72)

plans = []
for code, cfg in REPAIR.items():
    tmpl = PT.search([("default_code", "=", code)], limit=1)
    if not tmpl:
        raise SystemExit("Missing SKU: %s" % code)
    before = current_specs(tmpl)
    brand = before.get("Brand") or "Lenovo"
    specs = Importer._parse_specs(brand, [cfg["spec_title"]])
    specs["touch"] = "Yes"
    specs["wan"] = "Yes"
    donor_code, donor_batt = find_battery_donor(code)
    if donor_batt and not specs.get("battery"):
        specs["battery"] = donor_batt
    name_ok = (tmpl.name or "").strip() == cfg["name"]
    attrs_ok = (
        before.get("Touchscreen") == "Yes"
        and before.get("WAN") == "Enabled"
        and before.get("CPU")
        and before.get("RAM")
        and before.get("Storage")
        and name_ok
    )
    plans.append(
        {
            "tmpl": tmpl,
            "code": code,
            "cfg": cfg,
            "before": before,
            "brand": brand,
            "specs": specs,
            "donor": (donor_code, donor_batt),
            "changed": not attrs_ok or not name_ok,
        }
    )

to_apply = [p for p in plans if p["changed"]]
print("\nFound %d, need repair %d, already OK %d" % (
    len(plans), len(to_apply), len(plans) - len(to_apply)
))

for p in plans:
    tmpl = p["tmpl"]
    print("\n--- id=%s code=%r on_hand=%s" % (tmpl.id, p["code"], tmpl.qty_available))
    print("  name now: %r" % (tmpl.name,))
    print("  attrs now: cpu=%r ram=%r storage=%r touch=%r wan=%r battery=%r" % (
        p["before"].get("CPU"),
        p["before"].get("RAM"),
        p["before"].get("Storage"),
        p["before"].get("Touchscreen"),
        p["before"].get("WAN"),
        p["before"].get("Battery"),
    ))
    if p["changed"]:
        print("  -> name: %r" % p["cfg"]["name"])
        print("  -> restore CPU/RAM/Storage + Touchscreen=Yes + WAN=Enabled")
        print("  -> parsed specs: %r" % {
            k: p["specs"].get(k)
            for k in ("cpu", "ram", "storage", "touch", "wan", "battery", "generation")
        })
        if p["donor"][1]:
            print("  -> battery donor: %s -> %r" % p["donor"])
    else:
        print("  -> skip (already correct)")

if not to_apply:
    print("\nNothing to do.")
elif DRY_RUN:
    print("\nDRY_RUN: no changes written. Set DRY_RUN=False and re-run to apply.")
else:
    updated = 0
    for p in to_apply:
        tmpl = p["tmpl"]
        tmpl.write({"name": p["cfg"]["name"]})
        Importer._sync_template_attributes(
            tmpl,
            brand=p["brand"],
            titles=[p["cfg"]["spec_title"]],
            ptype=tmpl.type or "product",
            specs=p["specs"],
        )
        updated += 1
        after = current_specs(tmpl)
        print("  fixed %s -> name=%r touch=%r wan=%r cpu=%r" % (
            p["code"],
            tmpl.name,
            after.get("Touchscreen"),
            after.get("WAN"),
            after.get("CPU"),
        ))
    env.cr.commit()
    print("\nCommitted %d repair(s)." % updated)

print("\nDone.")
