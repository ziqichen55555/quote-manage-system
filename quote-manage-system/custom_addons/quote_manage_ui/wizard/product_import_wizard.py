# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductImportWizard(models.TransientModel):
    _name = "product.import.wizard"
    _description = "Upload inventory CSV"

    file = fields.Binary(string="CSV file", required=True)
    filename = fields.Char(string="Filename")
    result_message = fields.Text(string="Last result", readonly=True)

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Please choose a CSV file to upload."))
        result = self.env["product.csv.importer"].sudo().import_from_binary(
            self.file, filename=self.filename
        )
        msg = _(
            "Import complete.\n"
            "• CSV rows (SKUs): %(sku_count)s\n"
            "• Products created: %(created)s\n"
            "• Products updated: %(updated)s\n"
            "• Series merged (Configuration dropdown): %(merged_series)s\n"
            "• Old duplicate SKUs archived: %(archived_skus)s\n"
            "• Stock lines applied: %(stock_batches)s\n\n"
            "The shop will show one product per Series with a Configuration "
            "dropdown (lowest price on the catalogue). Re-upload the same CSV "
            "any time to refresh prices and stock."
        ) % result
        self.result_message = msg
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Inventory uploaded"),
                "message": msg,
                "type": "success",
                "sticky": True,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": "product.import.wizard",
                    "res_id": self.id,
                    "views": [(False, "form")],
                    "target": "new",
                },
            },
        }
