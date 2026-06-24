# -*- coding: utf-8 -*-
"""Export sale_ok products from production for price/image audit."""
import json

PT = env["product.template"].sudo().with_context(active_test=False)
Attachment = env["ir.attachment"].sudo()
rows = []
for t in PT.search([("sale_ok", "=", True)]):
    code = (t.default_code or "").strip()
    imgs_extra = Attachment.search_count(
        [
            ("res_model", "=", "product.template"),
            ("res_id", "=", t.id),
            ("mimetype", "like", "image/%"),
        ]
    )
    rows.append(
        {
            "code": code,
            "name": (t.name or "")[:120],
            "price": float(t.list_price or 0),
            "type": t.type,
            "tracking": t.tracking,
            "on_hand": float(t.qty_available or 0),
            "published": bool(t.website_published),
            "active": bool(t.active),
            "main_image": bool(t.image_1920),
            "extra_images": imgs_extra,
            "categ": t.categ_id.name if t.categ_id else "",
            "public_cats": ",".join(t.public_categ_ids.mapped("name")),
        }
    )
rows.sort(key=lambda r: (r["public_cats"], r["code"]))
print(json.dumps(rows, ensure_ascii=False))
