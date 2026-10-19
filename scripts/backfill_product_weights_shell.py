# -*- coding: utf-8 -*-
"""Backfill product.template weight (kg) for shippable shop products.

Weights are shipping estimates in 0.5 kg steps. Only templates with weight<=0
are updated unless OVERWRITE=True.

DRY_RUN=True: print planned changes only.
"""
DRY_RUN = True
OVERWRITE = False

import re

Template = env["product.template"].sudo()


def round_half(kg):
    return round(float(kg) * 2) / 2.0


def _text_blob(tmpl):
    parts = [
        tmpl.name or "",
        tmpl.default_code or "",
        tmpl.categ_id.name or "",
    ]
    parts.extend(tmpl.public_categ_ids.mapped("name"))
    return " ".join(parts).lower()


def suggest_weight_kg(tmpl):
    blob = _text_blob(tmpl)
    pubs = {n.lower() for n in tmpl.public_categ_ids.mapped("name") if n}
    categ = (tmpl.categ_id.name or "").lower()

    # --- Monitor / screen bundles (before generic defaults) ---
    if re.search(
        r"\b(dual|2 x|two)\b.*\b(monitor|screen|display)\b", blob
    ) or re.search(r"\b(monitor|screen|display).*\bbundle\b", blob):
        if re.search(r"\b24[\"']|24 inch\b", blob):
            return 8.0
        return 5.0
    if "bundle" in blob and re.search(r"\b(monitor|screen|dock|display)\b", blob):
        return 5.0

    # --- Small desktops / SFF (name hints when category is All) ---
    if re.search(r"\btiny\b|\bnuc\b|\bm910\b", blob):
        return 2.0
    if re.search(r"\bthinkstation\b|\bp510\b", blob):
        return 10.0
    if re.search(r"\b(optiplex|elite desk|9020|800 g2)\b", blob):
        return 3.0

    # --- Laptops / notebooks ---
    if "laptops" in pubs or categ == "computer systems":
        if re.search(r"\b(17[\"']|17 inch|p17|p71|workstation)\b", blob):
            return 3.5
        if re.search(r"\b(15[\"']|15 inch|t15|p15|latitude 55)\b", blob):
            return 3.0
        return 2.5

    # --- Desktops ---
    if "desktops" in pubs or "mini pc" in blob or categ == "desktops & workstations":
        if re.search(r"\b(mini|tiny|nuc|micro)\b", blob):
            return 2.0
        if re.search(r"\b(tower|workstation|precision|xeon)\b", blob):
            return 10.0
        return 3.0

    # --- Monitors ---
    if "monitors" in pubs or categ == "monitors & displays" or "monitor" in blob:
        if re.search(r"\b(32[\"']|34[\"']|43[\"']|49[\"'])\b", blob):
            return 8.0
        if re.search(r"\b27[\"']", blob):
            return 7.5
        return 5.0

    # --- Docks ---
    if "docks" in pubs or categ == "docks & port replicators" or "dock" in blob:
        return 1.5

    # --- Projectors / AV ---
    if "projectors" in pubs or "projector" in blob:
        if re.search(r"\b(large|installation|venue)\b", blob):
            return 5.0
        return 3.0

    # --- Cameras ---
    if "digital camera" in pubs or re.search(r"\b(camer|powershot|dslr)\b", blob):
        return 1.0

    # --- Cables / chargers / small adapters ---
    if (
        "cables & adapters" in pubs
        or categ == "chargers / power adapters"
        or re.search(r"\b(cable|adapter|charger|comsol|displayport|hdmi|usb)\b", blob)
    ):
        return 0.5

    # --- Headphones / small accessories ---
    if categ == "headphones" or re.search(r"\b(headphone|earbud|mouse|keyboard)\b", blob):
        return 0.5

    # --- Networking gear (often heavier) ---
    if re.search(r"\b(router|switch|cisco|access point|2911|1941|3750)\b", blob):
        return 4.0

    # --- PC accessories catch-all ---
    if categ == "pc accessories" or "accessories" in pubs:
        if re.search(r"\b(cable|adapter|dongle)\b", blob):
            return 0.5
        return 1.5

    # Default unknown shippable SKU
    return 1.5


domain = [("sale_ok", "=", True), ("type", "!=", "service")]
if not OVERWRITE:
    domain.append(("weight", "<=", 0))

templates = Template.search(domain, order="id")
print("=" * 72)
print(f"backfill_product_weights DRY_RUN={DRY_RUN} OVERWRITE={OVERWRITE}")
print(f"templates matched: {len(templates)}")
print("=" * 72)

by_weight = {}
updates = []
for tmpl in templates:
    kg = round_half(suggest_weight_kg(tmpl))
    by_weight[kg] = by_weight.get(kg, 0) + 1
    updates.append((tmpl, kg))
    print(
        f"  id={tmpl.id} code={tmpl.default_code or '-'} "
        f"weight {tmpl.weight or 0:g} -> {kg:g} | {tmpl.name[:55]}"
    )

print("-" * 72)
print("summary by target weight (kg):")
for kg in sorted(by_weight):
    print(f"  {kg:g} kg: {by_weight[kg]} products")

if DRY_RUN:
    print("DRY_RUN: no writes.")
else:
    for tmpl, kg in updates:
        tmpl.write({"weight": kg})
    env.cr.commit()
    print(f"APPLIED weight on {len(updates)} templates.")

print("Done.")
