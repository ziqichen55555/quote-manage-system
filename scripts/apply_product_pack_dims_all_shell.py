# -*- coding: utf-8 -*-
"""Apply suggested pack dimensions to all sale_ok products missing rw_ship_* cm.

DRY_RUN=False — writes production data. Re-run backfill_product_pack_dims_shell.py
(DRY_RUN=True) to preview rule changes.

Later edits: update exports/product_pack_dims_suggested.xlsx then CSV import via
apply_product_pack_dims_csv_shell.py
"""
DRY_RUN = False
OVERWRITE = False

import re

Template = env["product.template"].sudo()


def _text_blob(tmpl):
    parts = [
        tmpl.name or "",
        tmpl.default_code or "",
        tmpl.categ_id.name or "",
    ]
    parts.extend(tmpl.public_categ_ids.mapped("name"))
    return " ".join(parts).lower()


def suggest_pack_dims_cm(tmpl):
    blob = _text_blob(tmpl)
    pubs = {n.lower() for n in tmpl.public_categ_ids.mapped("name") if n}
    categ = (tmpl.categ_id.name or "").lower()

    def dims(l, w, h):
        return (float(l), float(w), float(h))

    if re.search(
        r"\b(dual|2 x|two)\b.*\b(monitor|screen|display)\b", blob
    ) or re.search(r"\b(monitor|screen|display).*\bbundle\b", blob):
        if re.search(r"\b24[\"']|24 inch\b", blob):
            return dims(60, 40, 25)
        return dims(55, 38, 22)
    if (
        "cables & adapters" in pubs
        or categ == "chargers / power adapters"
        or re.search(
            r"\b(cable|adapter|charger|comsol|displayport|hdmi|usb|display port|ethernet extension)\b",
            blob,
        )
    ):
        return dims(18, 12, 4)
    if "laptops" in pubs or (
        categ == "computer systems"
        and re.search(r"\b(thinkpad|latitude|toughbook|cf-54|elitebook|probook)\b", blob)
    ):
        if re.search(r"\b(toughbook|cf-54)\b", blob):
            return dims(42, 32, 8)
        if re.search(r"\b(t15|p15|17[\"']|17 inch|p17|p71)\b", blob):
            return dims(40, 30, 6)
        return dims(38, 28, 5)
    if "desktops" in pubs or re.search(r"\b(optiplex|elite desk|9020|800 g2|tiny|m910)\b", blob):
        if re.search(r"\b(mini|tiny|m910|nuc|micro)\b", blob):
            return dims(35, 30, 15)
        return dims(40, 35, 18)
    if re.search(r"\b(thinkstation|p510|workstation|tower)\b", blob):
        return dims(50, 45, 30)
    if "monitors" in pubs or categ == "monitors & displays" or re.search(
        r"\b(monitor|display)\b", blob
    ):
        if re.search(r"\b(32[\"']|34[\"']|43[\"']|49[\"'])\b", blob):
            return dims(75, 45, 15)
        if re.search(r"\b27[\"']", blob):
            return dims(65, 42, 14)
        return dims(55, 35, 12)
    if "docks" in pubs or categ == "docks & port replicators" or re.search(
        r"\bdock\b", blob
    ):
        return dims(28, 20, 8)
    if "projectors" in pubs or "projector" in blob:
        return dims(38, 30, 12)
    if "digital camera" in pubs or re.search(r"\b(camer|powershot|dslr|lumix)\b", blob):
        return dims(15, 12, 8)
    if categ == "headphones" or re.search(r"\b(headphone|jabra|earbud)\b", blob):
        return dims(22, 18, 10)
    if re.search(r"\b(mouse|keyboard)\b", blob):
        return dims(35, 15, 5)
    if re.search(r"\b(3750|48p|48 port)\b", blob):
        return dims(55, 40, 15)
    if re.search(r"\b(router|switch|cisco|access point|2911|1941|meraki)\b", blob):
        return dims(35, 25, 10)
    if categ == "pc accessories" or "accessories" in pubs:
        if re.search(r"\b(speaker|conference cam|bcc950)\b", blob):
            return dims(30, 25, 20)
        if re.search(r"\b(backpack|bag)\b", blob):
            return dims(45, 35, 15)
        return dims(28, 22, 8)
    return dims(30, 25, 10)


def _has_dims(tmpl):
    return (
        (tmpl.rw_ship_length_cm or 0) > 0
        and (tmpl.rw_ship_width_cm or 0) > 0
        and (tmpl.rw_ship_height_cm or 0) > 0
    )


domain = [("sale_ok", "=", True), ("type", "!=", "service")]
templates = Template.search(domain, order="id")
if not OVERWRITE:
    templates = templates.filtered(lambda t: not _has_dims(t))

print("=" * 72)
print(f"apply_product_pack_dims_all DRY_RUN={DRY_RUN} OVERWRITE={OVERWRITE}")
print(f"templates to update: {len(templates)}")
print("=" * 72)

updates = []
for tmpl in templates:
    l_cm, w_cm, h_cm = suggest_pack_dims_cm(tmpl)
    updates.append((tmpl, l_cm, w_cm, h_cm))
    print(
        f"  id={tmpl.id} code={tmpl.default_code or '-'} "
        f"-> {l_cm}x{w_cm}x{h_cm} cm | {tmpl.name[:50]}"
    )

if DRY_RUN:
    print(f"DRY_RUN: would update {len(updates)} templates.")
else:
    for tmpl, l_cm, w_cm, h_cm in updates:
        tmpl.write(
            {
                "rw_ship_length_cm": l_cm,
                "rw_ship_width_cm": w_cm,
                "rw_ship_height_cm": h_cm,
            }
        )
    env.cr.commit()
    print(f"APPLIED pack dims on {len(updates)} templates.")

print("Done.")
