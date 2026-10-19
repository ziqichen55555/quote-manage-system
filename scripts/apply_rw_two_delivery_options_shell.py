# -*- coding: utf-8 -*-
"""Prod: flat $25 post + pickup carriers; unpublish Odoo Standard delivery."""
DRY_RUN = True

Delivery = env["delivery.carrier"].sudo()
Product = env["product.product"].sudo()
Template = env["product.template"].sudo()
ICP = env["ir.config_parameter"].sudo()
AU = env.ref("base.au")

print("=" * 72)
print(f"apply_rw_two_delivery_options DRY_RUN={DRY_RUN}")
print("=" * 72)

demo = env.ref("delivery.free_delivery_carrier", raise_if_not_found=False)
if demo:
    print(f"Odoo Standard delivery id={demo.id} published={demo.website_published} type={demo.delivery_type}")
    if not DRY_RUN:
        demo.write({
            "website_published": False,
            "delivery_type": "fixed",
            "fixed_price": 0.0,
        })
        demo.price_rule_ids.unlink()

post = env.ref("quote_manage_ui.delivery_carrier_rw_au_metro_weight", raise_if_not_found=False)
pickup = env.ref("quote_manage_ui.delivery_carrier_rw_pickup_store", raise_if_not_found=False)

if not pickup:
    print("Creating pickup shipping product + carrier...")
    del_categ = env.ref("delivery.product_category_deliveries", raise_if_not_found=False)
    ship_prod = Product.create({
        "name": "Shipping - In-store pickup",
        "default_code": "RW_SHIP_PICKUP",
        "type": "service",
        "categ_id": del_categ.id if del_categ else False,
        "sale_ok": False,
        "purchase_ok": False,
        "list_price": 0.0,
    })
    pickup_vals = {
        "name": "Pick up in store",
        "delivery_type": "fixed",
        "sequence": 10,
        "website_published": True,
        "country_ids": [(6, 0, [AU.id])],
        "product_id": ship_prod.id,
        "fixed_price": 0.0,
        "carrier_description": "Collect from Co-Creative IT / Re-Ware — no shipping charge.",
    }
    if "rw_store_pickup" in Delivery._fields:
        pickup_vals["rw_store_pickup"] = True
    if "rw_rural_mode" in Delivery._fields:
        pickup_vals["rw_rural_mode"] = "normal"
    if not DRY_RUN:
        pickup = Delivery.create(pickup_vals)
        env["ir.model.data"].sudo().create({
            "name": "delivery_carrier_rw_pickup_store",
            "module": "quote_manage_ui",
            "model": "delivery.carrier",
            "res_id": pickup.id,
            "noupdate": True,
        })
    else:
        print("  would create pickup carrier", pickup_vals)
else:
    print(f"Pickup carrier id={pickup.id} name={pickup.name!r}")

if post:
    vals = {
        "name": "Standard shipping (by post)",
        "delivery_type": "fixed",
        "fixed_price": 25.0,
        "website_published": True,
        "carrier_description": "Flat $25 ex GST per order — we ship to your address.",
    }
    if "rw_store_pickup" in post._fields:
        vals["rw_store_pickup"] = False
    print(f"Post carrier id={post.id} -> {vals}")
    if not DRY_RUN:
        post.write(vals)
        post.price_rule_ids.unlink()

if pickup:
    vals = {
        "name": "Pick up in store",
        "delivery_type": "fixed",
        "fixed_price": 0.0,
        "website_published": True,
        "carrier_description": "Collect from Co-Creative IT / Re-Ware — no shipping charge.",
    }
    if "rw_store_pickup" in pickup._fields:
        vals["rw_store_pickup"] = True
    print(f"Pickup carrier -> {vals}")
    if not DRY_RUN:
        pickup.write(vals)

rural = env.ref("quote_manage_ui.delivery_carrier_rw_au_rural_quote", raise_if_not_found=False)
if rural and rural.website_published:
    print(f"Unpublish rural carrier id={rural.id}")
    if not DRY_RUN:
        rural.write({"website_published": False})

published = Delivery.search([("website_published", "=", True)])
print("\nPublished carriers after apply:")
for c in published:
    print(f"  id={c.id} {c.name!r} fixed={c.fixed_price} pickup={getattr(c, 'rw_store_pickup', None)}")

if DRY_RUN:
    print("\nDRY_RUN: no writes.")
else:
    env.cr.commit()
    print("\nAPPLIED.")

print("Done.")
