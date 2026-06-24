# -*- coding: utf-8 -*-
SO = env["sale.order"].sudo()
print("TOTAL ORDERS:", SO.search_count([]))
for o in SO.search([], order="name"):
    print(
        f"{o.name} state={o.state} partner={o.partner_id.name!r} "
        f"total={o.amount_total} lines={len(o.order_line)}"
    )
