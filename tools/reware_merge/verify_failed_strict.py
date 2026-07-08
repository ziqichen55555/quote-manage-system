# -*- coding: utf-8 -*-
"""Strict match check: failed not-ready rows vs reports (no typo guessing)."""
from pathlib import Path

import pandas as pd

from merge_receipt_blancco import (
    load_blancco,
    load_product_list,
    normalize_product_row,
    normalize_serial,
    build_blancco_indexes,
    resolve_blancco_row,
)

FOLDER = Path(r"C:\Users\User\OneDrive - Co-Creative IT\Desktop\re-ware merge")

not_ready = pd.read_csv(FOLDER / "MERGED import-not-ready 2026-07-08.csv", dtype=str)
failed = not_ready[
    not_ready["Status"].astype(str).str.upper().eq("FAILED")
    & ~not_ready["Not ready reason"].astype(str).str.contains("Sold", case=False, na=False)
]

blancco = load_blancco(FOLDER / "reports.csv")
by_s, by_k, by_m = build_blancco_indexes(blancco)
report_serials = set(blancco["serial"].astype(str).str.upper())

scan = load_product_list(FOLDER / "SCANNED STOCK FOR PORTAL merged 08-07-26.csv")
scan_idx = scan.set_index("serial", drop=False)

print(f"Failed (excl sold): {len(failed)}")
print(f"Reports serials: {len(report_serials)}")
print()
print("serial | mtm | normalized_sn | in_reports_exact | merge_resolve")

for _, r in failed.iterrows():
    sn = normalize_serial(r["Serial"])
    mtm = str(r["MTM"] or "").strip().upper()
    if sn in scan_idx.index:
        raw = scan_idx.loc[sn]
        if isinstance(raw, pd.DataFrame):
            raw = raw.iloc[0]
        norm_mtm, norm_sn = normalize_product_row(raw["mtm"], raw["serial"])
    else:
        norm_mtm, norm_sn = normalize_product_row(mtm, sn)
    exact = norm_sn in report_serials
    bl, kind = resolve_blancco_row(by_s, by_k, by_m, sn, mtm)
    resolved = "YES" if bl is not None else "NO"
    print(f"{sn} | {mtm} | {norm_sn} | {exact} | {resolved} ({kind or '-'})")
