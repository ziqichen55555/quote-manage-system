# -*- coding: utf-8 -*-
"""1.0.104 — Reactivate archived per-MTM variants; repair bad storage attrs from CPU parse."""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]
    PT = env["product.template"].sudo().with_context(active_test=False)
    PP = env["product.product"].sudo().with_context(active_test=False)

    fixed_variants = 0
    for tmpl in PT.search([("default_code", "!=", False)]):
        variants = tmpl.product_variant_ids
        if variants.filtered(lambda v: v.active):
            continue
        code = (tmpl.default_code or "").strip()
        match = variants.filtered(lambda v: (v.default_code or "").strip() == code)
        to_activate = match or (variants if len(variants) == 1 else variants[:1])
        if to_activate:
            to_activate.write({"active": True, "sale_ok": True})
            fixed_variants += len(to_activate)

    repaired_attrs = 0
    for tmpl in PT.search([("default_code", "!=", False)]):
        titles = [tmpl.name or "", tmpl.description_sale or ""]
        brand = ""
        for line in tmpl.attribute_line_ids:
            if line.attribute_id.name == "Brand" and line.value_ids:
                brand = line.value_ids[0].name
                break
        specs = Importer._parse_specs(brand, titles)
        storage = (specs.get("storage") or "").lower()
        if storage and "1145gb" not in storage:
            Importer._sync_template_attributes(
                tmpl,
                brand=brand,
                titles=titles,
                ptype=tmpl.type,
                specs=specs,
            )
            repaired_attrs += 1

    cr.commit()
