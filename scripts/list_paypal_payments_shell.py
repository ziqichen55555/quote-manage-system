# -*- coding: utf-8 -*-
"""Read-only: any PayPal (native or Stripe paypal method) payment transactions."""
DRY_RUN = True

Tx = env["payment.transaction"].sudo()
SO = env["sale.order"].sudo()

print("=== PayPal payment transactions (all time) ===")
paypal_txs = Tx.search(
    [
        "|",
        ("provider_code", "=", "paypal"),
        ("payment_method_code", "=", "paypal"),
    ],
    order="id asc",
)
print(f"Count: {len(paypal_txs)}")
for t in paypal_txs:
    so = SO.search([("name", "=", t.reference.split("-")[0])], limit=1)
    if not so and t.reference:
        so = SO.search([("name", "=", t.reference)], limit=1)
    print(
        f"id={t.id} ref={t.reference!r} provider={t.provider_code!r} "
        f"method={t.payment_method_code!r} state={t.state!r} "
        f"amount={t.amount} {t.currency_id.name} date={t.create_date}"
    )
    if so:
        print(f"  sale_order={so.name} state={so.state} partner={so.partner_id.name!r}")

print("\n=== Stripe txs with method=paypal only ===")
stripe_paypal = Tx.search(
    [("provider_code", "=", "stripe"), ("payment_method_code", "=", "paypal")],
    order="id asc",
)
print(f"Count: {len(stripe_paypal)}")
for t in stripe_paypal:
    print(
        f"id={t.id} ref={t.reference!r} state={t.state!r} "
        f"amount={t.amount} {t.create_date}"
    )
    if t.state_message:
        print(f"  msg={(t.state_message or '')[:200]!r}")

print("\n=== Summary: successful online payments by method ===")
done = Tx.search([("state", "=", "done")])
by_method = {}
for t in done:
    key = (t.provider_code, t.payment_method_code)
    by_method[key] = by_method.get(key, 0) + 1
for (prov, meth), n in sorted(by_method.items(), key=lambda x: (-x[1], x[0])):
    print(f"  {prov} / {meth}: {n}")

print("Done.")
