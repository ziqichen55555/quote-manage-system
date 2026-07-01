#!/usr/bin/env python3
"""Audit live prod snapshot: archive vs keep vs review."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BATTERY_SUFFIXES = ("-BT70", "-BTU70")
CMOS_SUFFIXES = ("-CMOSP", "-CMOSFL")
INTERNAL = BATTERY_SUFFIXES + CMOS_SUFFIXES

DEFAULT = Path(__file__).resolve().parents[1] / "backups/prod_product_snapshot_live_20260701.json"


def strip_sfx(code: str) -> str:
    code = (code or "").strip().upper()
    changed = True
    while changed:
        changed = False
        for sfx in INTERNAL:
            if code.endswith(sfx):
                code = code[: -len(sfx)]
                changed = True
    return code


def flags(code: str) -> dict:
    code = (code or "").strip().upper()
    return {
        "code": code,
        "base": strip_sfx(code),
        "has_battery": any(code.endswith(s) for s in BATTERY_SUFFIXES),
        "has_bt70": code.endswith("-BT70") and not code.endswith("-BTU70"),
        "has_btu70": code.endswith("-BTU70"),
        "has_cmosp": code.endswith("-CMOSP"),
        "has_cmosfl": code.endswith("-CMOSFL"),
        "is_rw": code.startswith("RW-"),
        "is_import": code.startswith("IMPORT-"),
        "is_config": bool(re.search(r"-\d+G-\d+G-[TN]$", code)),
    }


def is_refurb_serial(p: dict) -> bool:
    cats = (p.get("public_cats") or "").lower()
    return (
        p.get("tracking") == "serial"
        and p.get("type") == "product"
        and any(k in cats for k in ("laptop", "desktop", "mini"))
    )


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    data = json.loads(path.read_text(encoding="utf-8"))

    items = []
    for p in data["products"]:
        if not is_refurb_serial(p):
            continue
        serials = [
            s["serial"] if isinstance(s, dict) else str(s)
            for s in (p.get("serials") or [])
        ]
        items.append({
            **flags(p.get("code", "")),
            "name": p.get("name", ""),
            "on_hand": float(p.get("on_hand") or 0),
            "published": p.get("published"),
            "active": p.get("active"),
            "serials": serials,
            "id": p.get("id"),
        })

    by_base: dict[str, list] = defaultdict(list)
    for it in items:
        by_base[it["base"]].append(it)

    archive: list[tuple[dict, str]] = []
    keep: list[tuple[dict, str]] = []
    review: list[tuple[dict, str]] = []

    for base, group in sorted(by_base.items()):
        codes = {g["code"] for g in group}

        for p in group:
            if p["has_cmosfl"]:
                archive.append((p, "CMOSFL — zero/move SN, not shop stock"))

        for p in group:
            if p["has_battery"] and not p["has_cmosp"] and not p["has_cmosfl"]:
                bt = "BT70" if p["has_bt70"] else "BTU70"
                succ = f"{base}-{bt}-CMOSP"
                if succ in codes:
                    archive.append((p, f"Superseded by {succ}"))
                else:
                    review.append((p, "Battery-tier without CMOSP successor"))

        for p in group:
            if (
                not p["has_battery"]
                and not p["has_cmosp"]
                and not p["has_cmosfl"]
                and not p["is_config"]
            ):
                if any(x["has_cmosp"] or x["has_battery"] for x in group):
                    archive.append((p, "Base MTM — stock should be on tier/CMOSP SKUs"))

        for p in group:
            if p["is_config"] and not p["has_cmosp"]:
                if any(x["has_cmosp"] for x in group):
                    archive.append((p, "Legacy config SKU (-8G-256G-T etc.)"))

        for p in group:
            if p["is_rw"]:
                plain = p["code"][3:]
                if plain in codes or any(c.startswith(plain) for c in codes):
                    archive.append((p, "RW- duplicate of real MTM SKU"))

        for p in group:
            if p["is_import"]:
                archive.append((p, "IMPORT- synthetic SKU"))

        for p in group:
            if p["has_cmosp"]:
                keep.append((p, "KEEP — canonical shop SKU"))

    seen: set[str] = set()
    arch_u: list[tuple[dict, str]] = []
    for p, r in archive:
        if p["code"] in seen:
            continue
        seen.add(p["code"])
        arch_u.append((p, r))
    archive = sorted(arch_u, key=lambda x: (-x[0]["on_hand"], x[0]["code"]))
    keep_map = {p["code"]: (p, r) for p, r in keep}
    keep = sorted(keep_map.values(), key=lambda x: x[0]["code"])

    print(f"LIVE PROD snapshot: {path.name}")
    print(f"Exported: {data.get('exported_at')}")
    print(f"Serial refurb laptop/desktop SKUs: {len(items)}")
    print(f"ARCHIVE: {len(archive)} | KEEP: {len(keep)} | REVIEW: {len(review)}")
    print()

    print("=== KEEP (canonical *-CMOSP) ===")
    for p, _r in keep:
        sn = ",".join(p["serials"][:4])
        print(f"  {p['code']:<42} qty={p['on_hand']:<4} SN={sn}")
    print()

    print("=== ARCHIVE (has stock — action needed) ===")
    for p, r in archive:
        if p["on_hand"] <= 0:
            continue
        sn = ",".join(p["serials"][:4])
        print(f"  {p['code']:<42} qty={p['on_hand']:<4} pub={p['published']}  {r}")
        if sn:
            print(f"    SN: {sn}")
    print()

    print("=== ARCHIVE (zero stock — safe to deactivate) ===")
    for p, r in archive:
        if p["on_hand"] > 0:
            continue
        print(f"  {p['code']:<42}  {r}")
    print()

    if review:
        print("=== REVIEW ===")
        for p, r in review:
            print(f"  {p['code']:<42} qty={p['on_hand']}  {r}")
        print()

    print("=== Example: 20T1S6C300 family ===")
    for it in sorted(items, key=lambda x: x["code"]):
        if "20T1S6C300" in it["code"]:
            action = "KEEP"
            for p, reason in archive:
                if p["code"] == it["code"]:
                    action = f"ARCHIVE ({reason})"
                    break
            for p, _ in keep:
                if p["code"] == it["code"]:
                    action = "KEEP"
            print(
                f"  {it['code']:<42} qty={it['on_hand']} pub={it['published']} "
                f"SN={it['serials']} -> {action}"
            )


if __name__ == "__main__":
    main()
