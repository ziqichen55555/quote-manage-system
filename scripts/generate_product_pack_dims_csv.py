#!/usr/bin/env python3
"""Regenerate exports/product_weights_prod.csv + .xlsx (weight + pack L×W×H).

Single master file for OneDrive / colleague review. Run locally:

  python scripts/generate_product_pack_dims_csv.py

Existing length_cm/width_cm/height_cm in CSV are kept; empty cells get suggestions.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER_CSV = ROOT / "exports" / "product_weights_prod.csv"
MASTER_XLSX = ROOT / "exports" / "product_weights_prod.xlsx"

FIELDNAMES = [
    "product_id",
    "default_code",
    "product_name",
    "internal_category",
    "shop_categories",
    "weight_kg",
    "length_cm",
    "width_cm",
    "height_cm",
    "notes",
]


def text_blob(row):
    parts = [
        row.get("product_name") or "",
        row.get("default_code") or "",
        row.get("internal_category") or "",
        row.get("shop_categories") or "",
    ]
    return " ".join(parts).lower()


def suggest_pack_dims_cm(row):
    blob = text_blob(row)
    shop = (row.get("shop_categories") or "").lower()
    categ = (row.get("internal_category") or "").lower()

    def dims(l, w, h):
        return (l, w, h)

    if re.search(r"\b(dual|2 x|two)\b.*\b(monitor|screen|display)\b", blob) or re.search(
        r"\b(monitor|screen|display).*\bbundle\b", blob
    ):
        if re.search(r"\b24[\"']|24 inch\b", blob):
            return dims(60, 40, 25)
        return dims(55, 38, 22)
    if (
        "cables & adapters" in shop
        or categ == "chargers / power adapters"
        or re.search(r"\b(cable|adapter|charger|hdmi|displayport|usb|ethernet extension)\b", blob)
    ):
        return dims(18, 12, 4)
    if "laptops" in shop or (
        categ == "computer systems"
        and re.search(r"\b(thinkpad|latitude|toughbook|cf-54|elitebook|probook)\b", blob)
    ):
        if re.search(r"\b(toughbook|cf-54)\b", blob):
            return dims(42, 32, 8)
        if re.search(r"\b(t15|p15|17[\"']|17 inch)\b", blob):
            return dims(40, 30, 6)
        return dims(38, 28, 5)
    if re.search(r"\b(optiplex|elite desk|9020|800 g2|tiny|m910)\b", blob):
        if re.search(r"\b(mini|tiny|m910|nuc)\b", blob):
            return dims(35, 30, 15)
        return dims(40, 35, 18)
    if re.search(r"\b(thinkstation|p510|workstation)\b", blob):
        return dims(50, 45, 30)
    if "monitors" in shop or "monitor" in blob:
        if re.search(r"\b32[\"']", blob):
            return dims(75, 45, 15)
        if re.search(r"\b27[\"']", blob):
            return dims(65, 42, 14)
        return dims(55, 35, 12)
    if "docks" in shop or re.search(r"\bdock\b", blob):
        return dims(28, 20, 8)
    if "projector" in blob:
        return dims(38, 30, 12)
    if "digital camera" in shop or re.search(r"\b(camer|powershot|lumix)\b", blob):
        return dims(15, 12, 8)
    if re.search(r"\b(jabra|headphone)\b", blob):
        return dims(22, 18, 10)
    if re.search(r"\b(mouse|keyboard)\b", blob):
        return dims(35, 15, 5)
    if re.search(r"\b(3750|48p)\b", blob):
        return dims(55, 40, 15)
    if re.search(r"\b(router|switch|cisco|meraki|access point)\b", blob):
        return dims(35, 25, 10)
    if re.search(r"\b(backpack|bag)\b", blob):
        return dims(45, 35, 15)
    if re.search(r"\b(speaker|conference cam)\b", blob):
        return dims(30, 25, 20)
    return dims(30, 25, 10)


def _float_cell(row, key):
    raw = (row.get(key) or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def main():
    if not MASTER_CSV.is_file():
        raise SystemExit(f"Missing {MASTER_CSV}")

    with MASTER_CSV.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    out_rows = []
    for row in rows:
        l = _float_cell(row, "length_cm")
        w = _float_cell(row, "width_cm")
        h = _float_cell(row, "height_cm")
        if l is None or w is None or h is None:
            sl, sw, sh = suggest_pack_dims_cm(row)
            l = l if l is not None else sl
            w = w if w is not None else sw
            h = h if h is not None else sh
        out_rows.append(
            {
                "product_id": row["product_id"],
                "default_code": row.get("default_code") or "",
                "product_name": row.get("product_name") or "",
                "internal_category": row.get("internal_category") or "",
                "shop_categories": row.get("shop_categories") or "",
                "weight_kg": row.get("weight_kg") or "",
                "length_cm": l,
                "width_cm": w,
                "height_cm": h,
                "notes": row.get("notes")
                or "Share via OneDrive; edit weight_kg + L/W/H; Odoo import via shell scripts",
            }
        )

    with MASTER_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows -> {MASTER_CSV}")

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        print("openpyxl not installed — skip XLSX (pip install openpyxl)")
        return

    wb = Workbook()
    readme = wb.active
    readme.title = "README"
    readme["A1"] = "Re-Ware product shipping master (OneDrive)"
    readme["A1"].font = Font(bold=True)
    readme["A3"] = "Sheet 'products': one row per Odoo product.template (product_id)."
    readme["A4"] = "weight_kg + length_cm, width_cm, height_cm (bare size; foam added in Odoo Settings)."
    readme["A5"] = "Edit here with colleagues, then sync CSV back to repo or import on prod."

    ws = wb.create_sheet("products")
    ws.append(FIELDNAMES)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for rec in out_rows:
        ws.append([rec[k] for k in FIELDNAMES])
    ws.freeze_panes = "A2"
    wb.save(MASTER_XLSX)
    print(f"Wrote Excel -> {MASTER_XLSX}")


if __name__ == "__main__":
    main()
