#!/usr/bin/env python3
"""Find products that share the same name and could reuse each other's images.

Groups active sale_ok product templates by exact product name (case-insensitive).
Reports groups where at least one record has a main image and at least one does not.

Usage:
  # Offline — analyse a catalog snapshot JSON (default: newest backups/prod_product_snapshot*.json)
  python scripts/find_same_name_image_donors.py
  python scripts/find_same_name_image_donors.py backups/prod_product_snapshot_live_20260701.json

  # Live — query Odoo through docker (requires quote-manage-system-web-1)
  python scripts/find_same_name_image_donors.py --live
  python scripts/find_same_name_image_donors.py --live --all   # include inactive / not sale_ok
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUPS = ROOT / "backups"
REPORT_DIR = ROOT / "scripts" / "_reports"
CONTAINER = "quote-manage-system-web-1"
DB_NAME = "cocreativeit-quote"

LIVE_SHELL = r"""
import json
PT = env["product.template"].sudo().with_context(active_test=False)
domain = []
if not __ALL__:
    domain = [("sale_ok", "=", True), ("active", "=", True)]
rows = []
for t in PT.search(domain, order="name, default_code"):
    rows.append({
        "id": t.id,
        "code": (t.default_code or "").strip(),
        "name": (t.name or "").strip(),
        "main_image": bool(t.image_1920),
        "extra_images": len(t.product_template_image_ids),
        "published": bool(t.website_published),
        "active": bool(t.active),
        "sale_ok": bool(t.sale_ok),
        "on_hand": float(t.qty_available or 0),
    })
