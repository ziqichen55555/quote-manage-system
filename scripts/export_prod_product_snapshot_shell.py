# -*- coding: utf-8 -*-
"""Full production product snapshot before fresh SN laptop import.

Exports sale_ok products with price, image flags, attributes, and serial lots.
Run via SSH pipe to odoo shell on production.

Usage (PowerShell):
  Get-Content scripts/export_prod_product_snapshot_shell.py -Raw |
    ssh -i $env:USERPROFILE\\.ssh\\id_ed25519_do root@134.199.145.67 `
    "docker compose -f /root/reware/docker-compose.yml run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init" `
    > backups/prod_product_snapshot_YYYYMMDD.json
"""
import json
from datetime import datetime

ATTR_MAP = {
    "Brand": "brand",
    "Series": "series",
    "CPU": "cpu",
    "RAM": "ram",
    "Storage": "storage",
    "Touchscreen": "touch",
    "WAN": "wan",
}


def _specs(tmpl):
    out = {}
    for line in tmpl.attribute_line_ids:
        key = ATTR_MAP.get(line.attribute_id.name)
        if key and line.value_ids:
            out[key] = line.value_ids[0].name
    return out


def _serials_for_template(tmpl):
    """On-hand serial lot names per variant."""
    serials = []
    wh = env["stock.warehouse"].search(
        [("company_id", "=", env.company.id)], limit=1
    )
    if not wh:
        return serials
    Quant = env["stock.quant"].sudo()
    for variant in tmpl.product_variant_ids.filtered(lambda v: v.active):
        quants = Quant.search(
            [
                ("product_id", "=", variant.id),
                ("location_id", "child_of", wh.lot_stock_id.id),
                ("quantity", ">", 0),
                ("lot_id", "!=", False),
            ]
        )
        for q in quants:
            serials.append(
                {
                    "serial": q.lot_id.name,
                    "qty": float(q.quantity),
                    "variant_code": (variant.default_code or "").strip(),
                }
            )
    return serials


PT = env["product.template"].sudo().with_context(active_test=False)
Attachment = env["ir.attachment"].sudo()

products = []
serial_laptop_count = 0
for t in PT.search([("sale_ok", "=", True)]):
    code = (t.default_code or "").strip()
    specs = _specs(t)
    serials = _serials_for_template(t) if t.tracking == "serial" else []
    is_serial_refurb = t.tracking == "serial" and t.type == "product"
    if is_serial_refurb and serials:
        serial_laptop_count += 1
    imgs_extra = Attachment.search_count(
        [
            ("res_model", "=", "product.template"),
            ("res_id", "=", t.id),
            ("mimetype", "like", "image/%"),
        ]
    )
    products.append(
        {
            "id": t.id,
            "code": code,
            "name": t.name or "",
            "price": float(t.list_price or 0),
            "standard_price": float(t.standard_price or 0),
            "type": t.type,
            "tracking": t.tracking,
            "on_hand": float(t.qty_available or 0),
            "published": bool(t.website_published),
            "active": bool(t.active),
            "main_image": bool(t.image_1920),
            "extra_images": imgs_extra,
            "categ": t.categ_id.name if t.categ_id else "",
            "public_cats": ",".join(t.public_categ_ids.mapped("name")),
            "specs": specs,
            "serials": serials,
            "serial_count": len(serials),
        }
    )

products.sort(key=lambda r: (r["public_cats"], r["code"], r["name"]))

snapshot = {
    "exported_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "database": env.cr.dbname,
    "product_count": len(products),
    "serial_refurb_with_stock": serial_laptop_count,
    "products": products,
}

print(json.dumps(snapshot, ensure_ascii=False, indent=2))
