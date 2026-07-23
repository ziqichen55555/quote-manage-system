# -*- coding: utf-8 -*-
"""
S00074 — set display/monitor sale.order.line price_unit to 0 so SO matches invoice.

Context:
  Display was meant to be free ($0). Invoice was manually corrected to 0 and sent
  to the customer; sale order still has the original non-zero price.

DRY_RUN=True  → inspect SO vs invoice only (default)
DRY_RUN=False + confirm_apply="APPLY" → write price_unit=0 on matching SO line(s)

Optional:
  FORCE_LINE_IDS = (123,)  # pin exact sale.order.line ids if auto-detect is wrong
"""
DRY_RUN = True
confirm_apply = ""  # must be "APPLY" when DRY_RUN=False

ORDER = "S00074"
TARGET_PRICE = 0.0
FORCE_LINE_IDS = ()  # e.g. (42,) to override auto-detect

# Auto-detect keywords (name / default_code / categ)
DISPLAY_KEYS = (
    "monitor",
    "display",
    "screen",
    "顯示",
    "显示",
    "samsung",
    "dell p24",
    "f24t",
    "s24e",
    "s22a",
    "bundle",
)

SO = env["sale.order"].sudo().search([("name", "=", ORDER)], limit=1)
if not SO:
    raise SystemExit("Order %s not found" % ORDER)

print("=" * 72)
print("Fix display price on", ORDER)
print("  customer:", SO.partner_id.name)
print("  state:", SO.state, "invoice_status:", SO.invoice_status)
print("  SO amount_untaxed:", SO.amount_untaxed, "total:", SO.amount_total)
print("  DRY_RUN:", DRY_RUN)
print("=" * 72)

print("\n--- SALE ORDER LINES ---")
for line in SO.order_line:
    code = line.product_id.default_code or "-"
    print(
        "  sol_id=%s  code=%s  qty=%s  price_unit=%s  subtotal=%s  discount=%s"
        % (
            line.id,
            code,
            line.product_uom_qty,
            line.price_unit,
            line.price_subtotal,
            line.discount,
        )
    )
    print("    name:", (line.name or "")[:90])

print("\n--- INVOICES ---")
inv_by_sol = {}  # sol_id -> list of (inv_name, price_unit, subtotal)
for inv in SO.invoice_ids.sorted("id"):
    print(
        "  %s  type=%s  state=%s  untaxed=%s  total=%s  payment=%s"
        % (
            inv.name or "DRAFT/%s" % inv.id,
            inv.move_type,
            inv.state,
            inv.amount_untaxed,
            inv.amount_total,
            inv.payment_state,
        )
    )
    for il in inv.invoice_line_ids.filtered(lambda l: l.display_type in (False, "product")):
        sols = il.sale_line_ids
        print(
            "    aml_id=%s  code=%s  qty=%s  price_unit=%s  subtotal=%s  sols=%s"
            % (
                il.id,
                il.product_id.default_code or "-",
                il.quantity,
                il.price_unit,
                il.price_subtotal,
                sols.ids,
            )
        )
        print("      name:", (il.name or "")[:90])
        for sol in sols:
            inv_by_sol.setdefault(sol.id, []).append(
                (inv.name or str(inv.id), il.price_unit, il.price_subtotal)
            )

diff = abs(SO.amount_total - sum(
    i.amount_total if i.move_type == "out_invoice" else -i.amount_total
    for i in SO.invoice_ids.filtered(lambda m: m.state == "posted" and m.move_type in ("out_invoice", "out_refund"))
))
print("\nSO vs posted invoice total delta (abs):", round(diff, 2))


def _looks_display(line):
    blob = " ".join(
        [
            (line.name or "").lower(),
            (line.product_id.default_code or "").lower(),
            (line.product_id.name or "").lower(),
            (line.product_id.categ_id.complete_name or "").lower(),
        ]
    )
    return any(k in blob for k in DISPLAY_KEYS)


candidates = env["sale.order.line"].browse()
if FORCE_LINE_IDS:
    candidates = SO.order_line.filtered(lambda l: l.id in FORCE_LINE_IDS)
    print("\nUsing FORCE_LINE_IDS:", FORCE_LINE_IDS)
else:
    # Prefer: display-like + SO price != TARGET + linked invoice price == TARGET
    for line in SO.order_line:
        if line.display_type:
            continue
        inv_prices = [p for _, p, _ in inv_by_sol.get(line.id, [])]
        inv_is_zero = inv_prices and all(abs(p - TARGET_PRICE) < 0.01 for p in inv_prices)
        so_not_zero = abs(line.price_unit - TARGET_PRICE) >= 0.01
        if _looks_display(line) and so_not_zero and (inv_is_zero or not inv_prices):
            candidates |= line
    if not candidates:
        # Fallback: any SO line with non-zero price whose invoice line is 0
        for line in SO.order_line:
            if line.display_type:
                continue
            inv_prices = [p for _, p, _ in inv_by_sol.get(line.id, [])]
            if (
                abs(line.price_unit - TARGET_PRICE) >= 0.01
                and inv_prices
                and all(abs(p - TARGET_PRICE) < 0.01 for p in inv_prices)
            ):
                candidates |= line

print("\n--- CANDIDATES TO SET price_unit=%s ---" % TARGET_PRICE)
if not candidates:
    print("  (none) — inspect lines above; set FORCE_LINE_IDS if needed.")
    raise SystemExit(0)

for line in candidates:
    print(
        "  sol_id=%s  code=%s  current_price=%s  subtotal=%s"
        % (line.id, line.product_id.default_code or "-", line.price_unit, line.price_subtotal)
    )
    for inv_name, ip, isub in inv_by_sol.get(line.id, []):
        print("    linked invoice %s price_unit=%s subtotal=%s" % (inv_name, ip, isub))

if DRY_RUN:
    print("\n[DRY_RUN] Would write price_unit=%s on sol_ids=%s" % (TARGET_PRICE, candidates.ids))
    print("  Expected SO total drop ≈", sum(candidates.mapped("price_subtotal")))
    print("\nSet DRY_RUN=False and confirm_apply='APPLY' to write.")
    raise SystemExit(0)

if confirm_apply != "APPLY":
    raise SystemExit('Refusing write: set confirm_apply="APPLY" when DRY_RUN=False')

before = SO.amount_total
for line in candidates:
    old = line.price_unit
    line.write({"price_unit": TARGET_PRICE})
    print("Wrote sol_id=%s price_unit %s -> %s" % (line.id, old, line.price_unit))

SO.invalidate_recordset()
print("\n=== Result ===")
print("  SO amount_untaxed:", SO.amount_untaxed, "total:", SO.amount_total, "(was", before, ")")
for line in SO.order_line:
    print(
        "  sol_id=%s  code=%s  price_unit=%s  subtotal=%s"
        % (line.id, line.product_id.default_code or "-", line.price_unit, line.price_subtotal)
    )
env.cr.commit()
print("  COMMITTED.")
