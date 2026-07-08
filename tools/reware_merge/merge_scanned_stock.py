# -*- coding: utf-8 -*-
"""Merge multiple SCANNED STOCK FOR PORTAL files into one CSV.

Usage:
  py merge_scanned_stock.py [folder]

Defaults to the script directory. Pass the re-ware merge folder path if needed.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from merge_receipt_blancco import load_portal_scan_stock, normalize_mtm, normalize_serial

SCRIPT_DIR = Path(__file__).resolve().parent


def fix_mtm_typo(mtm: str) -> str:
    """2OJTS15500 → 20JTS15500 (scanner O/0)."""
    if mtm.startswith("2O") and re.match(r"^2O[A-Z0-9]{8}$", mtm):
        return "20" + mtm[2:]
    return mtm


def load_scanned_csv(path: Path) -> list[dict]:
    raw = pd.read_csv(path)
    col_mtm = next((c for c in raw.columns if "mtm" in c.lower()), raw.columns[0])
    col_sn = next((c for c in raw.columns if "serial" in c.lower()), raw.columns[1])
    rows = []
    for _, r in raw.iterrows():
        mtm = fix_mtm_typo(normalize_mtm(r[col_mtm]))
        serial = normalize_serial(str(r[col_sn]))
        if mtm and serial:
            rows.append({"Device MTM": mtm, "Serial": serial, "_source": path.name})
    return rows


def load_scanned_file(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        return load_scanned_csv(path)
    df = load_portal_scan_stock(path)
    return [
        {
            "Device MTM": fix_mtm_typo(r.mtm),
            "Serial": r.serial,
            "_source": path.name,
        }
        for r in df.itertuples()
    ]


def find_scanned_files(folder: Path) -> list[Path]:
    out = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        name = path.name.lower()
        if "merged" in name:
            continue
        if "scanned stock" in name and path.suffix.lower() in (".csv", ".xlsx", ".xls"):
            out.append(path)
    return out


def merge_scanned(folder: Path) -> Path:
    files = find_scanned_files(folder)
    if len(files) < 2:
        raise SystemExit(f"Need at least 2 SCANNED STOCK files in {folder}; found {len(files)}")

    rows: list[dict] = []
    for path in files:
        rows.extend(load_scanned_file(path))

    merged = pd.DataFrame(rows)
    dup = merged[merged.duplicated("Serial", keep=False)]
    if not dup.empty:
        print(f"Note: {dup['Serial'].nunique()} serial(s) in multiple files — keeping last file's row.")

    merged = merged.drop_duplicates(subset=["Serial"], keep="last")
    merged = merged.sort_values(["Device MTM", "Serial"]).reset_index(drop=True)
    out_df = merged[["Device MTM", "Serial"]]

    stamp = datetime.now().strftime("%d-%m-%y")
    out_path = folder / f"SCANNED STOCK FOR PORTAL merged {stamp}.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"Merged {len(files)} files -> {out_path.name}")
    for path in files:
        n = sum(1 for r in rows if r["_source"] == path.name)
        print(f"  {path.name}: {n} rows")
    print(f"Total unique devices: {len(out_df)}")
    return out_path


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else SCRIPT_DIR
    merge_scanned(folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
