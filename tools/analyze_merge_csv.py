#!/usr/bin/env python3
"""Summarize MERGED import-ready CSV for frontend stock verification."""
import csv
import sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else (
    r"C:\Users\User\OneDrive - Co-Creative IT\Desktop\re-ware merge"
    r"\MERGED import-ready 2026-06-19.csv"
)

rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
by_mtm = defaultdict(lambda: {"SUCCESS": [], "FAILED": [], "model": ""})

for r in rows:
    mtm = (r.get("MTM") or "").strip()
    serial = (r.get("Serial") or "").strip()
    status = (r.get("Status") or "").strip().upper()
    model = (r.get("Model name") or r.get("Series") or "").strip()
    if not mtm:
        continue
    if model:
        by_mtm[mtm]["model"] = model
    if status == "SUCCESS":
        by_mtm[mtm]["SUCCESS"].append(serial)
    else:
        by_mtm[mtm]["FAILED"].append((serial, (r.get("Failure reason") or "").strip()))

total_success = sum(len(v["SUCCESS"]) for v in by_mtm.values())
total_failed = sum(len(v["FAILED"]) for v in by_mtm.values())

print("=== SUMMARY ===")
print(f"File: {path}")
print(f"Total rows: {len(rows)}")
print(f"SUCCESS (will import): {total_success}")
print(f"FAILED (skipped): {total_failed}")
print(f"Unique MTM/SKU: {len(by_mtm)}")
print()
print("=== BY MTM — expected shop stock (SUCCESS only) ===")
print(f"{'MTM':<14} {'Qty':>4}  Model")
print("-" * 60)
for mtm in sorted(by_mtm.keys(), key=lambda m: (-len(by_mtm[m]["SUCCESS"]), m)):
    d = by_mtm[mtm]
    n = len(d["SUCCESS"])
    if n == 0:
        continue
    print(f"{mtm:<14} {n:>4}  {d['model']}")

grand = 0
print("-" * 60)
for mtm in sorted(by_mtm.keys()):
    grand += len(by_mtm[mtm]["SUCCESS"])
print(f"{'TOTAL':<14} {grand:>4}")
print()
print("=== SERIAL LIST (SUCCESS) ===")
for mtm in sorted(by_mtm.keys()):
    succ = by_mtm[mtm]["SUCCESS"]
    if not succ:
        continue
    print(f"\n--- {mtm} ({len(succ)}) {by_mtm[mtm]['model']} ---")
    for s in sorted(succ):
        print(f"  {s}")

if total_failed:
    print("\n=== FAILED (not imported) ===")
    for mtm in sorted(by_mtm.keys()):
        for serial, reason in by_mtm[mtm]["FAILED"]:
            r = reason or "no reason"
            print(f"  {mtm} | {serial} | {r}")
