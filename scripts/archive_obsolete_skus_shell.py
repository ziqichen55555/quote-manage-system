# -*- coding: utf-8 -*-
"""Archive obsolete refurb SKUs (migrate SNs to *-CMOSP, then zero + unpublish).

Safe rules:
  * Superseded SKU + SN already on keeper *-CMOSP -> zero duplicate only
  * Superseded SKU + SN only on obsolete (CMOS pass path) -> move to keeper, then zero
  * CMOSFL bucket -> zero only (not shop stock; manual add later)
  * Delivered SNs are never moved or restocked

Default DRY_RUN=True. Set False to apply.

Production:
  Get-Content scripts/archive_obsolete_skus_shell.py -Raw |
    ssh -i $env:USERPROFILE\.ssh\id_ed25519_do root@134.199.145.67 `
    "docker compose -f /root/reware/docker-compose.yml run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init"
"""
import re
from collections import defaultdict

DRY_RUN = True  # set False to apply on production

BATTERY_SUFFIXES = ("-BT70", "-BTU70")
CMOS_SUFFIXES = ("-CMOSP", "-CMOSFL")
INTERNAL_SUFFIXES = BATTERY_SUFFIXES + CMOS_SUFFIXES

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
WH = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)


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
        "base": strip_suffixes(code),
        "has_battery": any(code.endswith(s) for s in BATTERY_SUFFIXES),
        "has_bt70": code.endswith("-BT70") and not code.endswith("-BTU70"),
        "has_btu70": code.endswith("-BTU70"),
        "has_cmosp": code.endswith("-CMOSP"),
        "has_cmosfl": code.endswith("-CMOSFL"),
        "is_rw": code.startswith("RW-"),
        "is_import": code.startswith("IMPORT-"),
        "is_config": bool(re.search(r"-\d+G-\d+G-[TN]$", code)),
    }


def templates_for_code(code):
    return PT.search([("default_code", "=ilike", (code or "").strip())])


def on_hand_for_template(tmpl):
    return float(tmpl.qty_available or 0)


def lots_with_qty_on_template(tmpl):
    if not WH:
        return []
    out = []
    for variant in tmpl.product_variant_ids:
        for quant in Quant.search(
            [
                ("product_id", "=", variant.id),
                ("location_id", "child_of", WH.lot_stock_id.id),
                ("quantity", ">", 0),
                ("lot_id", "!=", False),
            ]
        ):
            out.append(
                {
                    "serial": quant.lot_id.name.upper(),
                    "lot": quant.lot_id,
                    "variant": variant,
                    "qty": float(quant.quantity),
                }
            )
    return out


def serial_on_keeper(serial, keeper_code):
    if not keeper_code:
        return False
    snap = Importer._serial_stock_snapshot(keeper_code)
    return serial.upper() in set(snap.get("lots_in_stock") or [])


def serial_on_cmosfl_in_family(serial, base, exclude_code):
    for tmpl in PT.search([("default_code", "=ilike", f"{base}%")]):
        code = (tmpl.default_code or "").upper()
        if not code.endswith("-CMOSFL") or code == exclude_code.upper():
            continue
        for row in lots_with_qty_on_template(tmpl):
            if row["serial"] == serial.upper():
                return code
    return ""


def resolve_keeper(code, reason, keep_codes):
    m = re.search(r"Superseded by (\S+)", reason or "")
    if m:
        return m.group(1).upper()
    if "Base MTM" in (reason or ""):
        base = strip_suffixes(code)
        for k in sorted(keep_codes):
            if k.endswith("-CMOSP") and strip_suffixes(k) == base:
                return k
    if "Legacy config" in (reason or ""):
        for k in keep_codes:
            if k.startswith(code) and k.endswith("-CMOSP"):
                return k
    return None


