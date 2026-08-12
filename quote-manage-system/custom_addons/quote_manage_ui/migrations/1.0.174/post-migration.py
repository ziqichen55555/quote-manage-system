# -*- coding: utf-8 -*-
"""1.0.174 — Remove leftover Square views after incomplete sale_square_terminal uninstall.

Production OwlError: sale.order.square_pay_enabled field is undefined — the
module was marked uninstalled without deleting its inherited form views.
"""

from odoo import SUPERUSER_ID, api


_SQUARE_ARCH_MARKERS = (
    "square_pay_enabled",
    "action_square_pay",
    "action_square_refund",
    "square_payment_id",
    "square_checkout_id",
    "square_refund_id",
    "square_enabled",
    "square_payment_mode",
    "square_access_token",
    "square_application_id",
    "square_location_id",
    "square_device_id",
    "square_mobile_api_key",
    "square_journal_id",
    "square_webhook",
    "square_terminal_setting",
    "square.terminal.pay.wizard",
    "square.refund.wizard",
    "Pay with Square",
    "Refund via Square",
    "Square Card Payments",
)


def _unlink_records(env, model_name, ids):
    if not ids:
        return
    Model = env[model_name].sudo()
    records = Model.browse(list(ids)).exists()
    if records:
        records.unlink()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Data = env["ir.model.data"].sudo()
    View = env["ir.ui.view"].sudo()

    # 1) Delete everything still registered under sale_square_terminal xmlids.
    xmlids = Data.search([("module", "=", "sale_square_terminal")])
    by_model = {}
    for xid in xmlids:
        by_model.setdefault(xid.model, set()).add(xid.res_id)

    # Views first (breaks form inheritance), then the rest.
    preferred_order = [
        "ir.ui.view",
        "ir.actions.act_window",
        "ir.model.access",
        "account.payment.method",
        "account.payment.method.line",
    ]
    seen = set()
    for model_name in preferred_order + sorted(by_model.keys()):
        if model_name in seen or model_name not in by_model:
            continue
        seen.add(model_name)
        try:
            _unlink_records(env, model_name, by_model[model_name])
        except Exception:
            # Model may already be gone; still drop the xmlids below.
            pass

    xmlids.unlink()

    # 2) Catch COW / orphan views that still reference Square fields in arch.
    domain = ["|"] * (len(_SQUARE_ARCH_MARKERS) - 1)
    domain.extend(("arch_db", "ilike", marker) for marker in _SQUARE_ARCH_MARKERS)
    orphan_views = View.search(domain)
    if orphan_views:
        orphan_views.unlink()

    # 3) Ensure module row is not left as installed.
    module = env["ir.module.module"].sudo().search(
        [("name", "=", "sale_square_terminal")], limit=1
    )
    if module and module.state in ("installed", "to upgrade", "to remove"):
        module.write({"state": "uninstalled"})
