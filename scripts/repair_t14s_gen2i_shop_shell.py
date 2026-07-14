# -*- coding: utf-8 -*-
"""T14s Gen 2i shop repair:
  1) Restore clean titles + CPU/RAM/Storage on the two broken CMOSP SKUs
  2) Upsert Touchscreen=Yes + WAN=Enabled on ALL active T14s Gen 2i shop SKUs
  3) Normalize Series sidebar (strip Gen-suffixed Series values -> ThinkPad T14s)

Does NOT rewrite titles for SKUs that already have clean names.
Does NOT call full _sync_template_attributes except for the two broken SKUs
(where CPU/RAM/Storage were wiped).

Default DRY_RUN=True. Set False + workflow confirm_apply=APPLY to write.
"""
import re

DRY_RUN = False  # set False to commit on production

# Broken by earlier apply: bad title + wiped CPU/RAM/Storage.
RESTORE = {
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
Line = env["product.template.attribute.line"].sudo()
Pav = env["product.attribute.value"].sudo()


def current_specs(tmpl):
    out = {}
    for line in tmpl.attribute_line_ids:
        if line.value_ids:
            out[line.attribute_id.name] = line.value_ids[0].name
    return out


def upsert_attr(tmpl, attr_xmlid, value_name):
    attr = env.ref(attr_xmlid)
    val = Pav.search(
        [("attribute_id", "=", attr.id), ("name", "=ilike", value_name)],
        limit=1,
    )
    if not val:
        val = Pav.create({"attribute_id": attr.id, "name": value_name[:128]})
    line = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id.id == attr.id)
    if line:
        if set(line.value_ids.ids) != {val.id}:
            line.write({"value_ids": [(6, 0, [val.id])]})
            return "updated"
        return "unchanged"
    Line.create(
        {
            "product_tmpl_id": tmpl.id,
            "attribute_id": attr.id,
            "value_ids": [(6, 0, [val.id])],
        }
    )
    return "created"


def is_t14s_gen2i(tmpl):
    specs = current_specs(tmpl)
    gen = (specs.get("Generation") or "").lower()
    if "2i" in gen:
        return True
    blob = " ".join(
        x for x in (tmpl.name, tmpl.description_sale, tmpl.default_code) if x
    ).upper()
    return bool(re.search(r"GEN\s*2I", blob)) and (
        "T14S" in blob or (tmpl.default_code or "").upper().startswith(("20WN", "20WNS", "20T"))
    )


def find_gen2i_shop_templates():
    """Active sale_ok shop SKUs for T14s Gen 2i (CMOSP / BTU70 / base active)."""
    out = []
    for tmpl in PT.search(
        [
            ("active", "=", True),
            ("sale_ok", "=", True),
            ("type", "=", "product"),
            "|",
            ("default_code", "=ilike", "20WN%"),
            "|",
            ("default_code", "=ilike", "20WNS%"),
            ("name", "ilike", "T14s Gen 2"),
        ]
    ):
        code = (tmpl.default_code or "").upper()
        if code.endswith("-CMOSFL"):
            continue
        if not is_t14s_gen2i(tmpl):
            continue
        out.append(tmpl)
    return sorted(out, key=lambda t: t.default_code or "")


def find_battery_donor(code):
    base = (code or "").split("-")[0]
    for other in PT.search([("default_code", "=ilike", "%s-%%" % base)]):
        if (other.default_code or "") == code:
            continue
        batt = current_specs(other).get("Battery")
        if batt:
            return other.default_code, batt
    return None, None


# ---------------------------------------------------------------------------
print("=" * 72)
print("T14s Gen 2i: restore titles + touch/wan all + Series normalize")
print("  DRY_RUN:", DRY_RUN)
print("=" * 72)

shop = find_gen2i_shop_templates()
print("\n[A] Gen 2i shop SKUs found: %d" % len(shop))
for t in shop:
    sp = current_specs(t)
    print(
        "  %s | name=%r | touch=%r wan=%r cpu=%r series=%r gen=%r on=%s"
        % (
            t.default_code,
            t.name,
            sp.get("Touchscreen"),
            sp.get("WAN"),
            sp.get("CPU"),
            sp.get("Series"),
            sp.get("Generation"),
            t.qty_available,
        )
    )

