# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

p = Path(r"C:\Users\User\OneDrive - Co-Creative IT\Desktop\re-ware merge\MERGED import-ready 2026-06-18.csv")
df = pd.read_csv(p, dtype=str)
ok = df[df["Status"] == "SUCCESS"].copy()
print("Total SUCCESS:", len(ok))
print()

t14 = ok[
    ok["System version"].str.contains("T14s", case=False, na=False)
    | ok["Series"].str.contains("T14s", case=False, na=False)
]
print("=== ThinkPad T14s ===")
print(t14.groupby(["System version", "MTM"]).size().reset_index(name="count").to_string(index=False))
print()

for term in ("P510", "ThinkStation", "THINKSTATION"):
    mask = ok.apply(lambda r, t=term: t.upper() in str(r.values).upper(), axis=1)
    sub = ok[mask]
    if len(sub):
        print(f"=== {term} ({len(sub)} rows) ===")
        cols = ["Serial", "MTM", "Model name", "System version", "Series", "CPU", "RAM (GB)", "SSD size (GB)"]
        print(sub[cols].drop_duplicates(["MTM", "System version"]).to_string(index=False))
        print()

print("=== System version -> MTM counts ===")
for sv, grp in ok.groupby("System version", dropna=False):
    label = sv if pd.notna(sv) and str(sv).strip() else "(empty)"
    mtms = sorted(grp["MTM"].dropna().unique())
    print(f"{label}: {len(grp)} devices, {len(mtms)} MTM -> {mtms}")
