# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ProductMergeWizard(models.TransientModel):
    _name = "product.merge.wizard"
    _description = "Archive old Series-combined shop products"

    result_message = fields.Text(string="Last result", readonly=True)

    def action_merge(self):
        self.ensure_one()
        result = self.env["product.csv.importer"].sudo().merge_existing_catalog()
        msg = result.get("message") or _(
            "Archived %(archived)s old combined Series product(s). "
            "Re-upload your MERGED CSV to recreate separate MTM listings."
        ) % {"archived": result.get("archived_skus", 0)}
        self.result_message = msg
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Old Series products archived"),
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
