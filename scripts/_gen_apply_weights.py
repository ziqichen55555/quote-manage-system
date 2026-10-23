# One-off generator — not for prod shell
import csv

WEIGHTS = [
    5, 0.5, 3, 1.5, 3, 1, 1, 1, 4, 4, 1, 10, 2, 0.5, 0.5, 0.5, 1.5, 2.5, 0.5, 3,
    0.5, 0.5, 0.5, 0.5, 0.5, 7, 7, 7, 7, 8, 8, 8, 3, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
    3, 1.5, 1.5, 1.5, 1.5, 0.5, 0.5, 0.5, 0.5, 2, 1.5, 1.5, 10, 0.5, 0.5, 1.5, 0.5, 1.5, 1.5,
    1.5, 4, 0.5, 0.5, 3, 3, 3, 10, 1.5, 1.5, 1.5, 1, 3, 3, 3, 3, 0.5, 1.5, 5, 5, 1.5, 1.5, 0.5,
    5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 3, 3, 3, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5,
    2.5, 2.5, 2.5, 2.5, 1.5, 5, 5, 1.5, 0.5, 0.5, 0.5, 0.5,
]

CSV_PATH = "exports/product_weights_prod.csv"
OUT_PATH = "scripts/apply_product_weights_user_list_shell.py"

pairs = []
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    for i, row in enumerate(csv.DictReader(f)):
        pairs.append((int(row["product_id"]), WEIGHTS[i]))

assert len(pairs) == len(WEIGHTS) == 115

lines = [
    '# -*- coding: utf-8 -*-',
    '"""Apply user weight_kg list (same order as exports/product_weights_prod.csv)."""',
    "DRY_RUN = True",
    "",
    "PAIRS = [",
]
for pid, w in pairs:
    lines.append(f"    ({pid}, {w}),")
lines.extend([
    "]",
    "",
    'Template = env["product.template"].sudo()',
    'print("=" * 72)',
    'print(f"apply_product_weights_user_list DRY_RUN={DRY_RUN} count={len(PAIRS)}")',
    "updated = 0",
    "for pid, w in PAIRS:",
    "    t = Template.browse(pid)",
    "    if not t.exists():",
    '        print(f"MISSING id={pid}")',
    "        continue",
    "    old = t.weight or 0",
    "    if old != w:",
    '        print(f"  id={pid} {old:g} -> {w:g} | {t.name[:55]}")',
    "        if not DRY_RUN:",
    '            t.write({"weight": w})',
    "        updated += 1",
    "if DRY_RUN:",
    '    print(f"Would update {updated} templates.")',
    "else:",
    "    env.cr.commit()",
    '    print(f"APPLIED {updated} templates.")',
    'print("Done.")',
    "",
])

with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines))

print(f"Wrote {OUT_PATH} with {len(pairs)} pairs")
