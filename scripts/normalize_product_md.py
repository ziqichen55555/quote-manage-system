#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize repo-root product.md (tab-separated) into product_import_ready.csv.

- Preserves section (Laptops, Docks, …) as column `section`.
- Columns: section, default_code, title_raw, brand, quantity, cost_ex,
          condition_note, unit_identifiers, row_note
- `unit_identifiers`: extra cells after Cost EX joined with `|` (often per-unit tags/serials).
- Networking block (MR18/MR42/MS220-style): different column layout in source;
  normalized to same logical columns (qty / condition / cost).

Run from repo root:
  python3 scripts/normalize_product_md.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "product.md"
OUT = ROOT / "product_import_ready.csv"

SECTION_TITLES = {
    "laptops",
    "docks",
    "desktops",
    "accessories",
    "monitors",
    "networking",
}


def parts(line: str) -> list[str]:
    return line.rstrip("\r\n").split("\t")


def slug_code(title: str, prefix: str = "IMPORT") -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip())[:48].strip("-").upper()
    if not s:
        s = "UNKNOWN"
    return f"{prefix}-{s}"


def looks_like_networking_special(row: list[str]) -> bool:
    if not row or not row[0].strip():
        return False
    p = row[0].strip().upper()
    if p in {"MR18-HW", "MR42-HW"} and len(row) >= 5:
        mid = row[2].strip() if len(row) > 2 else ""
        return mid.isdigit()
    if re.match(r"^MS220-", p) and len(row) >= 4:
        return True
    return False


def parse_networking_special(row: list[str]) -> dict:
    """MR18-HW\\tCisco Meraki MR18 \\t67\\tbracket\\t30 or MS220 row."""
    code = row[0].strip()
    if code.upper().startswith("MS220"):
        title = row[1].strip() if len(row) > 1 else ""
        # New layout: code, title, Brand, Qty, Cost, ...
        # Old layout: code, title, qty, '', cost (qty in col2 as digits only)
        if len(row) > 4 and row[3].strip().isdigit() and not row[2].strip().replace(".", "").isdigit():
            brand = row[2].strip() or "Cisco"
            qty_s = row[3].strip()
            cost_s = row[4].strip()
        else:
            brand = "Cisco"
            qty_s = row[2].strip() if len(row) > 2 else ""
            cost_s = row[4].strip() if len(row) > 4 else row[3].strip() if len(row) > 3 else ""
        qty = int(qty_s) if qty_s.isdigit() else ""
        try:
            cost = float(cost_s) if cost_s else ""
        except ValueError:
            cost = ""
        return {
            "default_code": code,
            "title_raw": title,
            "brand": brand,
            "quantity": qty,
            "cost_ex": cost,
            "condition_note": "",
            "unit_identifiers": "|".join(x.strip() for x in row[5:] if x.strip()),
            "row_note": "networking_ms220_layout",
        }
    # MR18 / MR42
    title = row[1].strip() if len(row) > 1 else ""
    qty_s = row[2].strip() if len(row) > 2 else ""
    cond = row[3].strip() if len(row) > 3 else ""
    cost_s = row[4].strip() if len(row) > 4 else ""
    qty = int(qty_s) if qty_s.isdigit() else qty_s
    try:
        cost = float(cost_s) if cost_s else ""
    except ValueError:
        cost = cost_s
    extras = "|".join(x.strip() for x in row[5:] if x.strip())
    return {
        "default_code": code,
        "title_raw": title,
        "brand": "Cisco",
        "quantity": qty,
        "cost_ex": cost,
        "condition_note": cond,
        "unit_identifiers": extras,
        "row_note": "networking_meraki_layout",
    }


def is_section_row(parts: list[str]) -> bool:
    if len(parts) < 2:
        return False
    a, b = parts[0].strip(), parts[1].strip()
    return a == "" and b.lower() in SECTION_TITLES


def parse_standard_row(
    row: list[str], section: str
) -> dict | None:
    # Minimum: title in col1 or product in col0
    p0 = row[0].strip() if row else ""
    p1 = row[1].strip() if len(row) > 1 else ""
    if not p0 and not p1:
        return None
    brand = row[2].strip() if len(row) > 2 else ""
    qty_s = row[3].strip() if len(row) > 3 else ""
    cost_s = row[4].strip() if len(row) > 4 else ""
    extras = [x.strip() for x in row[5:] if x.strip()]

    default_code = p0
    title_raw = p1
    if not default_code and title_raw:
        default_code = slug_code(title_raw)
        note = "synthetic_default_code_from_title"
    else:
        note = ""

    qty: int | str = ""
    if qty_s:
        try:
            qty = int(float(qty_s))
        except ValueError:
            qty = qty_s

    cost: float | str = ""
    if cost_s:
        try:
            cost = float(cost_s)
        except ValueError:
            cost = cost_s

    # Odell typo flag
    if "odell" in title_raw.lower():
        note = (note + ";typo_odell").strip(";")

    return {
        "default_code": default_code,
        "title_raw": title_raw,
        "brand": brand,
        "quantity": qty,
        "cost_ex": cost,
        "condition_note": "",
        "unit_identifiers": "|".join(extras),
        "row_note": note,
    }


def is_header_row(parts: list[str]) -> bool:
    if len(parts) < 2:
        return False
    return parts[0].strip().lower() == "product" and parts[1].strip().lower() == "title"


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Missing {SRC}")

    current_section = ""
    out_rows: list[dict] = []

    for raw in SRC.read_text(encoding="utf-8").splitlines():
        row = parts(raw)
        if not any(x.strip() for x in row):
            continue
        if is_header_row(row):
            continue
        if is_section_row(row):
            current_section = row[1].strip()
            continue

        if looks_like_networking_special(row):
            rec = parse_networking_special(row)
            rec["section"] = current_section or "Networking"
            out_rows.append(rec)
            continue

        rec = parse_standard_row(row, current_section)
        if not rec:
            continue
        rec["section"] = current_section
        out_rows.append(rec)

    fieldnames = [
        "section",
        "default_code",
        "title_raw",
        "brand",
        "quantity",
        "cost_ex",
        "condition_note",
        "unit_identifiers",
        "row_note",
    ]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"Wrote {len(out_rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
