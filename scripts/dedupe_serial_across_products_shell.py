# -*- coding: utf-8 -*-
"""Find serial numbers stocked on more than one refurb product; keep one, zero + archive the rest.

Use when old imports created duplicates like:
  60T1QQ2 on [DELL LATITUDE 5590-16G-256G-N] AND [LATITUDE 5590-16G-256G-N]
  64M3Q72 on three different Latitude E7470 product names

Default DRY_RUN=True. Set False to apply.

Production (DigitalOcean droplet, Docker in /root/reware):
  Get-Content scripts/dedupe_serial_across_products_shell.py -Raw |
    ssh -i $env:USERPROFILE\.ssh\id_ed25519_do root@134.199.145.67 `
    "docker compose -f /root/reware/docker-compose.yml run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init"

Optional: copy MERGED import-all CSV to server and set MERGE_CSV so keeper SKU follows the merge file.
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict

DRY_RUN = True

# On server after scp, e.g. /root/reware/imports/MERGED-import-all.csv — leave "" to use heuristics only.
MERGE_CSV = "/root/reware/imports/MERGED-import-all-2026-07-08.csv"

Importer = env["product.csv.importer"].sudo()
PT = env["product.template"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo()
WH = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)

LEGACY_BRACKET = re.compile(r"^\[[^\]]+\]", re.I)
AUTO_SN = re.compile(r"^S/N-", re.I)


def load_merge_serial_to_sku(path: str) -> dict[str, str]:
    if not (path or "").strip():
        return {}
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            text = f.read()
    except OSError as exc:
        print(f"MERGE_CSV read failed: {exc}")
        return {}
    reader = csv.DictReader(io.StringIO(text))
    out: dict[str, str] = {}
    for row in reader:
        sn = (row.get("Serial") or "").strip().upper()
        sku = (row.get("Shop SKU") or row.get("MTM") or "").strip().upper()
        if sn and sku:
            out[sn] = Importer._canonical_sku_code(sku).upper()
    return out


def sku_score(tmpl, serial: str, merge_map: dict[str, str]) -> int:
    code = (tmpl.default_code or "").strip().upper()
    canon = Importer._canonical_sku_code(tmpl.default_code or "").upper()
    score = 0
    want = merge_map.get(serial.upper(), "")
    if want and canon == want:
        score += 10_000
    if code.endswith("-CMOSP"):
        score += 500
    elif code.endswith("-CMOSFL"):
        score += 200
    if canon == code and not code.startswith(("RW-", "IMPORT-")):
        score += 300
    if not code.startswith("RW-"):
        score += 100
    if not code.startswith("IMPORT-"):
        score += 100
    if tmpl.website_published:
        score += 50
    if tmpl.active:
        score += 25
    # Prefer real MTM/SKU codes over legacy bracket titles in product name.
    name = (tmpl.name or "")
    if LEGACY_BRACKET.match(name):
        score -= 80
    if re.search(r"-\d+G-\d+G-[TN]$", code):
        score -= 40  # old config SKU
    score += int(tmpl.write_date.timestamp()) if tmpl.write_date else 0
    return score


def collect_serial_hits():
    """serial -> [{tmpl, sku, qty, lots}]"""
    hits: dict[str, list] = defaultdict(list)
    domain = Importer._refurb_serial_template_domain(active_only=False)
    for tmpl in PT.search(domain):
        code = (tmpl.default_code or "").strip()
        if not code or not Importer._stock_update_allowed(tmpl):
            continue
        for variant in tmpl.product_variant_ids:
            quants = Quant.search(
                [
                    ("product_id", "=", variant.id),
                    ("location_id.usage", "=", "internal"),
                    ("quantity", ">", 0),
                    ("lot_id", "!=", False),
                ]
            )
            by_lot: dict[int, float] = defaultdict(float)
            for q in quants:
                by_lot[q.lot_id.id] += float(q.quantity)
            for lot_id, qty in by_lot.items():
                lot = Lot.browse(lot_id)
                sn = (lot.name or "").strip().upper()
                if not sn or AUTO_SN.match(sn):
                    continue
                hits[sn].append(
                    {
                        "tmpl": tmpl,
                        "sku": code,
                        "qty": qty,
                        "lot": lot,
                        "variant": variant,
                    }
                )
    return hits


merge_map = load_merge_serial_to_sku(MERGE_CSV)
hits = collect_serial_hits()
dupes = {sn: rows for sn, rows in hits.items() if len({r["tmpl"].id for r in rows}) > 1}

print(f"DRY_RUN={DRY_RUN}")
print(f"Merge serial hints loaded: {len(merge_map)}")
print(f"Duplicate serials across products: {len(dupes)}\n")

archived = zeroed = skipped_delivered = 0

for sn in sorted(dupes):
    rows = dupes[sn]
    by_tmpl: dict[int, dict] = {}
    for r in rows:
        tid = r["tmpl"].id
        if tid not in by_tmpl:
            by_tmpl[tid] = {**r, "qty": 0.0}
        by_tmpl[tid]["qty"] += r["qty"]
    candidates = list(by_tmpl.values())
    candidates.sort(key=lambda r: sku_score(r["tmpl"], sn, merge_map), reverse=True)
    keeper = candidates[0]
    losers = candidates[1:]

    print(f"=== {sn} ({len(candidates)} products) ===")
    print(f"  KEEP  [{keeper['sku']}] {keeper['tmpl'].name[:70]!r} qty={keeper['qty']}")
    for r in losers:
        print(f"  DROP  [{r['sku']}] {r['tmpl'].name[:70]!r} qty={r['qty']}")

    for r in losers:
        tmpl = r["tmpl"]
        sku = Importer._canonical_sku_code(tmpl.default_code or "")
        if Importer._serial_is_delivered(sn, r["variant"].id):
            print(f"  skip delivered on {sku}")
            skipped_delivered += 1
            continue
        if DRY_RUN:
            continue
        if float(tmpl.qty_available or 0) > 0:
            Importer._zero_all_serial_stock(sku)
            zeroed += 1
        tmpl.write({"active": False, "website_published": False, "sale_ok": False})
        archived += 1

if not DRY_RUN:
    env.cr.commit()

print("\n=== SUMMARY ===")
print(f"duplicate_serials: {len(dupes)}")
print(f"templates_archived: {archived}")
print(f"skus_zeroed: {zeroed}")
print(f"skipped_delivered: {skipped_delivered}")
if DRY_RUN:
    print("DRY_RUN only — set DRY_RUN=False to apply.")
