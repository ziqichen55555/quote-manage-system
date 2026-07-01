#!/usr/bin/env python3
"""Classify refurb SKUs: keep vs archive (works on product snapshot JSON or code list)."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BATTERY_SUFFIXES = ("-BT70", "-BTU70")
CMOS_SUFFIXES = ("-CMOSP", "-CMOSFL")
INTERNAL_SUFFIXES = BATTERY_SUFFIXES + CMOS_SUFFIXES


def strip_suffixes(code: str) -> str:
    code = (code or "").strip().upper()
    changed = True
    while changed:
        changed = False
        for sfx in INTERNAL_SUFFIXES:
            if code.endswith(sfx):
                code = code[: -len(sfx)]
                changed = True
    return code


def flags(code: str) -> dict:
    code = (code or "").strip().upper()
    return {
        "code": code,
        "base": strip_suffixes(code),
        "has_battery": any(code.endswith(s) for s in BATTERY_SUFFIXES),
        "has_bt70": code.endswith("-BT70") and not code.endswith("-BTU70"),
        "has_btu70": code.endswith("-BTU70"),
        "has_cmosp": code.endswith("-CMOSP"),
        "has_cmosfl": code.endswith("-CMOSFL"),
        "is_rw_prefix": code.startswith("RW-"),
        "is_import_prefix": code.startswith("IMPORT-"),
        "is_config": bool(re.search(r"-\d+G-\d+G-[TN]$", code)),
    }


def classify(products: list[dict]) -> tuple[list, list, list]:
    by_base = defaultdict(list)
    all_codes = set()
    for p in products:
        code = (p.get("code") or "").strip().upper()
        if not code:
            continue
        all_codes.add(code)
        by_base[strip_suffixes(code)].append({**p, **flags(code)})

    archive, keep, review = [], [], []

    for base, group in sorted(by_base.items()):
        codes = {p["code"] for p in group}
        cmosp = [p for p in group if p["has_cmosp"]]
        cmosfl = [p for p in group if p["has_cmosfl"]]
        battery_only = [
            p for p in group if p["has_battery"] and not p["has_cmosp"] and not p["has_cmosfl"]
        ]
        bare = [
            p for p in group
            if not p["has_battery"] and not p["has_cmosp"] and not p["has_cmosfl"] and not p["is_config"]
        ]
        config_legacy = [
            p for p in group
            if p["is_config"] and not p["has_battery"] and not p["has_cmosp"] and not p["has_cmosfl"]
        ]
        rw_dupes = [p for p in group if p["is_rw_prefix"]]
        import_skus = [p for p in group if p["is_import_prefix"]]

        for p in cmosfl:
            archive.append({**p, "reason": "CMOSFL bucket — not shop stock; zero or move SN to -CMOSP"})

        for p in battery_only:
            bt = "BT70" if p["has_bt70"] else "BTU70"
            successor = f"{base}-{bt}-CMOSP"
            if successor in codes:
                archive.append({
                    **p,
                    "reason": f"Legacy battery SKU — superseded by {successor}",
                })
            elif any(x["has_cmosp"] for x in group):
                archive.append({
                    **p,
                    "reason": "Battery-tier without CMOSP (obsolete naming)",
                })
            else:
                review.append({**p, "reason": "Battery-tier only; migrate to -CMOSP on next merge import"})

        for p in bare:
            if any(x["has_cmosp"] or x["has_battery"] for x in group):
                archive.append({
                    **p,
                    "reason": "Base MTM — stock should be on -BT70/-BTU70-CMOSP tier SKUs",
                })
            elif p.get("on_hand", 0) > 0:
                review.append({**p, "reason": "Base MTM with stock; awaiting first tiered merge import"})

        for p in config_legacy:
            if cmosp or battery_only:
                archive.append({
                    **p,
                    "reason": "Legacy config SKU (-8G-256G-T) — superseded by tier/CMOSP SKUs",
                })

        for p in rw_dupes:
            plain = p["code"][3:]
            if plain in codes or f"{plain}-CMOSP" in codes or any(c.startswith(plain) for c in codes):
                archive.append({**p, "reason": f"RW- duplicate of {plain}"})

        for p in import_skus:
            archive.append({**p, "reason": "Synthetic IMPORT- SKU — replace with real MTM from merge"})

        for p in cmosp:
            keep.append({**p, "reason": "Current canonical shop SKU"})

    archived_codes = {a["code"] for a in archive}
    kept_codes = {k["code"] for k in keep}
    for p in products:
        code = (p.get("code") or "").strip().upper()
        if not code or code in archived_codes or code in kept_codes:
            continue
        if any(r["code"] == code for r in review):
            continue
        if p.get("on_hand", 0) > 0:
            review.append({**p, "reason": "Non-standard pattern with stock"})

    archive.sort(key=lambda x: (-float(x.get("on_hand") or 0), x["code"]))
    keep.sort(key=lambda x: x["code"])
    review.sort(key=lambda x: (-float(x.get("on_hand") or 0), x["code"]))
    return archive, keep, review


def load_snapshot(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    out = []
    for p in data.get("products", []):
        if p.get("type") != "product":
            continue
        cats = (p.get("public_cats") or "").lower()
        if p.get("tracking") != "serial" and "laptop" not in cats and "desktop" not in cats:
            continue
        out.append({
            "code": p.get("code") or "",
            "name": p.get("name") or "",
            "on_hand": float(p.get("on_hand") or 0),
            "published": bool(p.get("published")),
            "active": bool(p.get("active", True)),
            "serials": p.get("serials") or [],
        })
    return out


def main():
    snap = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"c:\Users\User\quote-management-system\quote-manage-system\backups\prod_product_snapshot-20260625-091608.json"
    )
    products = load_snapshot(snap)
    archive, keep, review = classify(products)

    print(f"Source: {snap.name}")
    print(f"Refurb serial products analyzed: {len(products)}")
    print(f"ARCHIVE: {len(archive)} | KEEP (CMOSP/canonical): {len(keep)} | REVIEW: {len(review)}")
    print()

    print("=== ARCHIVE (has stock — do first) ===")
    for p in archive:
        if p.get("on_hand", 0) <= 0 and p.get("active") is False:
            continue
        sn = ";".join((p.get("serials") or [])[:3])
        print(f"  {p['code']:<42} qty={p.get('on_hand',0):<5} pub={p.get('published')}  {p['reason']}")
        if sn:
            print(f"    SN: {sn}")
    print()

    print("=== ARCHIVE (zero stock / already inactive) ===")
    for p in archive:
        if p.get("on_hand", 0) > 0 or p.get("active") is not False:
            continue
        print(f"  {p['code']:<42}  {p['reason']}")
    print()

    print("=== KEEP (after cleanup, from latest merge rules) ===")
    print("  Expected pattern: *-BT70-CMOSP | *-BTU70-CMOSP | *-CMOSP (desktops)")
    print("  (Prod copy predates CMOSP — run audit_obsolete_skus_shell.py on live DB for current list)")
    print()

    print("=== REVIEW ===")
    for p in review[:25]:
        print(f"  {p['code']:<42} qty={p.get('on_hand',0):<5}  {p['reason']}")
    if len(review) > 25:
        print(f"  ... +{len(review)-25} more")


if __name__ == "__main__":
    main()
