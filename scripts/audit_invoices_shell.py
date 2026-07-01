# -*- coding: utf-8 -*-
"""Audit all customer invoices: paid, reversed, problematic flags."""
Move = env["account.move"].sudo()
SO = env["sale.order"].sudo()

invs = Move.search(
    [("move_type", "in", ("out_invoice", "out_refund"))],
    order="invoice_date desc, name desc",
)

INTERNAL_PARTNERS = {"re-ware", "co-creative-it", "co-creative it", "cocreativeit"}

def is_internal(partner):
    n = (partner.name or "").strip().casefold()
    return any(x in n for x in INTERNAL_PARTNERS) or partner.id == env.company.partner_id.id


def flags(inv):
    f = []
    if inv.state == "draft":
        f.append("DRAFT")
    if inv.state == "cancel":
        f.append("CANCELLED")
    if inv.amount_total == 0:
        f.append("ZERO")
    if inv.reversal_move_id:
        f.append("REVERSED(has credit note)")
    if inv.reversed_entry_id:
        f.append("CREDIT_NOTE")
    if inv.payment_state == "paid":
        f.append("PAID")
    elif inv.payment_state == "not_paid" and inv.state == "posted":
        f.append("UNPAID")
    elif inv.payment_state == "reversed":
        f.append("PAYMENT_REVERSED")
    if is_internal(inv.partner_id):
        f.append("INTERNAL")
    sos = inv.invoice_line_ids.mapped("sale_line_ids.order_id")
    if not sos and inv.state == "posted" and inv.amount_total > 0 and not inv.reversed_entry_id:
        f.append("NO_SALE_ORDER")
    # SO product mismatch: invoice product != current SO lines
    for so in sos:
        inv_prods = set(inv.invoice_line_ids.mapped("product_id").ids)
        so_prods = set(so.order_line.mapped("product_id").ids)
        if inv_prods and so_prods and not inv_prods & so_prods:
            f.append(f"SO_MISMATCH({so.name})")
    return f


print("=" * 100)
print("CUSTOMER INVOICE AUDIT")
print("=" * 100)
print(f"{'Name':<18} {'Date':<12} {'Customer':<28} {'Total':>10} {'Pay':<12} {'State':<8} Flags / SO")
print("-" * 100)

problem = []
ok = []

for inv in invs:
    fl = flags(inv)
    sos = inv.invoice_line_ids.mapped("sale_line_ids.order_id")
    so_names = ",".join(sos.mapped("name")) or "-"
    prods = " | ".join(
        (l.product_id.default_code or l.name[:20]) for l in inv.invoice_line_ids[:2]
    )[:40]
    line = (
        f"{inv.name or '/':<18} "
        f"{str(inv.invoice_date or ''):<12} "
        f"{(inv.partner_id.name or '')[:28]:<28} "
        f"{inv.amount_total:>10.2f} "
        f"{inv.payment_state:<12} "
        f"{inv.state:<8} "
        f"{', '.join(fl)}"
    )
    print(line)
    print(f"{'':18} SO={so_names}  products={prods}")
    if any(
        x in fl
        for x in (
            "DRAFT",
            "ZERO",
            "NO_SALE_ORDER",
        )
    ) or any("SO_MISMATCH" in x for x in fl) or (
        "CREDIT_NOTE" in fl and inv.state == "draft"
    ):
        problem.append(inv)
    elif "REVERSED" in str(fl) or inv.payment_state == "reversed":
        ok.append((inv, "reversed/cancelled ok"))
    elif "INTERNAL" in fl:
        ok.append((inv, "internal/test"))
    elif inv.payment_state == "paid":
        ok.append((inv, "paid real"))
    elif inv.payment_state == "not_paid" and inv.state == "posted" and "REVERSED" not in str(fl):
        problem.append(inv)  # open AR

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)
posted_real = invs.filtered(
    lambda i: i.move_type == "out_invoice"
    and i.state == "posted"
    and not i.reversal_move_id
    and not is_internal(i.partner_id)
    and i.amount_total > 0
)
paid_real = posted_real.filtered(lambda i: i.payment_state == "paid")
unpaid_real = posted_real.filtered(lambda i: i.payment_state == "not_paid")
print(f"Posted customer invoices (excl internal, not reversed): {len(posted_real)}")
print(f"  Paid (real money received): {len(paid_real)}  total={sum(paid_real.mapped('amount_total')):.2f}")
print(f"  Unpaid (still owe you): {len(unpaid_real)}  total={sum(unpaid_real.mapped('amount_total')):.2f}")

draft_cn = invs.filtered(lambda i: i.move_type == "out_refund" and i.state == "draft")
print(f"Draft credit notes (need POST): {draft_cn.mapped('name')}")

reversed_inv = invs.filtered(lambda i: i.reversal_move_id)
print(f"Reversed invoices: {[(i.name, i.reversal_move_id.name) for i in reversed_inv]}")

print()
print("LIKELY PROBLEMS:")
for inv in problem:
    print(f"  {inv.name or 'DRAFT'}  {inv.partner_id.name}  {flags(inv)}")

print()
print("Done.")
