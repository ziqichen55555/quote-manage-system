# Run in Odoo shell on production:
#   docker exec -it reware-web-1 odoo shell -d cocreativeit-quote --no-http
# Then: exec(open('/mnt/custom-addons/quote_manage_ui/scripts/cleanup_obsolete_mtm_shell.py').read())

Importer = env["product.csv.importer"].sudo()
base_sku = "20TJS5WW00"

print("=== purge auto S/N placeholders ===")
print(Importer.purge_auto_generated_serial_stock(base_sku))

print("=== zero all stock on obsolete base MTM ===")
print(Importer.sync_serial_stock_allowlist(base_sku, []))

print("=== unpublish base MTM (stock on -BT70) ===")
print(Importer.archive_obsolete_base_mtm_listing(base_sku))

# Remove ghost lot records (0 qty) cluttering the product form
PT = env["product.template"].sudo()
tmpl = PT.search([("default_code", "=", base_sku)], limit=1)
if tmpl:
    variant = tmpl.product_variant_ids[:1]
    Lot = env["stock.lot"].sudo()
    Quant = env["stock.quant"].sudo()
    ghosts = Lot.search([("product_id", "=", variant.id)])
    removed = []
    for lot in ghosts:
        if Quant.search_count([("lot_id", "=", lot.id), ("quantity", "!=", 0)]):
            continue
        removed.append(lot.name)
        lot.unlink()
    print("=== removed ghost lots ===", removed)

env.cr.commit()
print("=== done ===")
