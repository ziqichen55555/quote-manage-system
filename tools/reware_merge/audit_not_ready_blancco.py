# -*- coding: utf-8 -*-
"""Audit import-not-ready rows against Blancco reports.csv.

Checks whether failures are truly missing or caused by SN/MTM parsing typos.

Usage:
  py audit_not_ready_blancco.py [merge_folder]

Defaults to Desktop re-ware merge folder.
"""
from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

from merge_receipt_blancco import (
    load_blancco,
    normalize_product_row,
    normalize_serial,
    normalize_mtm,
    fix_thinkcentre_mtm_typo,
    parse_thinkcentre_glued_code,
)

DEFAULT_FOLDER = Path(r"C:\Users\User\OneDrive - Co-Creative IT\Desktop\re-ware merge")


def serial_variants(serial: str) -> list[str]:
    """Conservative OCR/scan variants — only patterns we trust, not L↔1 globally."""
    s = normalize_serial(serial)
    if not s:
        return []
    variants = {s}
    # Known portal mis-scan: I read as 1 after PC prefix (e.g. PCIFVNGF → PC1FVNGF).
    if s.startswith("PCIF"):
        variants.add("PC1F" + s[4:])
    if s.startswith("PC1F") and len(s) > 4:
        variants.add("PCIF" + s[4:])
    if s.startswith("S") and len(s) > 1:
        variants.add(s[1:])
    return [v for v in variants if v]


def variant_blocked_by_scan(variant: str, serial: str, scan_serials: set[str]) -> bool:
    """Do not remap to a reports SN that is already a separate scanned unit."""
    variant_u = variant.upper()
    serial_u = serial.upper()
    if variant_u == serial_u:
        return False
    return variant_u in scan_serials