print(json.dumps(rows, ensure_ascii=False))
"""


def newest_snapshot() -> Path | None:
    candidates = sorted(BACKUPS.glob("prod_product_snapshot*.json"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def norm_name(name: str) -> str:
    return (name or "").strip().casefold()


def has_image(p: dict) -> bool:
    return bool(p.get("main_image")) or int(p.get("extra_images") or 0) > 0


def load_snapshot(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "products" in data:
        meta = {k: data[k] for k in ("exported_at", "database", "product_count") if k in data}
        print(f"Snapshot: {path.name}")
        for k, v in meta.items():
            print(f"  {k}: {v}")
        print()
        return data["products"]
    if isinstance(data, list):
        print(f"Snapshot: {path.name} ({len(data)} rows)")
        print()
        return data
    raise SystemExit(f"Unrecognised snapshot format: {path}")


def load_live(all_products: bool) -> list[dict]:
    script = LIVE_SHELL.replace("__ALL__", "True" if all_products else "False")
    proc = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "odoo", "shell", "-d", DB_NAME, "--no-http"],
        input=script,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        raise SystemExit(f"odoo shell failed (exit {proc.returncode})")
    # odoo may log to stdout before the JSON line
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("["):
            return json.loads(line)
    raise SystemExit("Could not parse odoo shell output as JSON")


def analyse(products: list[dict], sale_ok_only: bool = True) -> dict:
    filtered = []
    for p in products:
        if sale_ok_only and not (p.get("sale_ok", True) and p.get("active", True)):
            continue
        name = (p.get("name") or "").strip()
        if not name:
            continue
        filtered.append(p)

    by_name: dict[str, list[dict]] = defaultdict(list)
    for p in filtered:
        by_name[norm_name(p["name"])].append(p)

    # groups: same name, mixed image status
    shareable = []
    all_same_name_multi = []
    no_image_no_donor = []

    for key, items in sorted(by_name.items(), key=lambda kv: kv[1][0]["name"].lower()):
        if len(items) < 2:
            continue
        with_img = [p for p in items if has_image(p)]
        without_img = [p for p in items if not has_image(p)]
        display_name = items[0]["name"]
        all_same_name_multi.append({"name": display_name, "count": len(items), "with_image": len(with_img)})

        if with_img and without_img:
            donors = sorted(with_img, key=lambda p: (not p.get("main_image"), -int(p.get("extra_images") or 0)))
            best = donors[0]
            shareable.append({
                "name": display_name,
                "donor_count": len(with_img),
                "target_count": len(without_img),
                "donor_codes": [p.get("code") or f"id:{p.get('id')}" for p in with_img],
                "target_codes": [p.get("code") or f"id:{p.get('id')}" for p in without_img],
                "best_donor": best.get("code") or f"id:{best.get('id')}",
                "best_donor_id": best.get("id"),
                "targets": without_img,
            })
        elif not with_img and len(without_img) >= 2:
            no_image_no_donor.append({
                "name": display_name,
                "count": len(items),
                "codes": [p.get("code") or f"id:{p.get('id')}" for p in items],
            })

    missing_image = [p for p in filtered if not has_image(p)]
    with_image = [p for p in filtered if has_image(p)]

    return {
        "total": len(filtered),
        "with_image": len(with_image),
        "without_image": len(missing_image),
        "duplicate_names": len(all_same_name_multi),
        "shareable_groups": shareable,
        "same_name_all_no_image": no_image_no_donor,
    }


def print_report(result: dict) -> None:
    print("=== Same-name image donor analysis ===\n")
    print(f"Products analysed       : {result['total']}")
    print(f"  with image            : {result['with_image']}")
    print(f"  without image         : {result['without_image']}")
    print(f"Duplicate name groups   : {result['duplicate_names']}")
    print(f"Can share image (name)  : {len(result['shareable_groups'])}")
    print(f"Same name, all no image : {len(result['same_name_all_no_image'])}")
    print()

    if result["shareable_groups"]:
        print("--- Groups: same name, some have image -> can copy ---\n")
        for g in result["shareable_groups"]:
            print(f"  {g['name']}")
            print(f"    donor ({g['donor_count']}): {', '.join(g['donor_codes'])}")
            print(f"    need image ({g['target_count']}): {', '.join(g['target_codes'])}")
            print(f"    suggested donor: {g['best_donor']}")
            print()

    if result["same_name_all_no_image"]:
        print("--- Same name but NO product in group has an image ---\n")
        for g in result["same_name_all_no_image"][:30]:
            print(f"  {g['name']} ({g['count']}): {', '.join(g['codes'][:6])}")
        if len(result["same_name_all_no_image"]) > 30:
            print(f"  ... and {len(result['same_name_all_no_image']) - 30} more")
        print()

    # targets that still have no image and no same-name donor
    covered = {norm_name(g["name"]) for g in result["shareable_groups"]}
    orphan_names = set()
    for g in result["same_name_all_no_image"]:
        orphan_names.add(norm_name(g["name"]))
    print("--- Image-less products with no same-name donor ---")
    print("(These need MTM match, manual upload, or a differently named donor)\n")
    # re-derive from shareable target lists only for summary count
    fixable_targets = sum(g["target_count"] for g in result["shareable_groups"])
    print(f"Fixable via same-name copy : {fixable_targets} product(s)")
    print(f"Same-name but all no image : {sum(g['count'] for g in result['same_name_all_no_image'])} product(s)")


def write_csv(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "product_name",
                "target_code",
                "target_id",
                "donor_code",
                "donor_id",
                "donor_count_in_group",
            ],
        )
        w.writeheader()
        for g in result["shareable_groups"]:
            for tgt in g["targets"]:
                w.writerow({
                    "product_name": g["name"],
                    "target_code": tgt.get("code") or "",
                    "target_id": tgt.get("id") or "",
                    "donor_code": g["best_donor"],
                    "donor_id": g["best_donor_id"] or "",
                    "donor_count_in_group": g["donor_count"],
                })
    print(f"\nCSV written: {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snapshot", nargs="?", help="Path to prod_product_snapshot JSON (offline mode)")
    ap.add_argument("--live", action="store_true", help="Query live Odoo via docker instead of snapshot")
    ap.add_argument("--all", action="store_true", help="Include inactive / not sale_ok (live mode only)")
    ap.add_argument("--csv", metavar="PATH", help="Write shareable pairs to CSV")
    args = ap.parse_args()

    if args.live:
        products = load_live(args.all)
        sale_ok_only = not args.all
    else:
        snap = Path(args.snapshot) if args.snapshot else newest_snapshot()
        if not snap or not snap.exists():
            raise SystemExit("No snapshot found under backups/. Run export or use --live.")
        products = load_snapshot(snap)
        sale_ok_only = True

    result = analyse(products, sale_ok_only=sale_ok_only)
    print_report(result)

    csv_path = Path(args.csv) if args.csv else REPORT_DIR / "same_name_image_donors.csv"
    if result["shareable_groups"]:
        write_csv(result, csv_path)


if __name__ == "__main__":
    main()
