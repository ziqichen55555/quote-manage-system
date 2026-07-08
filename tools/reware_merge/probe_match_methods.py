# -*- coding: utf-8 -*-
"""Probe which safe match methods could resolve each failed row."""
from __future__ import annotations

from difflib import SequenceMatcher
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

# One-char swaps we allow (NOT L↔1 — PC1TKK8L and PC1TKK81 are different units).
CONFUSABLE_PAIRS = {
    ("I", "1"),
    ("O", "0"),
    ("S", "5"),
    ("B", "8"),
    ("Z", "2"),
    ("G", "6"),
    ("Q", "0"),
}


def one_char_confusable(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    diffs = [(x, y) for x, y in zip(a, b) if x != y]
    if len(diffs) != 1:
        return False
    x, y = diffs[0]
    return (x, y) in CONFUSABLE_PAIRS or (y, x) in CONFUSABLE_PAIRS


def serial_alias_variants(serial: str) -> list[str]:
    s = normalize_serial(serial)
    out = {s}
    if s.startswith("S") and len(s) > 1:
        out.add(s[1:])
    if s.startswith("PCIF"):
        out.add("PC1F" + s[4:])
    if s.startswith("PC1F") and len(s) > 4:
        out.add("PCIF" + s[4:])
    return list(out)


def probe_same_mtm_one_edit(
    serial: str,
    mtm: str,
    blancco: pd.DataFrame,
    scan_serials: set[str],
    claimed: set[str],
) -> list[tuple[str, str]]:
    hits = []
    pool = blancco[blancco["blancco_mtm"].astype(str).str.upper().eq(mtm.upper())]
    for bl_sn in pool["serial"].astype(str):
        bl_u = bl_sn.upper()
        if bl_u in scan_serials and bl_u != serial.upper():
            continue
        if bl_u in claimed:
            continue
        if one_char_confusable(serial.upper(), bl_u):
            hits.append((bl_u, "same_mtm_one_confusable_char"))
    return hits


def main() -> None:
    not_ready = pd.read_csv(FOLDER / "MERGED import-not-ready 2026-07-08.csv", dtype=str)
    failed = not_ready[
        not_ready["Status"].astype(str).str.upper().eq("FAILED")
        & ~not_ready["Not ready reason"].astype(str).str.contains("Sold", case=False, na=False)
    ]
    blancco = load_blancco(FOLDER / "reports.csv")
    wd = load_product_list(FOLDER / "SCANNED STOCK FOR PORTAL merged 08-07-26.csv")
    by_s, by_k, by_m = build_blancco_indexes(blancco)
    scan_serials = set(wd["serial"].astype(str).str.upper())

    # Serials already successfully matched in import-all
    import_all = pd.read_csv(FOLDER / "MERGED import-all 2026-07-08.csv", dtype=str)
    claimed = set(import_all["Serial"].astype(str).str.upper())

    print("Method tiers:")
    print("  A exact (current merge)")
    print("  B alias: S-prefix strip, PCIF<->PC1F")
    print("  C same MTM + exactly 1 confusable-char diff, target not another scan row")
    print()

    for _, r in failed.iterrows():
        sn = normalize_serial(r["Serial"])
        mtm = str(r["MTM"] or "").strip().upper()
        bl, kind = resolve_blancco_row(by_s, by_k, by_m, sn, mtm)
        if bl is not None:
            print(f"{sn} | already resolves via current merge ({kind})")
            continue

        methods = []
        for v in serial_alias_variants(sn):
            if v not in by_s.index:
                continue
            if v in scan_serials and v != sn.upper():
                methods.append((v, f"B_blocked_scan_has_{v}"))
            elif v in claimed and v != sn.upper():
                methods.append((v, f"B_blocked_claimed_{v}"))
            else:
                methods.append((v, "B_alias"))

        edits = probe_same_mtm_one_edit(sn, mtm, blancco, scan_serials, claimed)
        for target, label in edits:
            methods.append((target, f"C_{label}"))

        if not methods:
            print(f"{sn} | {mtm} | NO_SAFE_METHOD")
        elif len({m[0] for m in methods if not m[1].startswith("B_blocked")}) == 1:
            t, lab = next(m for m in methods if not m[1].startswith("B_blocked"))
            print(f"{sn} | {mtm} | MATCH -> {t} via {lab}")
        else:
            opts = ", ".join(f"{t}({lab})" for t, lab in methods)
            print(f"{sn} | {mtm} | AMBIGUOUS: {opts}")


if __name__ == "__main__":
    main()