def zero_lot_row(row):
    if Importer._serial_is_delivered(row["serial"], row["variant"].id):
        return "skipped_delivered"
    if not DRY_RUN:
        for quant in Quant.search(
            [
                ("lot_id", "=", row["lot"].id),
                ("product_id", "=", row["variant"].id),
                ("quantity", ">", 0),
            ]
        ):
            quant.with_context(inventory_mode=True).write(
                {"inventory_quantity_auto_apply": 0.0}
            )
    return "zeroed"


def move_serial_to_keeper(row, keeper_code):
    keeper_tmpl, keeper_code = Importer._find_product_by_sku(keeper_code)
    if not keeper_tmpl:
        return "keeper_missing"
    keeper_var = Importer._stock_variant_for_unit(keeper_tmpl, keeper_code)
    if not DRY_RUN:
        Importer._move_serial_lot_to_variant(row["lot"], keeper_var, WH)
    return "moved"


def process_archive_template(tmpl, item, keeper_code, keep_codes):
    code = item["code"]
    is_cmosfl = item.get("has_cmosfl") or code.endswith("-CMOSFL")
    base = item["base"]
    stats = {
        "moved": [],
        "zeroed": [],
        "skipped_delivered": [],
        "skipped_cmosfl_only": [],
    }

    for row in lots_with_qty_on_template(tmpl):
        sn = row["serial"]
        if Importer._serial_is_delivered(sn, row["variant"].id):
            stats["skipped_delivered"].append(sn)
            continue

        if is_cmosfl:
            stats["zeroed"].append(sn)
            zero_lot_row(row)
            continue

        if keeper_code and serial_on_keeper(sn, keeper_code):
            stats["zeroed"].append(sn)
            zero_lot_row(row)
            continue

        fl_sku = serial_on_cmosfl_in_family(sn, base, code)
        if fl_sku:
            stats["skipped_cmosfl_only"].append(f"{sn}@{fl_sku}")
            stats["zeroed"].append(sn)
            zero_lot_row(row)
            continue

        if keeper_code:
            move_serial_to_keeper(row, keeper_code)
            stats["moved"].append(sn)
            if not DRY_RUN:
                row["lot"].invalidate_recordset()
            zero_lot_row(row)
            stats["zeroed"].append(sn)
        else:
            stats["zeroed"].append(sn)
            zero_lot_row(row)

    if WH:
        for variant in tmpl.product_variant_ids:
            for quant in Quant.search(
                [
                    ("product_id", "=", variant.id),
                    ("location_id", "child_of", WH.lot_stock_id.id),
                    ("quantity", ">", 0),
                    ("lot_id", "=", False),
                ]
            ):
                if not DRY_RUN:
                    quant.with_context(inventory_mode=True).write(
                        {"inventory_quantity_auto_apply": 0.0}
                    )

    deactivate = on_hand_for_template(tmpl) == 0
    vals = {"website_published": False, "sale_ok": False}
    if deactivate:
        vals["active"] = False
    if not DRY_RUN:
        tmpl.write(vals)
    tmpl.invalidate_recordset()
    stats["on_hand_after"] = on_hand_for_template(tmpl)
    return stats


def refurb_serial_domain(include_inactive=True):
    cat_l = env.ref("quote_manage_ui.public_cat_laptops").id
    cat_d = env.ref("quote_manage_ui.public_cat_desktops").id
    dom = [
        ("type", "=", "product"),
        ("tracking", "=", "serial"),
        ("public_categ_ids", "in", [cat_l, cat_d]),
    ]
    if not include_inactive:
        dom.append(("active", "=", True))
    return dom


