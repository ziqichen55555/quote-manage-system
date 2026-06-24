#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload product images from the Co-Creative USB folder ``Sales Pictures``.

The pictures live on the local U盘 (removable drive), usually:
  D:\\Sales Pictures   (volume label often "PRINTER" — drive letter may vary)

Examples (PowerShell):
  # Preview T14s Gen 1 mapping — skips 99px PNG thumbnails
  python tools/upload_sales_pictures.py --dry-run --sku 20T1S6C300

  # Upload both Gen-1 T14s SKUs from warehouse photos
  python tools/upload_sales_pictures.py --sku 20T0003UAU --sku 20T1S6C300

  # Copy images already on 20T0003UAU → 20T1S6C300 (no local files)
  python tools/upload_sales_pictures.py --copy-from 20T0003UAU --to 20T1S6C300

  # Apply full manifest for all mapped SKUs
  python tools/upload_sales_pictures.py --apply-manifest

Environment:
  ODOO_URL      default https://www.reware-project.com
  ODOO_DB       default cocreativeit-quote
  ODOO_USER     Odoo login (admin or API user)
  ODOO_PASSWORD Odoo password
  SALES_PICTURES_DIR  override auto-detect (U盘上的 Sales Pictures 文件夹)

Requires: pip install pillow (optional but recommended for size checks)
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import xmlrpc.client
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sales_pictures_upload import (  # noqa: E402
    DEFAULT_SALES_PICTURES_DIR,
    SKU_FILE_MANIFEST,
    find_sales_pictures_dir,
    image_quality_ok,
    load_sku_images,
    manifest_for_sku,
    scan_suggestions,
)


def odoo_client():
    url = os.environ.get("ODOO_URL", "https://www.reware-project.com").rstrip("/")
    db = os.environ.get("ODOO_DB", "cocreativeit-quote")
    user = os.environ.get("ODOO_USER") or os.environ.get("ODOO_LOGIN")
    password = os.environ.get("ODOO_PASSWORD")
    if not user or not password:
        print(
            "Set ODOO_USER and ODOO_PASSWORD (or ODOO_LOGIN) for XML-RPC upload.",
            file=sys.stderr,
        )
        sys.exit(1)
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
    uid = common.authenticate(db, user, password, {})
    if not uid:
        print("Odoo authentication failed.", file=sys.stderr)
        sys.exit(1)
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
    return db, uid, password, models


def find_template(models, db, uid, password, sku: str) -> int | None:
    code = sku.strip()
    ids = models.execute_kw(
        db,
        uid,
        password,
        "product.template",
        "search",
        [[("default_code", "=ilike", code)]],
        {"limit": 1},
    )
    if ids:
        return ids[0]
    ids = models.execute_kw(
        db,
        uid,
        password,
        "product.template",
        "search",
        [[("default_code", "=", code)]],
        {"limit": 1},
    )
    return ids[0] if ids else None


def upload_files_to_template(
    models,
    db,
    uid,
    password,
    tmpl_id: int,
    paths: list[Path],
    *,
    overwrite: bool,
    dry_run: bool,
) -> dict:
    if not paths:
        return {"status": "no_files"}
    main_path = paths[0]
    gallery = paths[1:]
    main_data = main_path.read_bytes()
    ok, reason = image_quality_ok(main_path, main_data)
    if not ok:
        return {"status": "rejected_main", "reason": reason, "file": main_path.name}

    if dry_run:
        return {
            "status": "dry_run",
            "main": main_path.name,
            "gallery": [p.name for p in gallery],
        }

    if overwrite:
        gallery_ids = models.execute_kw(
            db,
            uid,
            password,
            "product.image",
            "search",
            [[("product_tmpl_id", "=", tmpl_id)]],
        )
        if gallery_ids:
            models.execute_kw(
                db, uid, password, "product.image", "unlink", [gallery_ids]
            )

    models.execute_kw(
        db,
        uid,
        password,
        "product.template",
        "write",
        [[tmpl_id], {"image_1920": base64.b64encode(main_data).decode("ascii")}],
    )
    for extra in gallery:
        data = extra.read_bytes()
        ok_g, _ = image_quality_ok(extra, data)
        if not ok_g:
            continue
        models.execute_kw(
            db,
            uid,
            password,
            "product.image",
            "create",
            [
                {
                    "name": extra.name,
                    "product_tmpl_id": tmpl_id,
                    "image_1920": base64.b64encode(data).decode("ascii"),
                }
            ],
        )
    return {
        "status": "uploaded",
        "main": main_path.name,
        "gallery": [p.name for p in gallery],
    }


