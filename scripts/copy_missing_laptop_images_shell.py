# -*- coding: utf-8 -*-
"""
Copy product photos onto shop SKUs that still show the Odoo placeholder.

Approved mapping (2026-07-27):
  * T480s missing CMOSP <- same-model T480s donor
  * T15 Gen 2i missing CMOSP <- 20W4004TAU-BT70
  * Samsung 24" bundle: not in this script (no donor)

DRY_RUN inspect-only by default.
Set DRY_RUN to False and confirm_apply to APPLY to write.
"""
DRY_RUN = True
confirm_apply = ""  # must be "APPLY" when DRY_RUN is False

# (target_sku, donor_sku, reason)
COPIES = [
    # T480s
    (
        "20L8SBL100-BT70-CMOSP",
        "20L8SBL100-BTU70-CMOSP",
        "T480s: same MTM sibling",
    ),
    (
        "20L8SDCE00-16G-256G-T-BT70-CMOSP",
        "20L8SDCE00-BTU70",
        "T480s: same MTM base (SDCE00)",
    ),
    (
        "20L8SDCE00-8G-256G-T-BT70-CMOSP",
        "20L8SDCE00-BTU70",
        "T480s: same MTM base (SDCE00)",
    ),
    (
        "20L8SDCE00-8G-256G-T-BTU70-CMOSP",
        "20L8SDCE00-BTU70",
        "T480s: same MTM base (SDCE00)",
    ),
    # T15 Gen 2i
    (
        "20W4004TAU-16G-512G-T-BT70-CMOSP",
        "20W4004TAU-BT70",
        "T15 Gen 2i: same model donor",
    ),
    (
        "20W4004TAU-24G-512G-T-BT70-CMOSP",
        "20W4004TAU-BT70",
        "T15 Gen 2i: same model donor",
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
