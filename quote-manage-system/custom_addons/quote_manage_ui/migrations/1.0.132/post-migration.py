# -*- coding: utf-8 -*-
"""1.0.132 — Only CMOS Successful on shop; CMOS SKU split (-CMOSP/-CMOSFL)."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    attr = env.ref("quote_manage_ui.attr_cmos", raise_if_not_found=False)
    if not attr:
        _logger.info("1.0.132: attr_cmos missing; skip shop unpublish.")
        return

    failed_val = env["product.attribute.value"].search(
        [("attribute_id", "=", attr.id), ("name", "=", "Failed")], limit=1
    )
    if not failed_val:
        _logger.info("1.0.132: CMOS Failed value missing; skip.")
        return

    PT = env["product.template"].sudo().with_context(active_test=False)
    tmpl_ids = set(
        PT.search(
            [
                (
                    "attribute_line_ids.value_ids.product_attribute_value_id",
                    "=",
                    failed_val.id,
                ),
            ]
        ).ids
    )
    tmpl_ids.update(
        PT.search([("default_code", "=ilike", "%-CMOSFL")]).ids
    )

    if not tmpl_ids:
        _logger.info("1.0.132: no CMOS Failed products to unpublish.")
        return

    PT.browse(list(tmpl_ids)).write(
        {"website_published": False, "sale_ok": False}
    )
    _logger.info(
        "1.0.132: held %s CMOS Failed product(s) off the shop.",
        len(tmpl_ids),
    )
