# -*- coding: utf-8 -*-
"""1.0.136 — Generation shop filter + no_variant spec attrs (fix filters & add-to-cart)."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Importer = env["product.csv.importer"]
    Attr = env["product.attribute"].sudo()

    for xid in (
        "quote_manage_ui.attr_brand",
        "quote_manage_ui.attr_series",
        "quote_manage_ui.attr_generation",
        "quote_manage_ui.attr_cpu",
        "quote_manage_ui.attr_ram",
        "quote_manage_ui.attr_storage",
        "quote_manage_ui.attr_touchscreen",
        "quote_manage_ui.attr_wan",
        "quote_manage_ui.attr_battery",
        "quote_manage_ui.attr_cmos",
    ):
        attr = env.ref(xid, raise_if_not_found=False)
        if attr and attr.create_variant != "no_variant":
            try:
                attr.write({"create_variant": "no_variant"})
            except Exception as exc:
                _logger.warning(
                    "1.0.136: skip create_variant on %s (%s)", xid, exc
                )

    gen_attr = env.ref("quote_manage_ui.attr_generation", raise_if_not_found=False)
    if not gen_attr:
        _logger.info("1.0.136: attr_generation missing; re-upload merge CSV after -u.")
        return

    PT = env["product.template"].sudo().with_context(active_test=False)
    backfilled = 0
    for tmpl in PT.search([("type", "=", "product"), ("active", "=", True)]):
        if tmpl.attribute_line_ids.filtered(
            lambda l: l.attribute_id == gen_attr
        ):
            continue
        gen = Importer._normalize_generation_label(product_name=tmpl.name)
        if not gen:
            continue
        val = env["product.attribute.value"].sudo().search(
            [("attribute_id", "=", gen_attr.id), ("name", "=ilike", gen)],
            limit=1,
        )
        if not val:
            val = env["product.attribute.value"].sudo().create(
                {"attribute_id": gen_attr.id, "name": gen[:128]}
            )
        env["product.template.attribute.line"].sudo().create(
            {
                "product_tmpl_id": tmpl.id,
                "attribute_id": gen_attr.id,
                "value_ids": [(6, 0, [val.id])],
            }
        )
        backfilled += 1

    _logger.info(
        "1.0.136: filter attrs → no_variant; backfilled Generation on %s product(s). "
        "Re-import merge CSV to refresh all attributes.",
        backfilled,
    )
