# -*- coding: utf-8 -*-
"""Read-only: website payment providers, methods, recent failed Stripe/PayPal txs."""
DRY_RUN = True

Provider = env["payment.provider"].sudo()
Method = env["payment.method"].sudo()
Tx = env["payment.transaction"].sudo()
Website = env["website"].sudo()

print("=== PAYMENT PROVIDERS (prod DB) ===")
for p in Provider.search([]):
    methods = p.payment_method_ids.mapped("code")
    print(
        f"id={p.id} name={p.name!r} code={p.code!r} state={p.state!r} "
        f"published={p.is_published} company={p.company_id.name!r}"
    )
    print(f"  payment_method_codes={methods}")
    if p.code == "stripe":
        pk = (p.stripe_publishable_key or "")[:12]
        print(f"  stripe_publishable_key prefix={pk!r}…")
    if p.code == "paypal":
        print(f"  paypal_email={getattr(p, 'paypal_email_account', None)!r}")
    if p.code == "airwallex":
        print(f"  airwallex env={getattr(p, 'airwallex_environment', None)!r}")

print("\n=== WEBSITES ===")
for w in Website.search([]):
    print(f"id={w.id} domain={w.domain!r}")

print("\n=== RECENT ERROR / PENDING TX (last 15) ===")
recent = Tx.search([], order="id desc", limit=15)
for t in recent:
    print(
        f"id={t.id} ref={t.reference!r} provider={t.provider_code!r} "
        f"method={t.payment_method_code!r} state={t.state!r} "
        f"amount={t.amount} {t.currency_id.name}"
    )
    if t.state_message:
        msg = (t.state_message or "")[:240].replace("\n", " ")
        print(f"  state_message={msg!r}")

failed = Tx.search([("state", "=", "error")], order="id desc", limit=5)
print("\n=== LAST 5 ERROR TX (full message) ===")
for t in failed:
    print(f"--- {t.reference} provider={t.provider_code} method={t.payment_method_code} ---")
    print(t.state_message or "(no message)")

print("\nDone.")
