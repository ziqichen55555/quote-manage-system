# -*- coding: utf-8 -*-
"""Restore product images on production from same base MTM or same product name.

Backup JSON (backups/prod_product_snapshot-*.json) only records main_image true/false;
actual image bytes stay in Odoo. This copies image_1920 + gallery from donors still in DB.

Dry run:
  print(env['product.template'].quote_restore_missing_images(dry_run=True))

Apply:
  print(env['product.template'].quote_restore_missing_images(dry_run=False))
  env.cr.commit()
"""
import json
from pathlib import Path

result = env["product.template"].quote_restore_missing_images(dry_run=False)
print(json.dumps(result, ensure_ascii=False, indent=2))
env.cr.commit()
print("committed")
