#!/usr/bin/env python3
"""List backup products that had images — donors for name/MTM matching."""
import json
from pathlib import Path

SNAP = Path(__file__).resolve().parents[1] / "backups/prod_product_snapshot-20260625-091608.json"


def base_mtm(code: str) -> str:
    code = (code or "").strip()
    for sfx in ("-BT70", "-BTU70"):
        if code.endswith(sfx):
            code = code[: -len(sfx)]
            break
    import re
    m = re.match(r"^(.+)-\d+G-\d+G-[TN]$", code, re.I)
    return m.group(1) if m else code


def main():
    data = json.loads(SNAP.read_text(encoding="utf-8"))
    with_img = [p for p in data["products"] if p.get("main_image")]
    by_name = {}
    by_base = {}
    for p in with_img:
        by_name.setdefault((p.get("name") or "").strip().lower(), []).append(p)
        by_base.setdefault(base_mtm(p.get("code", "")).upper(), []).append(p)
    print(f"Snapshot: {data['exported_at']} — {len(with_img)} products with images")
    print()
    for name, items in sorted(by_name.items()):
        codes = sorted({i.get("code") for i in items if i.get("code")})
        if name and codes:
            print(f"  {name[:50]:50} | {', '.join(codes[:4])}")

if __name__ == "__main__":
    main()
