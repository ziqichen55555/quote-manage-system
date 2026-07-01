#!/usr/bin/env python3
"""Build one-off Odoo shell script with embedded not-ready rows."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = Path(
    r"C:\Users\User\OneDrive - Co-Creative IT\Desktop\re-ware merge"
) / "MERGED import-not-ready 2026-07-01.csv"
TEMPLATE = ROOT / "scripts" / "check_not_ready_delivered_shell.py"
OUT = ROOT / "backups" / "check_not_ready_delivered_run_20260701.py"

rows = []
with CSV_PATH.open(encoding="utf-8-sig", errors="replace") as f:
    for r in csv.DictReader(f):
        rows.append(
            {
                "serial": (r.get("Serial") or "").strip(),
                "mtm": (r.get("MTM") or "").strip(),
                "shop_sku": (r.get("Shop SKU") or "").strip(),
                "model": (r.get("Model name") or "").strip(),
                "reason": (r.get("Not ready reason") or "").strip(),
                "status": (r.get("Status") or "").strip(),
            }
        )

template = TEMPLATE.read_text(encoding="utf-8")
start = template.find("raw = sys.stdin.read()")
end = template.find("Importer = env")
if start < 0 or end < 0:
    raise SystemExit("template markers not found")

embedded = (
    template[:start]
    + f"rows = {json.dumps(rows, ensure_ascii=False)}\n\n"
    + template[end:]
)
OUT.write_text(embedded, encoding="utf-8")
print(f"Wrote {OUT} ({len(rows)} rows)")
