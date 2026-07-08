# -*- coding: utf-8 -*-
"""Safely delete obsolete refurb SKUs after archive + DB backup.

Scope (same as archive_obsolete_skus_shell.py):
  * serial-tracked laptop/desktop refurb products classified as obsolete
  * must already be inactive, on_hand=0, not sale_ok

Never touches services, consumables, or *-CMOSP / *-CMOSFL keepers.

Skips unlink when any reference exists (sale lines, stock moves, purchases, etc.).

Default DRY_RUN=True. Set False to apply.

Production:
  Get-Content scripts/delete_obsolete_skus_shell.py -Raw |
    ssh -i $env:USERPROFILE\.ssh\id_ed25519_do root@134.199.145.67 `
    "docker compose -f /root/reware/docker-compose.yml run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init"
"""
import re
from collections import defaultdict

DRY_RUN = True  # set False to apply on production

BATTERY_SUFFIXES = ("-BT70", "-BTU70")
CMOS_SUFFIXES = ("-CMOSP", "-CMOSFL")
INTERNAL_SUFFIXES = BATTERY_SUFFIXES + CMOS_SUFFIXES

PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
SOL = env["sale.order.line"].sudo()
SML = env["stock.move.line"].sudo()
SM = env["stock.move"].sudo()
POL = env["purchase.order.line"].sudo()
AML = env["account.move.line"].sudo()


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


def refurb_serial_domain():
    cat_l = env.ref("quote_manage_ui.public_cat_laptops").id
    cat_d = env.ref("quote_manage_ui.public_cat_desktops").id
    return [
        ("type", "=", "product"),
        ("tracking", "=", "serial"),
        ("public_categ_ids", "in", [cat_l, cat_d]),
    ]


def classify_obsolete():
    products = []
    for tmpl in PT.search(refurb_serial_domain(), order="default_code"):
        code = (tmpl.default_code or "").strip().upper()
        if not code:
            continue
        products.append({**sku_flags(code), "on_hand": float(tmpl.qty_available or 0)})

    by_base = defaultdict(list)
    for p in products:
        by_base[p["base"]].append(p)

    archive, keep_codes = [], set()
    for base, group in sorted(by_base.items()):
        codes = {p["code"] for p in group}

        def add_archive(p, reason):
            archive.append({**p, "reason": reason})

        for p in group:
            if p["has_battery"] and not p["has_cmosp"] and not p["has_cmosfl"]:
                bt = "BT70" if p["has_bt70"] else "BTU70"
                succ = f"{base}-{bt}-CMOSP"
                if succ in codes:
                    add_archive(p, f"Superseded by {succ}")
                else:
                    add_archive(p, "Battery-tier without CMOSP")

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
                    add_archive(p, "Legacy config SKU")

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
                keep_codes.add(p["code"])

    seen = set()
    out = []
    for p in sorted(archive, key=lambda x: x["code"]):
        if p["code"] in seen:
            continue
        seen.add(p["code"])
        out.append(p)
    return out


def templates_for_code(code):
    return PT.search([("default_code", "=ilike", (code or "").strip())])


def unlink_blockers(tmpl):
    variants = tmpl.product_variant_ids
    v_ids = variants.ids
    blockers = []

    if tmpl.active:
        blockers.append("active=True")
    oh = float(tmpl.qty_available or 0)
    if oh != 0:
        blockers.append(f"on_hand={oh}")
    if tmpl.sale_ok:
        blockers.append("sale_ok=True")

    n = SOL.search_count([("product_id", "in", v_ids)])
    if n:
        blockers.append(f"sale_order_lines={n}")

    n = SML.search_count([("product_id", "in", v_ids)])
    if n:
        blockers.append(f"stock_move_lines={n}")

    n = SM.search_count([("product_id", "in", v_ids)])
    if n:
        blockers.append(f"stock_moves={n}")

    n = POL.search_count([("product_id", "in", v_ids)])
    if n:
        blockers.append(f"purchase_order_lines={n}")

    n = AML.search_count([("product_id", "in", v_ids)])
    if n:
        blockers.append(f"account_move_lines={n}")

    n = Quant.search_count([("product_id", "in", v_ids), ("quantity", "!=", 0)])
    if n:
        blockers.append(f"nonzero_quants={n}")

    return blockers


obsolete = classify_obsolete()

print("=" * 72)
print("SAFE DELETE OBSOLETE REFURB SKUs")
print("DRY_RUN:", DRY_RUN)
print("=" * 72)
print("Obsolete candidates:", len(obsolete))
print()

deleted, skipped = [], []

for item in obsolete:
    code = item["code"]
    tmpls = templates_for_code(code)
    if not tmpls:
        skipped.append((code, ["template_not_found"]))
        continue

    for tmpl in tmpls:
        label = f"{code} [tmpl={tmpl.id}]"
        blockers = unlink_blockers(tmpl)
        if blockers:
            skipped.append((label, blockers))
            print(f"SKIP {label}")
            print(f"  reason: {item['reason']}")
            print(f"  blockers: {', '.join(blockers)}")
            print()
            continue

        print(f"{'[DRY] DELETE' if DRY_RUN else 'DELETE'} {label}")
        print(f"  reason: {item['reason']}")
        if not DRY_RUN:
            try:
                with env.cr.savepoint():
                    tmpl.unlink()
                deleted.append(label)
            except Exception as e:
                skipped.append((label, [f"unlink_error: {e}"]))
                print(f"  FAILED: {e}")
        else:
            deleted.append(label)
        print()

print("=" * 72)
print("Summary: would_delete/delete=", len(deleted), "| skipped=", len(skipped))
if deleted:
    print("\nDeleted / would delete:")
    for x in deleted:
        print(" ", x)
if skipped:
    print("\nSkipped (stay archived):")
    for code, blockers in skipped:
        print(f"  {code}: {', '.join(blockers)}")

if not DRY_RUN:
    env.cr.commit()
    print("\nCommitted.")
else:
    print("\nPreview only. Set DRY_RUN = False and re-run to apply.")
    env.cr.rollback()

print("Done.")