def classify_products():
    domain = refurb_serial_domain(include_inactive=True)
    products = []
    for tmpl in PT.search(domain, order="default_code"):
        code = (tmpl.default_code or "").strip().upper()
        if not code:
            continue
        products.append({**sku_flags(code), "on_hand": on_hand_for_template(tmpl)})

    by_base = defaultdict(list)
    for p in products:
        by_base[p["base"]].append(p)

    archive, keep = [], []
    keep_codes = set()

    for base, group in sorted(by_base.items()):
        codes = {p["code"] for p in group}

        def add_archive(p, reason, priority="high"):
            archive.append({**p, "reason": reason, "priority": priority})

        for p in group:
            if p["has_battery"] and not p["has_cmosp"] and not p["has_cmosfl"]:
                bt = "BT70" if p["has_bt70"] else "BTU70"
                succ = f"{base}-{bt}-CMOSP"
                if succ in codes:
                    add_archive(p, f"Superseded by {succ}")
                else:
                    add_archive(p, "Battery-tier without CMOSP", "medium")

        for p in group:
            if (
                not p["has_battery"]
                and not p["has_cmosp"]
                and not p["has_cmosfl"]
                and not p["is_config"]
            ):
                if any(x["has_cmosp"] or x["has_battery"] for x in group):
                    add_archive(p, "Base MTM superseded by tier/CMOSP SKUs")

        for p in group:
            if p["is_config"] and not p["has_cmosp"]:
                if any(x["has_cmosp"] for x in group):
                    add_archive(p, "Legacy config SKU", "medium")

        for p in group:
            if p["is_rw"]:
                plain = p["code"][3:]
                if plain in codes or any(c.startswith(plain) for c in codes):
                    add_archive(p, "RW- duplicate")

        for p in group:
            if p["is_import"]:
                add_archive(p, "IMPORT- synthetic SKU")

        for p in group:
            if p["has_cmosp"] or p["has_cmosfl"]:
                keep.append(p)
                keep_codes.add(p["code"])

    seen = set()
    arch_u = []
    for p in sorted(archive, key=lambda x: (-x["on_hand"], x["code"])):
        if p["code"] in seen:
            continue
        seen.add(p["code"])
        arch_u.append(p)
    return arch_u, keep, keep_codes


archive_skus, keep_skus, keep_codes = classify_products()

print("=" * 72)
print("ARCHIVE OBSOLETE REFURB SKUs (safe migrate)")
print("DRY_RUN:", DRY_RUN)
print("=" * 72)
print("Keep:", len(keep_skus), "| Archive:", len(archive_skus))
print()

for item in archive_skus:
    code = item["code"]
    keeper = resolve_keeper(code, item["reason"], keep_codes)
    tmpls = templates_for_code(code)
    if not tmpls:
        print(f"SKIP {code}: template not found")
        continue

    oh_before = sum(on_hand_for_template(t) for t in tmpls)
    print(f"{'[DRY] ' if DRY_RUN else ''}{code}")
    print(f"  reason: {item['reason']}")
    if keeper:
        print(f"  keeper: {keeper}")
    print(f"  templates={tmpls.ids} on_hand_before={oh_before}")

    merged = {
        "moved": [],
        "zeroed": [],
        "skipped_delivered": [],
        "skipped_cmosfl_only": [],
    }
    for tmpl in tmpls:
        st = process_archive_template(tmpl, item, keeper, keep_codes)
        for k in merged:
            merged[k].extend(st.get(k) or [])
        oh_after = sum(on_hand_for_template(t) for t in tmpls)

    print(f"  on_hand_after={oh_after}")
    if merged["moved"]:
        print(f"  moved to keeper: {merged['moved'][:8]}{'...' if len(merged['moved'])>8 else ''}")
    if merged["skipped_cmosfl_only"]:
        print(f"  zeroed only (SN on CMOSFL): {merged['skipped_cmosfl_only'][:5]}")
    if merged["zeroed"]:
        print(f"  zeroed duplicates: {len(merged['zeroed'])} lots")
    if merged["skipped_delivered"]:
        print(f"  skipped delivered: {merged['skipped_delivered']}")
    print()

if not DRY_RUN:
    env.cr.commit()
    print("Committed.")
else:
    print("Preview only. Set DRY_RUN = False and re-run to apply.")
    env.cr.rollback()

print("Done.")
