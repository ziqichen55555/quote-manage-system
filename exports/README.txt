Re-Ware shipping master (share this folder on OneDrive)

  product_weights_prod.csv   — weight (kg) + pack L×W×H (cm) for all SKUs
  product_weights_prod.xlsx  — same data for Excel review with colleagues

Regenerate suggestions (keeps your edited L/W/H cells):
  python scripts/generate_product_pack_dims_csv.py

Import to Odoo production: apply_product_pack_dims_csv_shell.py (+ weight scripts as needed).
