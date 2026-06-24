# -*- coding: utf-8 -*-
"""Odoo shell: upload Sales Pictures or copy images between SKUs.

On the server (pictures copied to /tmp/sales-pictures):
  SALES_PICTURES_DIR=/tmp/sales-pictures python3 ...

From repo via docker:
  docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote <<'PY'
  exec(open("/mnt/extra-addons/../tools/sales_pictures_shell.py").read())
  PY

Or paste run_upload() calls below.
"""
import base64
from pathlib import Path

PICTURES = Path(__import__("os").environ.get("SALES_PICTURES_DIR", r"D:\Sales Pictures"))


def run_copy(source: str, *targets: str, overwrite=True):
    PT = env["product.template"]
    out = PT.quote_copy_product_images(source, list(targets), overwrite=overwrite)
    env.cr.commit()
    print(out)
    return out


def run_upload_sku(sku: str, filenames: list, pictures_dir=None, overwrite=True):
    """Upload explicit filenames for one SKU."""
    root = Path(pictures_dir or PICTURES)
    tmpl = env["product.template"].sudo().search(
        [("default_code", "=ilike", sku.strip())], limit=1
    )
    if not tmpl:
        print(f"SKU not found: {sku}")
        return
    index = {p.name.casefold(): p for p in root.iterdir() if p.is_file()}
    paths = [index[n.casefold()] for n in filenames if n.casefold() in index]
    if not paths:
        print(f"No files for {sku} in {root}")
        return
    if overwrite:
        tmpl.product_template_image_ids.unlink()
    main = paths[0].read_bytes()
    tmpl.image_1920 = base64.b64encode(main)
    Image = env["product.image"].sudo()
    for extra in paths[1:]:
        Image.create(
            {
                "name": extra.name,
                "product_tmpl_id": tmpl.id,
                "image_1920": base64.b64encode(extra.read_bytes()),
            }
        )
    env.cr.commit()
    print(f"Uploaded {sku}: {[p.name for p in paths]}")


# T14s Gen 1 — fix thumbnail; share photos across both MTMs.
run_upload_sku("20T0003UAU", ["t14s.jpg", "t14s side.jpg"])
run_upload_sku("20T1S6C300", ["t14s.jpg", "t14s side.jpg"])
