# -*- coding: utf-8 -*-
"""1.0.78 — Repair GST and apply it to all sellable products.

Background
----------
Two data problems made website orders show ``Taxes $0.00``:

1. The sale tax that was meant to be GST 10% was saved with **Amount = 0**
   (a "10%" placeholder), so every line computed $0.
2. Products created by ``scripts/import_product_csv.py`` were saved without any
   ``taxes_id`` (Customer Taxes) at all.

What this migration does (per company), idempotently
----------------------------------------------------
1. Picks the canonical GST tax:
      a. the company's default sale tax, else
      b. any active sale tax with Amount == 10, else
      c. a sale tax whose name contains "10" (the placeholder) to repair.
2. Forces it to Amount = 10, Sales scope, active, and (re)names it "GST 10%".
3. Sets it as the company's default sale tax (so new products inherit it).
4. Applies it to every saleable product (replacing any wrong/empty tax).
5. Archives leftover sale taxes that are now unused (no products, not a default)
   — conservative: taxes still attached to products are left untouched.

Confirmed orders keep their stored line taxes (Odoo freezes those at order
time); only new orders pick up the corrected tax.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

LOG = "quote_manage_ui 1.0.78"


def _pick_gst_tax(env, company):
    Tax = env["account.tax"].sudo().with_company(company)
    # 1. Respect an explicit default that is already a real 10% tax.
    default = company.account_sale_tax_id
    if default and default.amount == 10.0:
        return default
    # 2. Prefer a proper, already-correct GST 10% (e.g. the l10n_au "GST").
    gst = Tax.search(
        [
            ("type_tax_use", "=", "sale"),
            ("amount", "=", 10.0),
            ("name", "ilike", "gst"),
            ("active", "=", True),
        ],
        limit=1,
    )
    if gst:
        return gst
    # 3. Any active 10% sale tax.
    ten = Tax.search(
        [("type_tax_use", "=", "sale"), ("amount", "=", 10.0), ("active", "=", True)],
        limit=1,
    )
    if ten:
        return ten
    # 4. Fall back to the (broken) default, or a "10"-named placeholder, to repair.
    if default:
        return default
    like_ten = Tax.search(
        [("type_tax_use", "=", "sale"), ("name", "ilike", "10")],
        limit=1,
    )
    return like_ten or Tax.browse()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    for company in env["res.company"].sudo().search([]):
        gst = _pick_gst_tax(env, company)
        if not gst:
            _logger.warning(
                "%s: company %s has no usable GST sale tax to repair; skipping.",
                LOG, company.name,
            )
            continue

        vals = {"type_tax_use": "sale", "active": True}
        if gst.amount != 10.0:
            vals["amount"] = 10.0
        # Only rename a generic placeholder; keep a proper "GST" name as-is.
        if "gst" not in (gst.name or "").lower():
            vals["name"] = "GST 10%"
        gst.write(vals)

        if company.account_sale_tax_id.id != gst.id:
            company.sudo().account_sale_tax_id = gst.id

        products = env["product.template"].with_company(company).sudo().search(
            [("sale_ok", "=", True)]
        )
        to_fix = products.filtered(lambda p: p.taxes_id.ids != gst.ids)
        if to_fix:
            to_fix.write({"taxes_id": [(6, 0, gst.ids)]})
        _logger.info(
            "%s: company %s -> tax '%s' (amount %s); products updated: %s/%s",
            LOG, company.name, gst.display_name, gst.amount, len(to_fix), len(products),
        )

        default_ids = env["res.company"].sudo().search([]).mapped("account_sale_tax_id").ids
        leftover = env["account.tax"].sudo().with_company(company).search([
            ("type_tax_use", "=", "sale"),
            ("active", "=", True),
            ("id", "not in", list(set(default_ids) | {gst.id})),
        ])
        unused = leftover.filtered(
            lambda t: not env["product.template"].sudo().with_context(
                active_test=False
            ).search_count([("taxes_id", "in", t.id)])
        )
        if unused:
            unused.write({"active": False})
            _logger.info("%s: archived unused sale taxes %s", LOG, unused.ids)
