# -*- coding: utf-8 -*-
"""Thin shell entry — delegates to the Odoo backend importer."""
from pathlib import Path

CSV_PATH = Path("/mnt/custom-addons/quote_manage_ui/data/product_import_ready.csv")

if not CSV_PATH.is_file():
    raise FileNotFoundError(CSV_PATH)

result = env["product.csv.importer"].sudo().import_from_path(str(CSV_PATH))
print(result)
