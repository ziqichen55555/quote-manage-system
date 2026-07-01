#!/usr/bin/env python3
"""Summarize live prod export for user-facing product list review."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "backups/prod_export_now.txt"


def load_snapshot(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\{[\s\S]*\}\s*$", raw)
    if not m:
        raise SystemExit(f"No JSON in {path}")
    return json.loads(m.group(0))


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    data = load_snapshot(path)
    prods = data["products"]
    print(f"Exported: {data.get('exported_at')}")
    print(f"sale_ok products (backend list): {len(prods)}")
    print()

    cats = Counter((p.get("public_cats") or "Other") for p in prods)
    print("By category:")
    for k, v in cats.most_common():
        print(f"  {k}: {v}")
    print()

    cmosp = cmosfl = bt_only = legacy_laptop = []
    for p in prods:
        c = (p.get("code") or "").strip()
        pc = p.get("public_cats") or ""
        if c.endswith("-CMOSP"):
            cmosp.append(p)
        elif c.endswith("-CMOSFL"):
            cmosfl.append(p)
        elif ("-BT70" in c or "-BTU70" in c) and not c.endswith("-CMOSP"):
            bt_only.append(p)
        elif p.get("tracking") == "serial" and (
            "Laptop" in pc or "Desktop" in pc or "Mini" in pc
        ):
            if not c.endswith("-CMOSP"):
                legacy_laptop.append(p)

    print(f"Merge laptops *-CMOSP: {len(cmosp)}")
    print(f"Still *-CMOSFL (should archive): {len(cmosfl)}")
    print(f"Battery-tier without CMOSP: {len(bt_only)}")
    print(f"Other legacy laptop/desktop serial: {len(legacy_laptop)}")
    print(f"Accessories + network + monitors + other: {len(prods) - len(cmosp) - len(cmosfl) - len(bt_only) - len(legacy_laptop)}")
    print()

    if cmosfl or bt_only:
        print("=== Should NOT appear (cleanup remaining) ===")
        for p in cmosfl + bt_only:
            print(f"  {p.get('code')}  on_hand={p.get('on_hand')}  pub={p.get('published')}")
        print()

    if legacy_laptop:
        print("=== Legacy Dell/HP etc. (not merge flow — separate cleanup) ===")
        for p in sorted(legacy_laptop, key=lambda x: -(x.get("on_hand") or 0))[:20]:
            print(f"  {p.get('code'):<40} on_hand={p.get('on_hand')}")
        if len(legacy_laptop) > 20:
            print(f"  ... +{len(legacy_laptop) - 20} more")
        print()

    print("=== Merge laptops *-CMOSP (correct pattern) ===")
    for p in sorted(cmosp, key=lambda x: -(float(x.get("on_hand") or 0))):
        c = p.get("code", "")
        sn = len(p.get("serials") or [])
        oh = p.get("on_hand")
        flag = " *** qty!=serials" if sn and float(oh or 0) != sn else ""
        print(f"  {c:<45} on_hand={oh}  SN={sn}{flag}")


if __name__ == "__main__":
    main()
