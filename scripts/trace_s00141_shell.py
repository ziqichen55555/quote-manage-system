# -*- coding: utf-8 -*-
"""Read-only: S00141 payment + quotation state investigation."""
ORDER_NAME = "S00141"

SaleOrder = env["sale.order"].sudo()
Payment = env["account.payment"].sudo()
Message = env["mail.message"].sudo()
Tracking = env["mail.tracking.value"].sudo()

so = SaleOrder.search([("name", "=", ORDER_NAME)], limit=1)
if not so:
    so = SaleOrder.browse(141)
if not so.exists():
    print(f"{ORDER_NAME} not found")
else:
    print("=" * 72)
    print(f"Order {so.name} id={so.id}")
    print(f"  state={so.state!r} (draft/sent=quotation, sale=confirmed SO)")
    print(f"  invoice_status={so.invoice_status}")
    print(
        f"  amounts: untaxed={so.amount_untaxed} tax={so.amount_tax} total={so.amount_total} "
        f"currency={so.currency_id.name}"
    )
    print(f"  partner={so.partner_id.display_name} email={so.partner_id.email or ''}")
    print(f"  website={so.website_id.name if so.website_id else None}")
    print(f"  origin={so.origin or ''} client_order_ref={so.client_order_ref or ''}")
    print(f"  date_order={so.date_order} create={so.create_date} write={so.write_date}")
    print(f"  create_uid={so.create_uid.login} write_uid={so.write_uid.login}")

    for line in so.order_line.filtered(lambda l: not l.display_type):
        print(
            f"  line: {line.product_id.default_code or '-'} qty={line.product_uom_qty:g} "
            f"subtotal={line.price_subtotal} {line.name[:70]!r}"
        )

    txs = so.transaction_ids
    print()
    print(f"payment.transaction count={len(txs)}")
    for tx in txs.sorted("id"):
        print(
            f"  tx id={tx.id} ref={tx.reference!r} state={tx.state!r} "
            f"provider={tx.provider_id.name if tx.provider_id else '-'} "
            f"amount={tx.amount} currency={tx.currency_id.name}"
        )
        for fname in (
            "provider_reference",
            "stripe_payment_intent",
            "authorize_txn_id",
            "paypal_authorization_id",
        ):
            if fname in tx._fields and tx[fname]:
                print(f"    {fname}={tx[fname]!r}")

    print()
    print(f"Invoices count={len(so.invoice_ids)}")
    for inv in so.invoice_ids:
        print(
            f"  {inv.name} state={inv.state} payment_state={inv.payment_state} "
            f"residual={inv.amount_residual} total={inv.amount_total}"
        )

    maybe = Payment.search(
        [
            "|",
            "|",
            ("ref", "ilike", ORDER_NAME),
            ("payment_reference", "ilike", ORDER_NAME),
            ("memo", "ilike", ORDER_NAME),
        ],
        limit=20,
    )
    print()
    print(f"account.payment mentioning {ORDER_NAME}: {len(maybe)}")
    for p in maybe:
        print(f"  {p.name} state={p.state} amount={p.amount} partner={p.partner_id.display_name}")

    msgs = Message.search(
        [("model", "=", "sale.order"), ("res_id", "=", so.id)],
        order="id desc",
        limit=25,
    )
    print()
    print(f"Recent chatter ({len(msgs)}):")
    for m in msgs:
        author = m.author_id.display_name if m.author_id else (m.email_from or "system")
        body = (m.subject or m.body or "")[:160].replace("\n", " ")
        print(f"  {m.date} [{m.message_type}] {author}: {body}")

    trackings = Tracking.search([("mail_message_id", "in", msgs.ids)], order="id desc")
    if trackings:
        print()
        print("Field changes:")
        for t in trackings[:30]:
            old = t.old_value_char or t.old_value_integer or t.old_value_monetary
            new = t.new_value_char or t.new_value_integer or t.new_value_monetary
            print(f"  {t.field_id.name}: {old!r} -> {new!r}")

    print()
    print("VERDICT HINT:")
    paid_tx = txs.filtered(lambda t: t.state in ("done", "authorized", "pending"))
    if so.state in ("draft", "sent"):
        print("  UI shows Quotation because state is draft/sent (not confirmed sale order).")
    if txs and not paid_tx:
        print("  Payment transactions exist but none are done/authorized — treat as NOT paid.")
    elif paid_tx:
        print("  At least one transaction is done/authorized — investigate why SO still quotation.")
    elif not txs:
        print("  No payment transactions linked — user did NOT complete checkout payment.")

print("Done.")
