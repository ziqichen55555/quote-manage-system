# -*- coding: utf-8 -*-
"""Compare production catalog export vs reference prices from product_import_ready.csv."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF_CSV = ROOT / "quote-manage-system/custom_addons/quote_manage_ui/data/product_import_ready.csv"
PROD_JSON = ROOT / "backups/prod_catalog_audit.json"


def load_reference_prices():
    ref = {}
    with REF_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("default_code") or "").strip().upper()
            if not code:
                continue
            price = float(row.get("cost_ex") or 0)
            if code not in ref or price > ref[code]["price"]:
                ref[code] = {
                    "price": price,
                    "section": (row.get("section") or "").strip(),
                    "title": (row.get("title_raw") or "")[:80],
                }
    return ref


def canonical(code: str) -> str:
    return re.sub(r"\s+", " ", (code or "").strip().upper())


def main():
    prod_path = Path(sys.argv[1]) if len(sys.argv) > 1 else PROD_JSON
    prod = json.loads(prod_path.read_text(encoding="utf-8"))
    ref = load_reference_prices()

    by_code = {canonical(r["code"]): r for r in prod if r.get("code")}
    issues = {
        "no_price": [],
        "price_mismatch": [],
        "no_image": [],
        "unpublished_with_stock": [],
        "not_in_reference": [],
        "reference_missing_on_prod": [],
    }

    for code, r in sorted(by_code.items()):
        price = r["price"]
        has_img = r["main_image"] or r["extra_images"] > 0
        ref_row = ref.get(code)
        if price <= 0 and r["type"] == "product" and r["on_hand"] > 0:
            issues["no_price"].append(r)
        if not has_img and r["published"] and r["type"] == "product":
            issues["no_image"].append(r)
        if r["on_hand"] > 0 and not r["published"]:
            issues["unpublished_with_stock"].append(r)
        if ref_row:
            if ref_row["price"] > 0 and abs(price - ref_row["price"]) > 0.01:
                issues["price_mismatch"].append(
                    {**r, "ref_price": ref_row["price"], "ref_section": ref_row["section"]}
                )
        elif r["published"] and not code.startswith("RW-"):
            issues["not_in_reference"].append(r)

    for code, ref_row in sorted(ref.items()):
        if code not in by_code:
            issues["reference_missing_on_prod"].append({"code": code, **ref_row})

    print("=== PRODUCTION CATALOG AUDIT ===")
    print(f"Products (sale_ok): {len(prod)}")
    print(f"Reference SKUs: {len(ref)}")
    print()
    for key, items in issues.items():
        print(f"--- {key} ({len(items)}) ---")
        for r in items[:25]:
            if key == "price_mismatch":
                print(
                    f"  {r['code']}: prod ${r['price']:.0f} vs ref ${r['ref_price']:.0f} | {r['name'][:50]}"
                )
            elif key == "reference_missing_on_prod":
                print(f"  {r['code']}: ref ${r['price']:.0f} ({r['section']}) — NOT ON PROD")
            else:
                img = "img" if (r.get("main_image") or r.get("extra_images")) else "NO_IMG"
                print(
                    f"  {r.get('code','?')}: ${r.get('price',0):.0f} on={r.get('on_hand',0)} "
                    f"{img} | {r.get('name','')[:55]}"
                )
        if len(items) > 25:
            print(f"  ... +{len(items) - 25} more")
        print()


if __name__ == "__main__":
    main()
