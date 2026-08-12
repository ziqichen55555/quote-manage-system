# -*- coding: utf-8 -*-
"""Read-only: return location options for WH/OUT/00071."""
Picking = env["stock.picking"].sudo()
p = Picking.search([("name", "=", "WH/OUT/00071")], limit=1)
assert p.exists(), "picking not found"
print(f"picking={p.name} state={p.state} type={p.picking_type_id.name}")
print(f"  location_id (src)={p.location_id.complete_name}")
print(f"  location_dest_id={p.location_dest_id.complete_name}")
print(f"  warehouse={p.picking_type_id.warehouse_id.name}")
wh = p.picking_type_id.warehouse_id
print(f"  wh.lot_stock_id={wh.lot_stock_id.complete_name if wh.lot_stock_id else None}")
print(f"  wh.wh_input_stock_loc_id={wh.wh_input_stock_loc_id.complete_name if wh.wh_input_stock_loc_id else None}")
# default return type
ret_type = p.picking_type_id.return_picking_type_id
print(f"  return_picking_type={ret_type.display_name if ret_type else None}")
if ret_type:
    print(f"    default_location_src={ret_type.default_location_src_id.complete_name}")
    print(f"    default_location_dest={ret_type.default_location_dest_id.complete_name}")
for ml in p.move_line_ids:
    print(f"  move_line product={ml.product_id.default_code} qty={ml.qty_done} lot={ml.lot_id.name or '-'}")
    print(f"    from={ml.location_id.complete_name} -> {ml.location_dest_id.complete_name}")
