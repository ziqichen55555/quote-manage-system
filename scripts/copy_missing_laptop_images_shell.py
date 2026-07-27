# -*- coding: utf-8 -*-
"""
Copy product photos onto shop SKUs that still show the Odoo placeholder.

Approved mapping (visual check 2026-07-27):
  * T14s Gen 2i (missing) ← T14s Gen 1 photo (20T1S6C300-BT70-CMOSP)
    - same-MTM sibling preferred when it already has a real photo
  * T470s ← T480s (20L8SBL100-BTU70-CMOSP) — same classic thick-bezel look
  * T470s ← T490s  SKIP — donor photo has "T490s" printed on the bezel

DRY_RUN=True  → inspect only (default)
DRY_RUN=False + confirm_apply="APPLY" → write + commit
"""
DRY_RUN = False
confirm_apply = "APPLY"

# (target_sku, donor_sku, reason)
COPIES = [
    # T14s Gen 2i — prefer same-MTM sibling that already has Gen1 lineage photo
    (
        "20WNS1M500-BTU70-CMOSP",
        "20WNS1M500-BT70-CMOSP",
        "T14s Gen 2i: same MTM sibling (already has Gen1/T0003 photo)",
    ),
    (
        "20WNS6LL00-BT70-CMOSP",
        "20T1S6C300-BT70-CMOSP",
        "T14s Gen 2i: Gen 1 photo",
    ),
    (
        "20WNS8B700-BT70-CMOSP",
        "20T1S6C300-BT70-CMOSP",
        "T14s Gen 2i: Gen 1 photo",
    ),
]

PT = env["product.template"].sudo().with_context(active_test=False)


def _has_real_image(tmpl):
    """True when image_1920 is set (placeholder shop cards usually have it empty)."""
    return bool(tmpl.image_1920)


print("=" * 60)
print("Copy product images")
print("  DRY_RUN:", DRY_RUN)
print("  pairs:", len(COPIES))
print("=" * 60)

plan = []
for target_sku, donor_sku, reason in COPIES:
    tgt = PT.search([("default_code", "=ilike", target_sku)], limit=1)
    donor = PT.search([("default_code", "=ilike", donor_sku)], limit=1)
    row = {
        "target": target_sku,
        "donor": donor_sku,
        "reason": reason,
        "target_id": tgt.id if tgt else None,
        "donor_id": donor.id if donor else None,
        "target_has_image": _has_real_image(tgt) if tgt else None,
        "donor_has_image": _has_real_image(donor) if donor else None,
        "target_name": tgt.name if tgt else None,
        "donor_name": donor.name if donor else None,
    }
    if not tgt:
        row["status"] = "target_not_found"
    elif not donor:
        row["status"] = "donor_not_found"
    elif not _has_real_image(donor):
        row["status"] = "donor_no_image"
    elif _has_real_image(tgt):
        row["status"] = "target_already_has_image"
    else:
        row["status"] = "would_copy" if DRY_RUN else "copy"
    plan.append(row)
    print(
        "  %s <- %s | %s | %s"
        % (target_sku, donor_sku, row["status"], reason)
    )
    if tgt:
        print(
            "    target id=%s name=%r has_image=%s"
            % (tgt.id, tgt.name, row["target_has_image"])
        )
    if donor:
        print(
            "    donor  id=%s name=%r has_image=%s"
            % (donor.id, donor.name, row["donor_has_image"])
        )

to_copy = [r for r in plan if r["status"] in ("would_copy", "copy")]
print("\nActionable copies:", len(to_copy))

if DRY_RUN:
    print("\n[DRY_RUN] No writes. Set DRY_RUN=False and confirm_apply='APPLY' to write.")
    raise SystemExit(0)

if confirm_apply != "APPLY":
    raise SystemExit('Refusing write: set confirm_apply="APPLY" when DRY_RUN=False')

for row in to_copy:
    result = PT.quote_copy_product_images(row["donor"], [row["target"]], overwrite=True)
    print("COPIED:", result)
    row["status"] = "copied"
    row["result"] = result

env.cr.commit()
print("\nCOMMITTED.")
for row in plan:
    print("  final:", row["target"], "->", row["status"])