def copy_images_between_skus(
    models,
    db,
    uid,
    password,
    source_sku: str,
    target_skus: list[str],
    *,
    overwrite: bool,
    dry_run: bool,
) -> list[dict]:
    src_id = find_template(models, db, uid, password, source_sku)
    if not src_id:
        return [{"sku": source_sku, "status": "source_not_found"}]

    src = models.execute_kw(
        db,
        uid,
        password,
        "product.template",
        "read",
        [[src_id], ["image_1920", "product_template_image_ids"]],
    )[0]
    main_b64 = src.get("image_1920")
    gallery_ids = src.get("product_template_image_ids") or []
    gallery_rows = []
    if gallery_ids:
        gallery_rows = models.execute_kw(
            db,
            uid,
            password,
            "product.image",
            "read",
            [gallery_ids, ["name", "image_1920"]],
        )

    results = []
    for target_sku in target_skus:
        tgt_id = find_template(models, db, uid, password, target_sku)
        if not tgt_id:
            results.append({"sku": target_sku, "status": "not_found"})
            continue
        if dry_run:
            results.append(
                {
                    "sku": target_sku,
                    "status": "dry_run_copy",
                    "from": source_sku,
                    "gallery": len(gallery_rows),
                }
            )
            continue
        if overwrite:
            old_ids = models.execute_kw(
                db,
                uid,
                password,
                "product.image",
                "search",
                [[("product_tmpl_id", "=", tgt_id)]],
            )
            if old_ids:
                models.execute_kw(
                    db, uid, password, "product.image", "unlink", [old_ids]
                )
        if main_b64:
            models.execute_kw(
                db,
                uid,
                password,
                "product.template",
                "write",
                [[tgt_id], {"image_1920": main_b64}],
            )
        for row in gallery_rows:
            if not row.get("image_1920"):
                continue
            models.execute_kw(
                db,
                uid,
                password,
                "product.image",
                "create",
                [
                    {
                        "name": row.get("name") or "gallery",
                        "product_tmpl_id": tgt_id,
                        "image_1920": row["image_1920"],
                    }
                ],
            )
        results.append(
            {
                "sku": target_sku,
                "status": "copied",
                "from": source_sku,
                "gallery": len(gallery_rows),
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Sales Pictures to Odoo products")
    parser.add_argument(
        "--pictures-dir",
        type=Path,
        default=None,
        help="U盘 Sales Pictures folder (auto-detected if omitted)",
    )
    parser.add_argument("--sku", action="append", dest="skus", help="Product default_code / MTM")
    parser.add_argument("--apply-manifest", action="store_true", help="All SKUs in manifest")
    parser.add_argument("--copy-from", metavar="SKU", help="Copy images from this SKU in Odoo")
    parser.add_argument("--to", action="append", dest="copy_targets", help="Target SKU(s) for --copy-from")
    parser.add_argument("--overwrite", action="store_true", default=True)
    parser.add_argument("--no-overwrite", action="store_false", dest="overwrite")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scan", action="store_true", help="List files in pictures dir with quality flags")
    args = parser.parse_args()
    pictures_dir = args.pictures_dir or find_sales_pictures_dir()
    if not pictures_dir.is_dir():
        print(f"Sales Pictures folder not found: {pictures_dir}", file=sys.stderr)
        print("Plug in the U盘 or set SALES_PICTURES_DIR.", file=sys.stderr)
        return 1
    if not args.pictures_dir and not os.environ.get("SALES_PICTURES_DIR"):
        print(f"Using pictures dir: {pictures_dir}")

    if args.scan:
        for row in scan_suggestions(pictures_dir):
            flag = "OK" if row["usable"] else "SKIP"
            print(f"[{flag}] {row['file']:40} {row['dims']:>12}  {row['note']}")
        return 0

    skus = list(args.skus or [])
    if args.apply_manifest:
        skus.extend(SKU_FILE_MANIFEST.keys())
    skus = sorted({s.strip().upper() for s in skus if s and s.strip()})

    if args.copy_from:
        targets = args.copy_targets or []
        if not targets:
            print("--copy-from requires at least one --to SKU", file=sys.stderr)
            return 1
        db, uid, password, models = odoo_client()
        for row in copy_images_between_skus(
            models,
            db,
            uid,
            password,
            args.copy_from,
            targets,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        ):
            print(row)
        return 0

    if not skus:
        parser.print_help()
        return 1

    db, uid, password, models = odoo_client()
    for sku in skus:
        paths = load_sku_images(pictures_dir, sku)
        manifest_names = manifest_for_sku(sku)
        tmpl_id = find_template(models, db, uid, password, sku)
        if not tmpl_id:
            print({"sku": sku, "status": "product_not_found"})
            continue
        if not paths:
            print(
                {
                    "sku": sku,
                    "status": "no_usable_files",
                    "wanted": manifest_names,
                }
            )
            continue
        result = upload_files_to_template(
            models,
            db,
            uid,
            password,
            tmpl_id,
            paths,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        print({"sku": sku, "tmpl_id": tmpl_id, **result})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