def find_not_ready_file(folder: Path) -> Path:
    candidates = sorted(folder.glob("MERGED import-not-ready *.csv"), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No MERGED import-not-ready *.csv in {folder}")
    return candidates[0]


def find_scan_file(folder: Path) -> Path | None:
    candidates = sorted(folder.glob("SCANNED STOCK FOR PORTAL merged *.csv"), reverse=True)
    return candidates[0] if candidates else None


def load_scan_lookup(scan_path: Path | None) -> dict[str, tuple[str, str]]:
    """serial -> (raw_mtm_col, raw_serial_col) from merged scan export."""
    if not scan_path or not scan_path.is_file():
        return {}
    df = pd.read_csv(scan_path, dtype=str)
    mtm_col = next((c for c in df.columns if "mtm" in c.lower()), df.columns[0])
    sn_col = next((c for c in df.columns if "serial" in c.lower()), df.columns[1])
    out: dict[str, tuple[str, str]] = {}
    for _, row in df.iterrows():
        raw_mtm = str(row[mtm_col] or "").strip()
        raw_sn = str(row[sn_col] or "").strip()
        mtm, serial = normalize_product_row(raw_mtm, raw_sn)
        if serial:
            out[serial.upper()] = (raw_mtm, raw_sn)
    return out


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def audit_row(
    serial: str,
    mtm: str,
    blancco: pd.DataFrame,
    scan_lookup: dict[str, tuple[str, str]],
    scan_serials: set[str],
) -> dict:
    serial = normalize_serial(serial)
    mtm = fix_thinkcentre_mtm_typo(normalize_mtm(mtm))
    raw_mtm, raw_sn = scan_lookup.get(serial, ("", ""))

    result = {
        "serial": serial,
        "mtm": mtm,
        "scan_raw_mtm": raw_mtm,
        "scan_raw_serial": raw_sn,
        "verdict": "NOT_IN_REPORTS",
        "match_method": "",
        "reports_serial": "",
        "reports_model": "",
        "reports_version": "",
        "reports_date": "",
        "near_miss_serial": "",
        "near_miss_distance": "",
        "notes": "",
    }

    by_serial = blancco.set_index("serial", drop=False)

    for variant in serial_variants(serial):
        if variant not in by_serial.index:
            continue
        if variant_blocked_by_scan(variant, serial, scan_serials):
            continue
        row = by_serial.loc[variant]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        bl_mtm = normalize_mtm(str(row.get("blancco_mtm", "") or ""))
        result.update(
            {
                "verdict": "FOUND_EXACT" if variant == serial else "FOUND_TYPO_VARIANT",
                "match_method": f"serial={variant}",
                "reports_serial": variant,
                "reports_model": bl_mtm,
                "reports_version": str(row.get("blancco_title", "") or ""),
                "reports_date": str(row.get("blancco_date", "") or ""),
                "notes": "" if variant == serial else f"Scan SN '{serial}' -> reports '{variant}'",
            }
        )
        if mtm and bl_mtm and mtm != bl_mtm:
            result["notes"] += f"; MTM scan={mtm} reports={bl_mtm}"
        return result

    # ThinkCentre: rebuild candidates from raw scan glue if present
    glue_candidates: list[str] = []
    if raw_mtm and raw_sn:
        fixed_mtm, fixed_sn = normalize_product_row(raw_mtm, raw_sn)
        if fixed_sn and fixed_sn != serial:
            glue_candidates.append(fixed_sn)
        mtm_glue, prefix = parse_thinkcentre_glued_code(raw_mtm)
        if mtm_glue and prefix and raw_sn:
            glue_candidates.append(normalize_serial(prefix + raw_sn.upper()))
    for candidate in glue_candidates:
        if candidate in by_serial.index:
            row = by_serial.loc[candidate]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            result.update(
                {
                    "verdict": "FOUND_REBUILT_FROM_SCAN",
                    "match_method": f"rebuilt={candidate}",
                    "reports_serial": candidate,
                    "reports_model": normalize_mtm(str(row.get("blancco_mtm", "") or "")),
                    "reports_version": str(row.get("blancco_title", "") or ""),
                    "reports_date": str(row.get("blancco_date", "") or ""),
                    "notes": f"Raw scan {raw_mtm!r},{raw_sn!r}",
                }
            )
            return result

    # Suffix match within same MTM (ThinkCentre tail only)
    if mtm:
        mtm_rows = blancco[
            blancco["blancco_mtm"].astype(str).str.upper().eq(mtm.upper())
        ]
        suffix_hits = mtm_rows[
            mtm_rows["serial"].astype(str).str.upper().str.endswith(serial.upper())
        ]
        if len(suffix_hits) == 1:
            row = suffix_hits.iloc[0]
            result.update(
                {
                    "verdict": "FOUND_SUFFIX_MTM",
                    "match_method": "suffix+mtm",
                    "reports_serial": str(row["serial"]),
                    "reports_model": mtm,
                    "reports_version": str(row.get("blancco_title", "") or ""),
                    "reports_date": str(row.get("blancco_date", "") or ""),
                    "notes": f"Serial ends with {serial}",
                }
            )
            return result
        if len(suffix_hits) > 1:
            result["notes"] = f"{len(suffix_hits)} suffix hits for MTM {mtm}: " + ", ".join(
                suffix_hits["serial"].astype(str).tolist()[:5]
            )

    # Near-miss: same MTM, edit distance ~1 on serial
    if mtm:
        pool = blancco[blancco["blancco_mtm"].astype(str).str.upper().eq(mtm.upper())]
    else:
        pool = blancco
    best_sn = ""
    best_score = 0.0
    for bl_sn in pool["serial"].astype(str):
        bl_sn_u = bl_sn.upper()
        if variant_blocked_by_scan(bl_sn_u, serial, scan_serials):
            continue
        for variant in serial_variants(serial):
            score = similarity(variant, bl_sn_u)
            if score > best_score:
                best_score = score
                best_sn = bl_sn_u
    if best_sn and best_score >= 0.85:
        result["near_miss_serial"] = best_sn
        result["near_miss_distance"] = f"{best_score:.3f}"
        result["verdict"] = "NEAR_MISS_SAME_MTM"
        result["notes"] = f"Closest same-MTM SN (not auto-matched): {best_sn}"

    if mtm and serial in scan_serials:
        siblings = sorted(s for s in scan_serials if s != serial and similarity(s, serial) >= 0.85)
        if siblings and result["verdict"] == "NOT_IN_REPORTS":
            result["notes"] = (
                (result["notes"] + f"; scan also has similar SN(s): {', '.join(siblings[:4])}")
                .strip("; ")
            )

    # MTM-only inventory in reports
    if mtm and result["verdict"] == "NOT_IN_REPORTS":
        mtm_rows = blancco[
            blancco["blancco_mtm"].astype(str).str.upper().eq(mtm.upper())
        ]
        mtm_count = len(mtm_rows)
        if mtm_count:
            sns = mtm_rows["serial"].astype(str).tolist()
            result["notes"] = (
                (result["notes"] + f"; MTM {mtm} has {mtm_count} other unit(s) in reports: {', '.join(sns[:6])}")
                .strip("; ")
            )
            if mtm_count == 1:
                only_sn = sns[0].upper()
                if not variant_blocked_by_scan(only_sn, serial, scan_serials):
                    score = max(similarity(v, only_sn) for v in serial_variants(serial))
                    if score >= 0.75:
                        result["verdict"] = "NEAR_MISS_SAME_MTM"
                        result["near_miss_serial"] = only_sn
                        result["near_miss_distance"] = f"{score:.3f}"
                        result["notes"] = (
                            f"Only Blancco SN for MTM {mtm} is {only_sn}; scan may be typo of this unit"
                        )

    return result


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FOLDER
    not_ready_path = find_not_ready_file(folder)
    reports_path = folder / "reports.csv"
    scan_path = find_scan_file(folder)

    if not reports_path.is_file():
        raise FileNotFoundError(f"Missing {reports_path}")

    not_ready = pd.read_csv(not_ready_path, dtype=str)
    failed = not_ready[
        not_ready["Status"].astype(str).str.upper().eq("FAILED")
        & ~not_ready["Not ready reason"].astype(str).str.contains("Sold", case=False, na=False)
    ].copy()

    blancco = load_blancco(reports_path)
    scan_lookup = load_scan_lookup(scan_path)
    scan_serials = set(scan_lookup.keys())

    rows = [
        audit_row(r["Serial"], r["MTM"], blancco, scan_lookup, scan_serials)
        for _, r in failed.iterrows()
    ]
    report = pd.DataFrame(rows)

    out_csv = folder / f"audit-not-ready {not_ready_path.stem.split()[-1]}.csv"
    report.to_csv(out_csv, index=False)

    print(f"Not-ready file: {not_ready_path.name}")
    print(f"Reports: {reports_path.name} ({len(blancco)} serials)")
    print(f"Failed (excl. sold): {len(failed)}")
    print(f"Audit saved: {out_csv.name}")
    print()

    verdict_order = ["FOUND_EXACT", "FOUND_TYPO_VARIANT", "FOUND_REBUILT_FROM_SCAN", "FOUND_SUFFIX_MTM", "NEAR_MISS_SAME_MTM", "NOT_IN_REPORTS"]
    for verdict in verdict_order:
        subset = report[report["verdict"] == verdict]
        if subset.empty:
            continue
        print(f"=== {verdict} ({len(subset)}) ===")
        for _, r in subset.iterrows():
            line = f"  {r['serial']} / {r['mtm']}"
            if r["reports_serial"]:
                line += f" -> {r['reports_serial']} ({r['reports_model']})"
            if r["notes"]:
                line += f" | {r['notes']}"
            if r["near_miss_serial"]:
                line += f" | near={r['near_miss_serial']} ({r['near_miss_distance']})"
            print(line)
        print()

    fixable = report[report["verdict"].isin(
        ["FOUND_TYPO_VARIANT", "FOUND_REBUILT_FROM_SCAN", "FOUND_SUFFIX_MTM", "NEAR_MISS_SAME_MTM"]
    )]
    if not fixable.empty:
        print(f"Likely merge-script fixable: {len(fixable)} row(s)")
    truly_missing = report[report["verdict"] == "NOT_IN_REPORTS"]
    print(f"Truly not in reports (or no close match): {len(truly_missing)} row(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