# --- Series pollution report (before)
series_attr = env.ref("quote_manage_ui.attr_series")
print("\n[B] Published products with Gen-suffixed Series (pollution):")
polluted = []
for tmpl in PT.search(
    [("website_published", "=", True), ("active", "=", True), ("sale_ok", "=", True)]
):
    sp = current_specs(tmpl)
    series = sp.get("Series") or ""
    if re.search(r"\bGen\b", series, re.I):
        polluted.append((tmpl.default_code, series, tmpl.name))
        print("  %s | Series=%r | name=%r" % (tmpl.default_code, series, tmpl.name))
if not polluted:
    print("  (none)")

# --- Plan restore + touch/wan
restore_plans = []
for code, cfg in RESTORE.items():
    tmpl = PT.search([("default_code", "=", code)], limit=1)
    if not tmpl:
        print("WARN missing restore SKU:", code)
        continue
    before = current_specs(tmpl)
    brand = before.get("Brand") or "Lenovo"
    specs = Importer._parse_specs(brand, [cfg["spec_title"]])
    specs["touch"] = "Yes"
    specs["wan"] = "Yes"
    donor_code, donor_batt = find_battery_donor(code)
    if donor_batt and not specs.get("battery"):
        specs["battery"] = donor_batt
    need = (
        (tmpl.name or "").strip() != cfg["name"]
        or not before.get("CPU")
        or not before.get("RAM")
        or not before.get("Storage")
        or before.get("Touchscreen") != "Yes"
        or before.get("WAN") != "Enabled"
    )
    restore_plans.append(
        {
            "tmpl": tmpl,
            "code": code,
            "cfg": cfg,
            "brand": brand,
            "specs": specs,
            "before": before,
            "need": need,
            "donor": (donor_code, donor_batt),
        }
    )

touch_plans = []
for tmpl in shop:
    before = current_specs(tmpl)
    need = before.get("Touchscreen") != "Yes" or before.get("WAN") != "Enabled"
    # Still list restore SKUs here; restore path handles full attrs.
    touch_plans.append({"tmpl": tmpl, "before": before, "need": need})

print("\n[C] Restore title/CPU (broken 2): %d need work" % sum(1 for p in restore_plans if p["need"]))
for p in restore_plans:
    print(
        "  %s need=%s name=%r cpu=%r"
        % (p["code"], p["need"], p["tmpl"].name, p["before"].get("CPU"))
    )

print(
    "\n[D] Touch/WAN upsert: %d need work of %d"
    % (sum(1 for p in touch_plans if p["need"]), len(touch_plans))
)

if DRY_RUN:
    print("\nDRY_RUN: would also call repair_shop_sidebar_filters().")
    print("No changes written.")
else:
    # 1) Restore broken two first (full sync for those only)
    for p in restore_plans:
        if not p["need"]:
            continue
        tmpl = p["tmpl"]
        tmpl.write({"name": p["cfg"]["name"]})
        Importer._sync_template_attributes(
            tmpl,
            brand=p["brand"],
            titles=[p["cfg"]["spec_title"]],
            ptype=tmpl.type or "product",
            specs=p["specs"],
        )
        print(
            "  restored %s -> name=%r cpu=%r touch=%r"
            % (
                p["code"],
                tmpl.name,
                current_specs(tmpl).get("CPU"),
                current_specs(tmpl).get("Touchscreen"),
            )
        )

    # 2) Upsert touch/wan on all Gen2i shop (non-destructive)
    n = 0
    for p in touch_plans:
        if not p["need"]:
            continue
        tmpl = p["tmpl"]
        upsert_attr(tmpl, "quote_manage_ui.attr_touchscreen", "Yes")
        upsert_attr(tmpl, "quote_manage_ui.attr_wan", "Enabled")
        n += 1
        print("  touch/wan upsert %s" % tmpl.default_code)
    print("  touched %d SKUs for touch/wan" % n)

    # 3) Normalize Series (Gen out of Series -> ThinkPad T14s; Generation kept)
    fixed_series, fixed_gen = Importer.repair_shop_sidebar_filters()
    print("  repair_shop_sidebar_filters: series=%s gen=%s" % (fixed_series, fixed_gen))

    print("\n[E] After: Gen-suffixed Series on published products:")
    left = 0
    for tmpl in PT.search(
        [("website_published", "=", True), ("active", "=", True), ("sale_ok", "=", True)]
    ):
        series = current_specs(tmpl).get("Series") or ""
        if re.search(r"\bGen\b", series, re.I):
            left += 1
            print("  STILL %s | Series=%r" % (tmpl.default_code, series))
    if not left:
        print("  (none — Series filter should only show ThinkPad T14s etc.)")

    env.cr.commit()
    print("\nCommitted.")

print("\nDone.")
