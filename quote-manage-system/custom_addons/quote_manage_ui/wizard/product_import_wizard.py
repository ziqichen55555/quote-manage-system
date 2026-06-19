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
            "Import complete (additive mode).\n"
            "• CSV rows (SKUs): %(sku_count)s\n"
            "• New products created: %(created)s\n"
            "• Existing products changed: %(updated)s\n"
            "• Stock lines added: %(stock_batches)s\n"
            "• Serial numbers skipped (already in stock): %(skipped_serials)s\n\n"
            "Existing products keep their name, price, and attributes — only "
            "new serials/quantity are added. SKUs not in this file are untouched."
        ) % {**result, "skipped_serials": result.get("skipped_serials", 0)}
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
