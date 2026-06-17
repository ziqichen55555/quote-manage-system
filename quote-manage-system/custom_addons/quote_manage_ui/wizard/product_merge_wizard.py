# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ProductMergeWizard(models.TransientModel):
    _name = "product.merge.wizard"
    _description = "Merge existing products by Series"

    result_message = fields.Text(string="Last result", readonly=True)

    def action_merge(self):
        self.ensure_one()
        result = self.env["product.csv.importer"].sudo().merge_existing_catalog()
        msg = _(
            "Merge complete (existing products — images and stock kept).\n"
            "• Series groups merged: %(merged_series)s\n"
            "• New combined products: %(created)s\n"
            "• Combined products updated: %(updated)s\n"
            "• Old duplicate SKUs archived: %(archived_skus)s\n"
            "• Stock lines moved: %(stock_migrations)s\n\n"
            "The shop now shows one product per Series with a Configuration "
            "dropdown. Your product images were copied to the merged product."
        ) % result
        self.result_message = msg
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Products merged"),
                "message": msg,
                "type": "success",
                "sticky": True,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": "product.merge.wizard",
                    "res_id": self.id,
                    "views": [(False, "form")],
                    "target": "new",
                },
            },
        }
