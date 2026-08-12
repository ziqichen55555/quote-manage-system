# -*- coding: utf-8 -*-
"""Read-only: why S00091 had no shipping line."""
SaleOrder = env["sale.order"].sudo()
so = SaleOrder.search([("name", "=", "S00091")], limit=1)
Website = env["website"].sudo()
print(f"S00091 state={so.state} website={so.website_id.name}")
print(f"  carrier_id={so.carrier_id.name if so.carrier_id else None}")
print(f"  delivery lines={[(l.name, l.price_unit, l.is_delivery) for l in so.order_line]}")
print(f"  only_services={so.only_services}")
print(f"  partner_shipping zip={so.partner_shipping_id.zip!r} country={so.partner_shipping_id.country_id.code}")
w = so.website_id
print(f"  website.enabled_delivery={w.enabled_delivery}")
# carriers available at time logic
if so.exists():
    methods = so._get_delivery_methods()
    print(f"  delivery methods now for same partner: {methods.mapped('name')}")
    carrier = env.ref("quote_manage_ui.delivery_carrier_rw_au_metro_weight", raise_if_not_found=False)
    if carrier:
        print(f"  metro carrier available now? {carrier._is_available_for_order(so)}")
        res = carrier.rate_shipment(so)
        print(f"  rate_shipment: {res}")
