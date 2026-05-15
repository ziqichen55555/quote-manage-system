# -*- coding: utf-8 -*-
"""
Wipe sellable catalog for a clean re-import (DEV / test DB style).

Run in Odoo shell:
  exec(open("/mnt/custom-addons/quote_manage_ui/scripts/wipe_catalog_products.py").read())

1) Ensures a service placeholder product (delivery.carrier.product_id is NOT NULL).
2) Reassigns every delivery.carrier to that placeholder.
3) Removes all sale orders (ORM, savepoint per row).
4) Removes draft purchase orders if the module is installed.
5) Raw SQL clears stock history (moves, pickings, valuation, lots, scrap) and
   nulls account_move_line.product_id / account_move.stock_move_id — required
   because ORM unlink often skips done moves (234/234 skipped in practice).
6) Unlinks all product.template except the placeholder; on remaining FK issues,
   archives and renames default_code to __ZAP__...

WARNING: Destroys stock traceability and weakens accounting links on lines.
Do not use on production books.
"""
from __future__ import annotations


def _unlink_best_effort(env, model_name, domain):
    Model = env[model_name].sudo()
    recs = Model.search(domain)
    total = len(recs)
    ok = skipped = 0
    for rec in recs:
        try:
            with env.cr.savepoint():
                rec.unlink()
                ok += 1
        except Exception:  # noqa: BLE001
            skipped += 1
    return total, ok, skipped


def _sql_delete_all_sale_orders(cr):
    """ORM often cannot unlink confirmed SO; PostgreSQL cascades lines from sale_order."""
    errors = []
    for sql in ("DELETE FROM sale_order",):
        try:
            with cr.savepoint():
                cr.execute(sql)
        except Exception as exc:  # noqa: BLE001
            errors.append((sql, str(exc)[:240]))
    return errors


def _sql_dev_wipe_stock_and_accounting(cr):
    """Hard-delete stock rows and drop product_id on journal lines (dev only)."""
    statements = [
        "UPDATE account_move SET stock_move_id = NULL WHERE stock_move_id IS NOT NULL",
        "UPDATE account_move_line SET product_id = NULL WHERE product_id IS NOT NULL",
        "DELETE FROM stock_valuation_layer",
        "DELETE FROM stock_move_line",
        "UPDATE stock_move SET origin_returned_move_id = NULL, package_level_id = NULL",
        "DELETE FROM stock_move",
        "DELETE FROM stock_package_level",
        "UPDATE stock_picking SET backorder_id = NULL, return_id = NULL, sale_id = NULL",
        "DELETE FROM stock_scrap",
        "DELETE FROM stock_return_picking_line",
        "DELETE FROM stock_quant",
        "DELETE FROM stock_lot",
        "DELETE FROM stock_picking",
    ]
    errors = []
    for sql in statements:
        try:
            with cr.savepoint():
                cr.execute(sql)
        except Exception as exc:  # noqa: BLE001
            errors.append((sql[:72], str(exc)[:240]))
    return errors


def wipe_catalog(env):
    cr = env.cr
    report = {
        "placeholder_template_id": None,
        "delivery_carriers_updated": 0,
        "sale_orders": (0, 0, 0),
        "draft_purchase_orders": 0,
        "sale_order_sql_errors": [],
        "sql_stock_errors": [],
        "pickings": (0, 0, 0),
        "quants": (0, 0, 0),
        "move_lines": (0, 0, 0),
        "moves": (0, 0, 0),
        "templates_unlinked": 0,
        "templates_zapped": 0,
    }

    PT = env["product.template"].with_context(active_test=False).sudo()
    ph = PT.search([("default_code", "=", "__WIPE_PLACEHOLDER__")], limit=1)
    if not ph:
        ph = PT.create(
            {
                "name": "Catalog wipe placeholder (delivery carriers)",
                "default_code": "__WIPE_PLACEHOLDER__",
                "type": "service",
                "sale_ok": False,
                "purchase_ok": False,
                "active": False,
            }
        )
    report["placeholder_template_id"] = ph.id
    ph_variant_id = ph.product_variant_id.id

    if "delivery.carrier" in env:
        carriers = env["delivery.carrier"].sudo().search([])
        report["delivery_carriers_updated"] = len(carriers)
        if carriers:
            carriers.write({"product_id": ph_variant_id})

    report["sale_orders"] = _unlink_best_effort(env, "sale.order", [])
    report["sale_order_sql_errors"] = _sql_delete_all_sale_orders(cr)

    if "purchase.order" in env:
        PO = env["purchase.order"].sudo()
        pod = PO.search([("state", "=", "draft")])
        report["draft_purchase_orders"] = len(pod)
        if pod:
            pod.unlink()

    report["sql_stock_errors"] = _sql_dev_wipe_stock_and_accounting(cr)
    # Clear anything SQL could not remove (permissions / extra modules).
    if "stock.picking" in env:
        SP = env["stock.picking"].sudo().search([])
        report["pickings"] = _unlink_best_effort(env, "stock.picking", [("id", "in", SP.ids)])
    if "stock.quant" in env:
        q = env["stock.quant"].sudo().search([])
        report["quants"] = _unlink_best_effort(env, "stock.quant", [("id", "in", q.ids)])
    if "stock.move.line" in env:
        sml = env["stock.move.line"].sudo().search([])
        report["move_lines"] = _unlink_best_effort(env, "stock.move.line", [("id", "in", sml.ids)])
    if "stock.move" in env:
        sm = env["stock.move"].sudo().search([])
        report["moves"] = _unlink_best_effort(env, "stock.move", [("id", "in", sm.ids)])

    tmpls = PT.search([("id", "!=", ph.id)])
    for t in tmpls:
        try:
            with cr.savepoint():
                t.unlink()
                report["templates_unlinked"] += 1
        except Exception:  # noqa: BLE001
            code = t.default_code or ""
            with cr.savepoint():
                t.sudo().write(
                    {
                        "active": False,
                        "website_published": False,
                        "sale_ok": False,
                        "default_code": f"__ZAP__{t.id}__{code}"[:80],
                    }
                )
                report["templates_zapped"] += 1

    env.cr.commit()
    return report


result = wipe_catalog(env)
print(result)
