#!/usr/bin/env python3
"""Analyze MERGED import-ready CSV vs Odoo importer rules."""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT = Path(
    r"c:\Users\User\OneDrive - Co-Creative IT\Desktop\re-ware merge"
    r"\MERGED import-ready 2026-06-25.csv"
)


def section(mtm: str, model: str) -> str:
    m = (model or "").lower()
    mtm = (mtm or "").upper()
    if "thinkstation" in m or mtm.startswith(("30", "10")):
        return "Desktops"
    if mtm.startswith("20") or "thinkpad" in m or "latitude" in m:
        return "Laptops"
    return "Other"


def tier_code(row) -> str:
    t = (row.get("Battery tier") or "").strip()
    return "BT70" if t == "70%+" else "BTU70"


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    ok = [
        r
        for r in rows
        if (r.get("Status") or "").strip().upper() == "SUCCESS"
        and (r.get("Serial") or "").strip()
    ]
    failed = [r for r in rows if (r.get("Status") or "").strip().upper() != "SUCCESS"]

    print(f"File: {path.name}")
    print(f"Total rows: {len(rows)}")
    print(f"SUCCESS (will import): {len(ok)}")
    print(f"FAILED (will skip): {len(failed)}")
    print()

    reasons = Counter((r.get("Failure reason") or "").strip() for r in failed)
    print("Failure reasons:", dict(reasons))
    print()

    failed_sec = Counter(section(r.get("MTM", ""), r.get("Model name", "")) for r in failed)
    print("FAILED by section:", dict(failed_sec))
    print()

    short = [r for r in failed if len((r.get("Serial") or "").strip()) <= 5]
    print(f"FAILED short serial (<=5 chars, likely scan typos): {len(short)}")
    for r in short:
        print(f"  {r['Serial']:10} | {r.get('MTM',''):12} | {r.get('Model name','')[:45]}")
    print()

    skus = defaultdict(list)
    for r in ok:
        mtm = (r.get("MTM") or "").strip().upper()
        code = f"{mtm}-{tier_code(r)}" if section(mtm, r.get("Model name", "")) == "Laptops" else mtm
        skus[code].append(r["Serial"].strip().upper())

    print(f"Shop SKUs after import: {len(skus)}")
    print(f"Total stock units: {sum(len(v) for v in skus.values())}")
    print("Largest SKUs:")
    for code, sns in sorted(skus.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  {code}: {len(sns)} units")
    print()

    print("=== All 29 FAILED (portal serial | MTM | reason) ===")
    for r in failed:
        print(
            f"  {(r.get('Serial') or ''):12} | {(r.get('MTM') or ''):12} | "
            f"{(r.get('Failure reason') or '')}"
        )


if __name__ == "__main__":
    main()
