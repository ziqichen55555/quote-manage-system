# -*- coding: utf-8 -*-
"""
Re-Ware: merge wp DELIVERY RECEIPT (Sheet1 master) + Blancco export.
Double-click run_merge.bat in the folder that contains the input files.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill

# --- Config (edit prefixes here if filenames change) ---
SCRIPT_DIR = Path(__file__).resolve().parent
RECEIPT_PREFIX = "wp DELIVERY RECEIPT"
BLANCCO_PREFIXES = ("reports blannco", "reports blancco")
RECEIPT_EXTENSIONS = (".xlsx",)
BLANCCO_EXTENSIONS = (".csv", ".xlsx")
MTM_LUT_FILE = SCRIPT_DIR / "mtm_lookup.csv"
OUTPUT_PREFIX = "MERGED import-ready"

SERIAL_S_PREFIX = re.compile(r"^S((?:PC|PF|GM|R)\w+)$", re.I)
GEN_RE = re.compile(r"gen\s*(\d+\w*)", re.I)
SYSVER_GEN_RE = re.compile(r"Gen(?:eration)?\s*(\d+\w*)", re.I)

OUTPUT_COLUMNS = [
    "Serial",
    "MTM",
    "Model name",
    "System version",
    "Series",
    "Touch",
    "WAN",
    "Generation",
    "CPU",
    "RAM (GB)",
    "SSD type",
    "SSD size (GB)",
    "Battery (%)",
    "GPU",
    "Mobo status",
    "Blancco date",
    "Manufacturer",
    "Price",
    "Status",
    "Failure reason",
]

FAIL_FILL = PatternFill(start_color="FFFFC7CE", end_color="FFFFC7CE", fill_type="solid")
HEADER_FILL = PatternFill(start_color="FFD9E1F2", end_color="FFD9E1F2", fill_type="solid")

def normalize_serial(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().upper()
    if not s:
        return ""
    m = SERIAL_S_PREFIX.match(s)
    if m:
        return m.group(1).upper()
    return s

def normalize_mtm(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().upper()

def parse_size_gb(text) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = str(text).strip()
    m = re.search(r"(\d+)", s)
    return m.group(1) if m else ""

def parse_name_attrs(name: str) -> dict:
    n = (name or "").strip()
    low = n.lower()
    touch = ""
    if "non-touch" in low or "non touch" in low:
        touch = "No"
    elif "touch" in low:
        touch = "Yes"
    wan = ""
    if re.search(r"\bwan\b", low):
        wan = "Yes"
    elif touch == "Yes":
        wan = "No"
    gen = ""
    m = GEN_RE.search(n)
    if m:
        gen = m.group(1)
    clean = re.sub(r"^lenovo\s+", "", n, flags=re.I).strip()
    # WD receipt name — strip generation suffix; Gen comes from Blancco System version.
    clean = re.sub(r"\s*Gen(?:eration)?\s*\d+\w*\s*$", "", clean, flags=re.I).strip()
    return {"model_name": clean, "touch": touch, "wan": wan, "generation": gen}

def parse_generation_from_system_version(system_version: str) -> str:
    """Gen 1 / Gen 2i / Gen 3 from Blancco System version (authoritative)."""
    if not system_version:
        return ""
    m = SYSVER_GEN_RE.search(str(system_version))
    return m.group(1) if m else ""

def derive_series_label(system_version: str, model_name: str, mtm: str) -> str:
    """Product family for grouping: e.g. ThinkPad T14s Gen 1 vs Gen 2i (never lumped)."""
    gen = parse_generation_from_system_version(system_version)
    base = ""
    if system_version:
        base = re.sub(
            r"\s*Gen(?:eration)?\s*\d+\w*\s*$", "", str(system_version).strip(), flags=re.I
        ).strip()
    if not base and model_name:
        base = str(model_name).strip()
    if not base:
        base = mtm
    if gen:
        return f"{base} Gen {gen}"
    return base

def find_latest_file(folder: Path, prefixes: tuple[str, ...], extensions: tuple[str, ...]) -> Path | None:
    candidates: list[Path] = []
    for path in folder.iterdir():
        if not path.is_file():
            continue
        name_lower = path.name.lower()
        if path.suffix.lower() not in extensions:
            continue
        if any(name_lower.startswith(p.lower()) for p in prefixes):
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

def pick_files_interactive(folder: Path) -> tuple[Path, Path]:
    receipt = find_latest_file(folder, (RECEIPT_PREFIX,), RECEIPT_EXTENSIONS)
    blancco = find_latest_file(folder, BLANCCO_PREFIXES, BLANCCO_EXTENSIONS)

    # Headless / auto-confirm mode: skip popups (used for testing / scheduled runs)
    if "--yes" in sys.argv or "--auto" in sys.argv:
        if not receipt or not blancco:
            raise FileNotFoundError(
                "Auto mode: need both a delivery receipt and a Blancco file in "
                + str(folder)
            )
        print("Auto merge:", receipt.name, "+", blancco.name)
        return receipt, blancco

    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    if receipt and blancco:
        msg = (
            "Found these files in this folder:\n\n"
            f"Delivery receipt:\n  {receipt.name}\n\n"
            f"Blancco report:\n  {blancco.name}\n\n"
            "Merge now? (WD is master; each row will pull Blancco specs by serial)"
        )
        if messagebox.askyesno("Re-Ware merge", msg):
            root.destroy()
            return receipt, blancco

    messagebox.showinfo("Re-Ware merge", "Pick the delivery receipt (.xlsx).")
    receipt = Path(
        filedialog.askopenfilename(
            title="Delivery receipt",
            initialdir=str(folder),
            filetypes=[("Excel", "*.xlsx")],
        )
    )
    if not receipt or not str(receipt):
        root.destroy()
        sys.exit(0)

    messagebox.showinfo("Re-Ware merge", "Pick the Blancco report (.csv or .xlsx).")
    blancco = Path(
        filedialog.askopenfilename(
            title="Blancco report",
            initialdir=str(folder),
            filetypes=[("CSV/Excel", "*.csv *.xlsx")],
        )
    )
    root.destroy()
    if not blancco or not str(blancco):
        sys.exit(0)
    return receipt, blancco

def load_receipt_sheet1(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    mtm_col = col_map.get("model mtm") or col_map.get("mtm")
    serial_col = col_map.get("serial no.") or col_map.get("serial no") or col_map.get("serial")
    if not mtm_col or not serial_col:
        raise ValueError(f"Sheet1 must have 'Model MTM' and 'Serial no.' columns. Found: {list(df.columns)}")
    out = df[[mtm_col, serial_col]].copy()
    out.columns = ["mtm_raw", "serial_raw"]
    out["mtm"] = out["mtm_raw"].map(normalize_mtm)
    out["serial"] = out["serial_raw"].map(normalize_serial)
    out = out[(out["serial"] != "") & (out["mtm"] != "")]
    out = out.drop_duplicates(subset=["serial"], keep="first")
    return out.reset_index(drop=True)

def load_receipt_sheet2_meta(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (serial->comments/uncollected, rows for MTM LUT generation)."""
    try:
        raw = pd.read_excel(path, sheet_name=1, header=None, dtype=str)
    except Exception:
        return pd.DataFrame(columns=["serial", "uncollected"]), pd.DataFrame()

    header_row = None
    for i, row in raw.iterrows():
        cells = [str(x).strip().lower() for x in row.tolist() if pd.notna(x)]
        if "serial no." in cells or "serial no" in cells:
            header_row = i
            break
    if header_row is None:
        return pd.DataFrame(columns=["serial", "uncollected"]), pd.DataFrame()

    df = pd.read_excel(path, sheet_name=1, header=int(header_row), dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    serial_col = col_map.get("serial no.") or col_map.get("serial no")
    name_col = col_map.get("name")
    comments_col = col_map.get("comments")
    if not serial_col:
        return pd.DataFrame(columns=["serial", "uncollected"]), pd.DataFrame()

    meta = df[[serial_col] + ([comments_col] if comments_col else []) + ([name_col] if name_col else [])].copy()
    meta["serial"] = meta[serial_col].map(normalize_serial)
    meta = meta[meta["serial"] != ""]
    if comments_col:
        meta["uncollected"] = meta[comments_col].fillna("").str.lower().str.contains("uncollected")
    else:
        meta["uncollected"] = False
    if name_col:
        meta["name"] = meta[name_col].fillna("")

    uncollected_df = meta[["serial", "uncollected"]].drop_duplicates("serial")
    lut_rows = meta[["serial", "name"]].drop_duplicates("serial") if name_col else pd.DataFrame()
    return uncollected_df, lut_rows

def load_blancco(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, dtype=str)
    else:
        df = pd.read_excel(path, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]

    def pick(*names):
        lower = {c.lower(): c for c in df.columns}
        for n in names:
            if n.lower() in lower:
                return lower[n.lower()]
        return None

    serial_col = pick("System serial", "Serial", "System serial number")
    if not serial_col:
        raise ValueError(f"Blancco file needs a serial column. Found: {list(df.columns)}")

    mapping = {
        "blancco_date": pick("Creation date"),
        "blancco_title": pick("System version"),
        "blancco_mtm": pick("System model"),
        "cpu": pick("CPU model", "CPU"),
        "disk_capacity": pick("Disk capacity", "Disk capacit"),
        "ssd_type": pick("Disk interface type"),
        "ram": pick("Physical_memory", "Physical memory", "RAM"),
        "battery": pick("Capacity"),
        "gpu": pick("Video card model", "GPU"),
        "mobo_status": pick("Motherboard test status", "CMOS condition"),
    }

    out = pd.DataFrame()
    out["serial"] = df[serial_col].map(normalize_serial)
    for key, col in mapping.items():
        out[key] = df[col] if col else ""
    out = out[out["serial"] != ""]
    out["_duplicate_count"] = out.groupby("serial")["serial"].transform("count")

    if "blancco_date" in out.columns and out["blancco_date"].notna().any():
        out = out.sort_values("blancco_date", ascending=False)
    out = out.drop_duplicates(subset=["serial"], keep="first")
    return out.reset_index(drop=True)

def ensure_mtm_lookup(receipt_path: Path, sheet1: pd.DataFrame, sheet2_names: pd.DataFrame) -> pd.DataFrame:
    if MTM_LUT_FILE.is_file():
        lut = pd.read_csv(MTM_LUT_FILE, dtype=str)
        lut["mtm"] = lut["mtm"].map(normalize_mtm)
        return lut

    if sheet2_names.empty:
        lut = pd.DataFrame(columns=["mtm", "model_name", "touch", "wan", "generation"])
        lut.to_csv(MTM_LUT_FILE, index=False)
        return lut

    joined = sheet2_names.merge(sheet1[["serial", "mtm"]], on="serial", how="inner")
    rows = []
    for mtm, group in joined.groupby("mtm"):
        names = group["name"].dropna().astype(str)
        name = names.mode().iloc[0] if len(names) else ""
        attrs = parse_name_attrs(name)
        rows.append({"mtm": mtm, **attrs})
    lut = pd.DataFrame(rows)
    lut.to_csv(MTM_LUT_FILE, index=False)
    return lut

def classify_row(wd_row, blancco_row, uncollected: bool) -> tuple[str, str]:
    if uncollected:
        return "FAILED", "Uncollected (not received)"
    if blancco_row is None:
        return "FAILED", "Serial not found in Blancco"
    if int(blancco_row.get("_duplicate_count", 1) or 1) > 1:
        pass  # already deduped; note in reason if needed
    cpu = str(blancco_row.get("cpu", "") or "").strip()
    disk = str(blancco_row.get("disk_capacity", "") or "").strip()
    if not cpu and not disk:
        return "FAILED", "Serial in Blancco but specs empty"
    return "SUCCESS", ""

def merge_data(
    wd: pd.DataFrame,
    blancco: pd.DataFrame,
    lut: pd.DataFrame,
    uncollected_map: dict[str, bool],
) -> pd.DataFrame:
    blancco_idx = blancco.set_index("serial", drop=False)
    lut_idx = lut.set_index("mtm", drop=False) if not lut.empty else {}

    rows = []
    for _, wd_row in wd.iterrows():
        serial = wd_row["serial"]
        mtm = wd_row["mtm"]
        bl = blancco_idx.loc[serial] if serial in blancco_idx.index else None
        if bl is not None and isinstance(bl, pd.DataFrame):
            bl = bl.iloc[0]

        uncollected = uncollected_map.get(serial, False)
        status, reason = classify_row(wd_row, bl, uncollected)

        lut_row = lut_idx.loc[mtm] if mtm in getattr(lut_idx, "index", []) else None
        if lut_row is not None and isinstance(lut_row, pd.DataFrame):
            lut_row = lut_row.iloc[0]

        model_name = ""
        touch = wan = ""
        if lut_row is not None:
            model_name = str(lut_row.get("model_name", "") or "")
            model_name = re.sub(
                r"\s*Gen(?:eration)?\s*\d+\w*\s*$", "", model_name, flags=re.I
            ).strip()
            touch = str(lut_row.get("touch", "") or "")
            wan = str(lut_row.get("wan", "") or "")

        system_version = str(bl.get("blancco_title", "") or "") if bl is not None else ""
        gen = parse_generation_from_system_version(system_version)
        if not gen and lut_row is not None:
            gen = str(lut_row.get("generation", "") or "").strip()
        series = derive_series_label(system_version, model_name, mtm)

        rows.append(
            {
                "Serial": serial,
                "MTM": mtm,
                "Model name": model_name,
                "System version": system_version,
                "Series": series,
                "Touch": touch,
                "WAN": wan,
                "Generation": gen,
                "CPU": str(bl.get("cpu", "") if bl is not None else ""),
                "RAM (GB)": parse_size_gb(bl.get("ram", "") if bl is not None else ""),
                "SSD type": str(bl.get("ssd_type", "") if bl is not None else ""),
                "SSD size (GB)": parse_size_gb(bl.get("disk_capacity", "") if bl is not None else ""),
                "Battery (%)": str(bl.get("battery", "") if bl is not None else ""),
                "GPU": str(bl.get("gpu", "") if bl is not None else ""),
                "Mobo status": str(bl.get("mobo_status", "") if bl is not None else ""),
                "Blancco date": str(bl.get("blancco_date", "") if bl is not None else ""),
                "Manufacturer": "LENOVO",
                "Price": "",
                "Status": status,
                "Failure reason": reason,
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

def build_analysis(merged: pd.DataFrame) -> pd.DataFrame:
    total = len(merged)
    success = int((merged["Status"] == "SUCCESS").sum())
    failed = total - success
    rate = f"{(success / total * 100):.1f}%" if total else "0%"

    lines = [
        ["Metric", "Value"],
        ["WD rows (master)", total],
        ["Matched (SUCCESS)", success],
        ["Failed", failed],
        ["Match rate", rate],
        ["", ""],
        ["Failure breakdown", "Count"],
    ]
    if failed:
        for reason, cnt in merged.loc[merged["Status"] == "FAILED", "Failure reason"].value_counts().items():
            lines.append([reason, int(cnt)])
    else:
        lines.append(["(none)", 0])
    lines.append(["", ""])
    lines.append(["Failed serials (for investigation)", "MTM"])
    for _, r in merged.loc[merged["Status"] == "FAILED"].iterrows():
        lines.append([r["Serial"], r["MTM"]])

    return pd.DataFrame(lines)

def write_output(merged: pd.DataFrame, analysis: pd.DataFrame, out_path: Path) -> None:
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        merged.to_excel(writer, sheet_name="Devices", index=False)
        analysis.to_excel(writer, sheet_name="Analysis", index=False, header=False)

    wb = load_workbook(out_path)
    ws = wb["Devices"]
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = Font(bold=True)

    status_col = OUTPUT_COLUMNS.index("Status") + 1
    for row_idx in range(2, ws.max_row + 1):
        if ws.cell(row=row_idx, column=status_col).value == "FAILED":
            for col_idx in range(1, len(OUTPUT_COLUMNS) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = FAIL_FILL
    wb.save(out_path)

def failure_summary_text(merged: pd.DataFrame) -> str:
    failed = merged[merged["Status"] == "FAILED"]
    if failed.empty:
        return ""
    lines = ["\nFailed serials (not in Odoo CSV):"]
    for _, row in failed.iterrows():
        lines.append(f"  {row['Serial']} ({row['MTM']}): {row['Failure reason']}")
    return "\n".join(lines)

def show_result_popup(summary: str, out_path: Path) -> None:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo("Re-Ware merge complete", summary + f"\n\nSaved:\n{out_path}")
    root.destroy()

def main() -> int:
    folder = SCRIPT_DIR
    receipt_path, blancco_path = pick_files_interactive(folder)

    wd = load_receipt_sheet1(receipt_path)
    uncollected_df, sheet2_names = load_receipt_sheet2_meta(receipt_path)
    uncollected_map = dict(zip(uncollected_df["serial"], uncollected_df["uncollected"])) if not uncollected_df.empty else {}
    blancco = load_blancco(blancco_path)
    lut = ensure_mtm_lookup(receipt_path, wd, sheet2_names)

    merged = merge_data(wd, blancco, lut, uncollected_map)

    stamp = datetime.now().strftime("%Y-%m-%d")
    out_path = folder / f"{OUTPUT_PREFIX} {stamp}.csv"
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")

    total = len(merged)
    success = int((merged["Status"] == "SUCCESS").sum())
    failed = total - success
    summary = (
        f"WD master rows: {total}\n"
        f"SUCCESS (Blancco data pulled): {success}\n"
        f"FAILED: {failed}\n"
        f"Match rate: {(success/total*100):.1f}%" if total else "No rows"
    )
    summary += failure_summary_text(merged)
    summary += (
        f"\n\nSaved merge file:\n  {out_path.name}\n"
        f"  (one row per device — upload this file in Odoo:\n"
        f"   Inventory -> Upload inventory CSV, after DB backup)"
    )
    if "--yes" in sys.argv or "--auto" in sys.argv:
        print(summary)
        print("Saved:", out_path)
    else:
        show_result_popup(summary, out_path)
    return 0 if failed == 0 else 2

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror("Re-Ware merge error", str(exc))
        root.destroy()
        raise