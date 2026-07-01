# -*- coding: utf-8 -*-
"""Audit refurb laptop/desktop SKUs that should be archived (Odoo shell).

Usage:
  Get-Content scripts/audit_obsolete_skus_shell.py |
    docker compose run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init
"""
import re
from collections import defaultdict

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)

BATTERY_SUFFIXES = ("-BT70", "-BTU70")
CMOS_SUFFIXES = ("-CMOSP", "-CMOSFL")
INTERNAL_SUFFIXES = BATTERY_SUFFIXES + CMOS_SUFFIXES


def strip_suffixes(code):
    code = (code or "").strip().upper()
    changed = True
    while changed:
        changed = False
        for sfx in INTERNAL_SUFFIXES:
            if code.endswith(sfx):
                code = code[: -len(sfx)]
                changed = True
    return code


def sku_flags(code):
    code = (code or "").strip().upper()
    return {
        "code": code,
        "has_bt70": code.endswith("-BT70") and not code.endswith("-BTU70"),
        "has_btu70": code.endswith("-BTU70"),
        "has_battery": any(code.endswith(s) for s in BATTERY_SUFFIXES),
        "has_cmosp": code.endswith("-CMOSP"),
        "has_cmosfl": code.endswith("-CMOSFL"),
        "base": strip_suffixes(code),
    }


def snapshot(sku):
    snap = Importer._serial_stock_snapshot(sku)
    tmpl, code = Importer._find_product_by_sku(sku)
    return {
        **snap,
        "name": tmpl.name if tmpl else "",
        "published": bool(tmpl.website_published) if tmpl else False,
        "sale_ok": bool(tmpl.sale_ok) if tmpl else False,
        "active": bool(tmpl.active) if tmpl else False,
        "tmpl_id": tmpl.id if tmpl else None,
    }


domain = Importer._refurb_serial_template_domain()
products = []
for tmpl in PT.search(domain, order="default_code"):
    code = (tmpl.default_code or "").strip().upper()
    if not code:
        continue
    snap = snapshot(code)
    flags = sku_flags(code)
    products.append({**flags, **snap})

by_base = defaultdict(list)
for p in products:
    by_base[p["base"]].append(p)

archive = []
keep = []
review = []

for base, group in sorted(by_base.items()):
    codes = {p["code"] for p in group}
    has_cmosp = [p for p in group if p["has_cmosp"]]
    has_cmosfl = [p for p in group if p["has_cmosfl"]]
    has_battery_only = [
        p for p in group if p["has_battery"] and not p["has_cmosp"] and not p["has_cmosfl"]
    ]
    bare_mtm = [
        p
        for p in group
        if not p["has_battery"] and not p["has_cmosp"] and not p["has_cmosfl"]
    ]
    config_skus = [
        p
        for p in group
        if re.search(r"-\d+G-\d+G-[TN]$", p["code"])
        and not p["has_battery"]
        and not p["has_cmosp"]
        and not p["has_cmosfl"]
    ]

    for p in has_cmosfl:
        archive.append({
            **p,
            "reason": "CMOSFL bucket (no longer bulk-imported; move SN or zero stock)",
            "priority": "high",
        })

    for p in has_battery_only:
        bt = "BT70" if p["has_bt70"] else "BTU70"
        successor = f"{base}-{bt}-CMOSP"
        if successor in codes:
            archive.append({
                **p,
                "reason": f"Legacy battery-tier SKU; superseded by {successor}",
                "priority": "high",
            })
        else:
            review.append({
                **p,
                "reason": "Battery-tier without CMOSP and no -CMOSP successor yet",
                "priority": "medium",
            })

    for p in bare_mtm:
        tiered = [x for x in group if x["has_battery"] or x["has_cmosp"]]
        if tiered:
            archive.append({
                **p,
                "reason": "Base MTM SKU; stock should live on battery/CMOS tier SKUs",
                "priority": "high",
            })
        elif p["on_hand"] > 0:
            review.append({
                **p,
                "reason": "Base MTM only listing with stock (no tier split yet)",
                "priority": "low",
            })

    for p in config_skus:
        tiered = [x for x in group if x["base"] == strip_suffixes(p["code"]) or x["base"] == p["base"]]
        if any(x["has_cmosp"] for x in group if x["base"] == strip_suffixes(p["code"])):
            archive.append({
                **p,
                "reason": "Legacy config SKU; superseded by CMOSP tier listings",
                "priority": "medium",
            })

    for p in has_cmosp:
        keep.append({**p, "reason": "Current shop SKU (battery + CMOS pass)", "priority": "keep"})

archived_codes = {a["code"] for a in archive}
for p in products:
    if p["code"] in archived_codes:
        continue
    if any(k["code"] == p["code"] for k in keep):
        continue
    if any(r["code"] == p["code"] for r in review):
        continue
    if p["on_hand"] > 0 or p["lots_in_stock"]:
        review.append({
            **p,
            "reason": "Active stock on non-standard SKU pattern",
            "priority": "medium",
        })

archive.sort(key=lambda x: (-x["on_hand"], x["code"]))
review.sort(key=lambda x: (-x["on_hand"], x["code"]))

print("=" * 72)
print("REFURB SKU ARCHIVE AUDIT")
print("=" * 72)
print(f"Serial-tracked laptops/desktops: {len(products)}")
print(f"Recommend ARCHIVE: {len(archive)}")
print(f"Keep (CMOSP current): {len(keep)}")
print(f"Review manually: {len(review)}")
print()

print("--- ARCHIVE (high priority) ---")
for p in archive:
    if p["priority"] != "high":
        continue
    lots = ", ".join(p["lots_in_stock"][:5])
    if len(p["lots_in_stock"]) > 5:
        lots += "..."
    print(
        f"  {p['code']:40} on_hand={p['on_hand']:<4} pub={p['published']}  "
        f"SN=[{lots}]"
    )
    print(f"    -> {p['reason']}")
print()

print("--- ARCHIVE (medium priority) ---")
for p in archive:
    if p["priority"] != "medium":
        continue
    print(f"  {p['code']:40} on_hand={p['on_hand']}")
    print(f"    -> {p['reason']}")
print()

print("--- REVIEW ---")
for p in review:
    lots = ", ".join(p["lots_in_stock"][:3])
    print(f"  {p['code']:40} on_hand={p['on_hand']}  {p['reason']}  SN=[{lots}]")
print()

print("--- KEEP sample (first 15 CMOSP) ---")
for p in sorted(keep, key=lambda x: x["code"])[:15]:
    print(f"  {p['code']:40} on_hand={p['on_hand']}")
if len(keep) > 15:
    print(f"  ... and {len(keep) - 15} more CMOSP SKUs")
