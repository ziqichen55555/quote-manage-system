# -*- coding: utf-8 -*-
"""
Run inside Odoo shell (env is predefined):

  docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d DB \\
    < /mnt/custom-addons/quote_manage_ui/scripts/import_product_csv.py

Or:  exec(open("/mnt/custom-addons/quote_manage_ui/scripts/import_product_csv.py").read())

Reads: quote_manage_ui/data/product_import_ready.csv
Creates or updates product.template by default_code; sets list_price & standard_price from cost_ex;
syncs website attribute lines (Brand / Series / CPU / RAM / Storage / Touch / WAN) from title for shop tags;
clears product_tag_ids on storable imports; applies stock via inventory_quantity_auto_apply when stock is installed.
"""
from __future__ import annotations

import base64
import csv
import re
from collections import defaultdict
from pathlib import Path

import requests
from markupsafe import escape

CSV_PATH = Path("/mnt/custom-addons/quote_manage_ui/data/product_import_ready.csv")


def _clean_title(title: str, code: str) -> str:
    t = (title or "").strip()
    for p in (
        "Re-Ware ",
        "Re-ware ",
        "Re-WareLenovo",
        "Re-WareLenovo ",
        "Co-Creative IT & ",
    ):
        if t.upper().startswith(p.upper()):
            t = t[len(p) :].strip()
    
    # Aggressive truncation for technical specs
    # Split by comma, parenthesis, or bracket and take the first part
    t = re.split(r'[,(\[]', t)[0].strip()
    
    # Remove common technical suffixes and redundant words
    # We want to keep "ThinkPad T14s" but remove "HYBRID USB-C..."
    t = re.sub(r'\s+(i[3579]|CPU|@|Intel|\d+\s?GB|\d+\s?SSD|USB-C|USB-A|DOCK|DOCKING|SFF|Tiny|Mini|Switch|cloud-managed|Layer\s?2|port|Gigabit|Ethernet|PoE\+|SFP).*$', '', t, flags=re.I).strip()
    
    # Fix common typos
    t = re.sub(r'^Odell', 'Dell', t, flags=re.I)
    
    # If it's a Lenovo ThinkPad, ensure it's clean
    if "THINKPAD" in t.upper():
        t = re.sub(r'(ThinkPad\s+[A-Z0-9]+).*$', r'\1', t, flags=re.I).strip()
        if not t.startswith("Lenovo"):
            t = f"Lenovo {t}"
    
    # If it's a Dell Latitude/Optiplex, ensure it's clean
    if "LATITUDE" in t.upper() or "OPTIPLEX" in t.upper():
        t = re.sub(r'((?:Latitude|Optiplex)\s+[A-Z0-9]+).*$', r'\1', t, flags=re.I).strip()
        if not t.startswith("Dell"):
            t = f"Dell {t}"

    # If it's a Meraki Switch
    if "MERAKI" in t.upper() and "MS220" in code.upper():
        t = f"Meraki {code.upper()}"
    elif "MERAKI" in t.upper() and "MR" in code.upper():
        t = f"Meraki {code.upper()}"

    return (t[:200] if t else code) or code


def _fetch_image(url: str) -> bytes | None:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        return base64.b64encode(resp.content)
    except Exception as e:
        print(f"Fetch failed for {url}: {e}")
        return None


def _sync_product_images(env, tmpl, title: str):
    """Fetch images based on title and attach to product."""
    # Sample image map for demonstration
    # Categories: Laptop, Desktop, Monitor, Dock, Networking, Accessories
    LAPTOP_VIEWS = [
        "https://unsplash.com/photos/AodYkAhsU4w/download?force=true&w=640", # Front
        "https://unsplash.com/photos/FOIVg8D_Tns/download?force=true&w=640", # Side
        "https://unsplash.com/photos/WLmUkN1Qxkc/download?force=true&w=640", # Keyboard
    ]
    DESKTOP_VIEWS = [
        "https://unsplash.com/photos/Zk5VT0zy6Zg/download?force=true&w=640", # Front
        "https://unsplash.com/photos/raYCIWM7HsQ/download?force=true&w=640", # Angle
        "https://unsplash.com/photos/uJS4gy_lgIg/download?force=true&w=640", # Side
    ]
    MONITOR_VIEWS = [
        "https://unsplash.com/photos/-3_WpTWNMbI/download?force=true&w=640", # Front
        "https://unsplash.com/photos/RmMNRUN-ASM/download?force=true&w=640", # Desk
        "https://unsplash.com/photos/MPTyosWgiWA/download?force=true&w=640", # Angle
    ]
    DOCK_VIEWS = [
        "https://cdn.cs.1worldsync.com/fe/21/fe213d86-4adf-460c-9839-7a6049d559b9.jpg", # Main
        "https://cdn.cs.1worldsync.com/6c/da/6cdafc20-432d-4aad-bdca-b4ed68b966f4.jpg", # Side
        "https://cdn.cs.1worldsync.com/8d/7d/8d7def0a-536f-4826-8f86-25762da570b4.jpg", # Angle
    ]
    NETWORKING_VIEWS = [
        "https://openwrt.org/_media/media/meraki/mr18-7.jpg",
        "https://5.imimg.com/data5/BL/UB/MY-72644893/mr18-hw-1000x1000.jpg",
    ]
    MERAKI_SWITCH_VIEWS = [
        "https://unsplash.com/photos/G_9u927O_7s/download?force=true&w=640", # Network switch
        "https://unsplash.com/photos/vE5AKQRUs7c/download?force=true&w=640", # Switch with cables
    ]

    IMAGE_MAP = {
        "Lenovo ThinkPad Hybrid": DOCK_VIEWS,
        "ThinkPad T14s": [
            "https://p4-ofp.static.pub/fes/cms/2024/03/18/4kh7kd640bjmmoxylxe2hrhhxe6rfi478563.png",
        ] + LAPTOP_VIEWS[1:],
        "ThinkPad T15": [
            "https://cdn.shopify.com/s/files/1/0659/6342/6008/files/LenovoThinkPadT1515.png?v=1762929676",
        ] + LAPTOP_VIEWS[1:],
        "ThinkPad P1": [
            "https://p3-ofp.static.pub/fes/cms/2022/03/21/2cgsl33c6uo4pnek5wphntoelukwii932952.png",
        ] + LAPTOP_VIEWS[1:],
        "Optiplex 9020M": DESKTOP_VIEWS,
        "Dell 5590": LAPTOP_VIEWS,
        "Dell 3301": LAPTOP_VIEWS,
        "Dell E7470": LAPTOP_VIEWS,
        "Toughbook": LAPTOP_VIEWS,
        "Meraki MS": MERAKI_SWITCH_VIEWS,
        "Meraki MR": NETWORKING_VIEWS,
        "Meraki": NETWORKING_VIEWS,
        "Prodesk 400": DESKTOP_VIEWS,
        "ThinkPad": LAPTOP_VIEWS,
        "Dell": LAPTOP_VIEWS,
        "Optiplex": DESKTOP_VIEWS,
        "Dock": DOCK_VIEWS,
        "Monitor": MONITOR_VIEWS,
        "Samsung": MONITOR_VIEWS,
        "Cisco": NETWORKING_VIEWS,
        "Keyboard": ["https://unsplash.com/photos/Guoh4Xpv2m4/download?force=true&w=640"],
        "Mouse": ["https://unsplash.com/photos/Guoh4Xpv2m4/download?force=true&w=640"],
        "Backpack": ["https://unsplash.com/photos/Guoh4Xpv2m4/download?force=true&w=640"],
        "Service": ["https://unsplash.com/photos/Guoh4Xpv2m4/download?force=true&w=640"],
    }
    
    # Match title to map
    urls = []
    t_up = title.upper()
    for key in sorted(IMAGE_MAP.keys(), key=len, reverse=True):
        if key.upper() in t_up:
            urls = IMAGE_MAP[key]
            break
    
    if not urls:
        return

    # Set main image
    if not tmpl.image_1920:
        img_data = _fetch_image(urls[0])
        if img_data:
            tmpl.image_1920 = img_data
            print(f"Set main image for {title}")
    
    # Set extra images
    if len(urls) > 1:
        # Clear existing extra images for this demo
        tmpl.product_template_image_ids.unlink()
        for i, url in enumerate(urls[1:]):
            img_data = _fetch_image(url)
            if img_data:
                env["product.image"].sudo().create({
                    "name": f"{title} - View {i+2}",
                    "product_tmpl_id": tmpl.id,
                    "image_1920": img_data,
                })
                print(f"Added extra image {i+2} for {title}")


def _float(val):
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(str(val).strip())
    except ValueError:
        return None


def _int(val):
    if val is None or str(val).strip() == "":
        return 0
    try:
        return int(float(str(val).strip()))
    except ValueError:
        return 0


def _section_maps(env):
    """Return dict section_lower -> (categ_id, public_commands, tag_commands, type)."""

    def ref(xmlid):
        return env.ref(xmlid).id

    return {
        "laptops": (
            ref("quote_manage_ui.product_category_computer_systems_refurb"),
            [(6, 0, [ref("quote_manage_ui.public_cat_laptops"), ref("quote_manage_ui.public_cat_laptops_computer_systems")])],
            [(6, 0, [ref("quote_manage_ui.product_tag_computer_systems")])],
            "product",
        ),
        "docks": (
            ref("quote_manage_ui.product_category_docks"),
            [(6, 0, [ref("quote_manage_ui.public_cat_docks")])],
            [(6, 0, [ref("quote_manage_ui.product_tag_docks")])],
            "product",
        ),
        "desktops": (
            ref("quote_manage_ui.product_category_workstations"),
            [(6, 0, [ref("quote_manage_ui.public_cat_desktops")])],
            [(6, 0, [ref("quote_manage_ui.product_tag_desktops")])],
            "product",
        ),
        "accessories": (
            ref("quote_manage_ui.product_category_pc_accessories"),
            [(6, 0, [ref("quote_manage_ui.public_cat_accessories")])],
            [(6, 0, [ref("quote_manage_ui.product_tag_accessories")])],
            "product",
        ),
        "monitors": (
            ref("quote_manage_ui.product_category_monitors"),
            [(6, 0, [ref("quote_manage_ui.public_cat_monitors")])],
            [(6, 0, [ref("quote_manage_ui.product_tag_monitors")])],
            "product",
        ),
        "networking": (
            ref("quote_manage_ui.product_category_pc_accessories"),
            [(6, 0, [ref("quote_manage_ui.public_cat_accessories")])],
            [(6, 0, [ref("quote_manage_ui.product_tag_accessories")])],
            "product",
        ),
    }


MANAGED_ATTR_XMLIDS = (
    "quote_manage_ui.attr_brand",
    "quote_manage_ui.attr_series",
    "quote_manage_ui.attr_cpu",
    "quote_manage_ui.attr_ram",
    "quote_manage_ui.attr_storage",
    "quote_manage_ui.attr_touchscreen",
    "quote_manage_ui.attr_wan",
)


def _managed_attribute_ids(env):
    return [env.ref(x).id for x in MANAGED_ATTR_XMLIDS]


def _get_or_create_attr_value(env, attribute, name):
    PAV = env["product.attribute.value"].sudo()
    name = (name or "").strip()[:128]
    if not name:
        return PAV.browse()
    found = PAV.search(
        [("attribute_id", "=", attribute.id), ("name", "=ilike", name)], limit=1
    )
    if found:
        return found
    return PAV.create({"attribute_id": attribute.id, "name": name})


def _ref_val(env, xmlid, not_found_ok=True):
    try:
        return env.ref(xmlid)
    except ValueError:
        return False if not_found_ok else None


def _sync_template_attributes(env, tmpl, *, brand, titles, ptype):
    """Replace managed attribute lines so the shop can show attribute:value tags."""
    if ptype != "product":
        return
    Line = env["product.template.attribute.line"].sudo()
    managed_ids = _managed_attribute_ids(env)
    Line.search(
        [("product_tmpl_id", "=", tmpl.id), ("attribute_id", "in", managed_ids)]
    ).unlink()

    blob = " ".join(titles).strip() if titles else (tmpl.name or "")
    t_up = blob.upper()

    def add_line(attr_xml, value_recs):
        if not value_recs:
            return
        attr = env.ref(attr_xml)
        Line.create(
            {
                "product_tmpl_id": tmpl.id,
                "attribute_id": attr.id,
                "value_ids": [(6, 0, value_recs.ids)],
            }
        )

    brand_txt = (brand or "").strip()
    if not brand_txt:
        if "DELL" in t_up or "ODELL" in t_up:
            brand_txt = "Dell"
        elif "LENOVO" in t_up or "THINKPAD" in t_up:
            brand_txt = "Lenovo"
        elif "HP " in t_up or " HP" in t_up:
            brand_txt = "HP"
        elif "PANASONIC" in t_up or "TOUGHBOOK" in t_up:
            brand_txt = "Panasonic"
        elif "CISCO" in t_up:
            brand_txt = "Cisco"
        elif "SAMSUNG" in t_up:
            brand_txt = "Samsung"

    if brand_txt:
        v = _get_or_create_attr_value(env, env.ref("quote_manage_ui.attr_brand"), brand_txt)
        if v:
            add_line("quote_manage_ui.attr_brand", v)

    series_val = False
    if "T490" in t_up or "T490S" in t_up:
        series_val = _ref_val(env, "quote_manage_ui.attr_val_series_t490s")
    elif "T14S" in t_up or ("T14" in t_up and "T490" not in t_up):
        series_val = _ref_val(env, "quote_manage_ui.attr_val_series_t14s")
    elif "T15" in t_up:
        series_val = _ref_val(env, "quote_manage_ui.attr_val_series_t15")
    elif "P1" in t_up and ("GEN 3" in t_up or "GEN3" in t_up.replace(" ", "")):
        series_val = _ref_val(env, "quote_manage_ui.attr_val_series_p1")
    elif "T480" in t_up:
        series_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_series"), "ThinkPad T480s"
        )
    elif "LAT3301" in t_up:
        series_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_series"), "Latitude 3301"
        )
    elif "LAT5590" in t_up:
        series_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_series"), "Latitude 5590"
        )
    elif "LAT5591" in t_up:
        series_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_series"), "Latitude 5591"
        )
    elif "LATITUDE" in t_up:
        m = re.search(r"Latitude\s+([A-Z0-9]+)", blob, re.I)
        label = m.group(1) if m else "Latitude"
        series_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_series"), f"Dell {label}"
        )
    elif "OPTIPLEX" in t_up:
        m = re.search(r"Optiplex\s+([A-Z0-9]+)", blob, re.I)
        label = m.group(1) if m else "Optiplex"
        series_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_series"), f"Optiplex {label}"
        )
    elif "TOUGHBOOK" in t_up or "FZ55" in t_up or "CF-54" in t_up or "CF 54" in t_up:
        series_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_series"), "Toughbook"
        )
    if series_val:
        add_line("quote_manage_ui.attr_series", series_val)

    cpu_val = False
    if re.search(r"I5[-\s]?10210U|102IOU", t_up):
        cpu_val = _ref_val(env, "quote_manage_ui.attr_val_cpu_i5_10210u")
    elif "8265U" in t_up:
        cpu_val = _ref_val(env, "quote_manage_ui.attr_val_cpu_i5_8265u")
    elif re.search(r"I7.*2\.8|I7 @\s*2\.8", t_up):
        cpu_val = _ref_val(env, "quote_manage_ui.attr_val_cpu_i7_28ghz")
    elif "10885" in t_up or "I9" in t_up:
        cpu_val = _ref_val(env, "quote_manage_ui.attr_val_cpu_i9_24ghz")
    elif "1135G7" in t_up or "1145G7" in t_up:
        cpu_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_cpu"), "11th Gen Core i5/i7"
        )
    elif "7300U" in t_up:
        cpu_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_cpu"), "i5-7300U"
        )
    elif "8365U" in t_up:
        cpu_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_cpu"), "i5-8365U"
        )
    elif "8565U" in t_up:
        cpu_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_cpu"), "i7-8565U"
        )
    elif "6200U" in t_up:
        cpu_val = _get_or_create_attr_value(
            env, env.ref("quote_manage_ui.attr_cpu"), "i5-6200U"
        )
    if cpu_val:
        add_line("quote_manage_ui.attr_cpu", cpu_val)

    ram_val = False
    # 1. Look for explicit "GB RAM"
    ram_m = re.search(r"(\d+)\s*G[B]?\s*RAM", blob, re.I)
    if ram_m:
        gb = int(ram_m.group(1))
        if gb == 8:
            ram_val = _ref_val(env, "quote_manage_ui.attr_val_ram_8gb")
        elif gb == 16:
            ram_val = _ref_val(env, "quote_manage_ui.attr_val_ram_16gb")
        elif gb == 40:
            ram_val = _ref_val(env, "quote_manage_ui.attr_val_ram_40gb")
        else:
            ram_val = _get_or_create_attr_value(env, env.ref("quote_manage_ui.attr_ram"), f"{gb}GB")
    else:
        # 2. Look for multiple GB mentions, e.g. "256GB, 8GB" -> usually last one is RAM
        all_gb = re.findall(r"(\d+)\s*G[B]?", blob, re.I)
        if len(all_gb) >= 2:
            gb = int(all_gb[-1])
            if gb <= 64: # Sanity check for RAM size
                ram_val = _get_or_create_attr_value(env, env.ref("quote_manage_ui.attr_ram"), f"{gb}GB")
        elif len(all_gb) == 1:
            gb = int(all_gb[0])
            if gb <= 64:
                ram_val = _get_or_create_attr_value(env, env.ref("quote_manage_ui.attr_ram"), f"{gb}GB")

    if ram_val:
        add_line("quote_manage_ui.attr_ram", ram_val)

    st_val = False
    if re.search(r"1\s*TB\s*SSD", blob, re.I):
        st_val = _ref_val(env, "quote_manage_ui.attr_val_storage_1tbssd")
    else:
        # Look for GB SSD or the larger GB mention
        st_m = re.search(r"(\d+)\s*(?:GB|G)\s*SSD", blob, re.I)
        if st_m:
            num = st_m.group(1)
            if "256" in num:
                st_val = _ref_val(env, "quote_manage_ui.attr_val_storage_256ssd")
            elif "512" in num:
                st_val = _ref_val(env, "quote_manage_ui.attr_val_storage_512ssd")
            else:
                st_val = _get_or_create_attr_value(env, env.ref("quote_manage_ui.attr_storage"), f"{num}GB SSD")
        else:
            all_gb = re.findall(r"(\d+)\s*G[B]?", blob, re.I)
            if all_gb:
                # If we have multiple, pick the one that isn't the RAM one (usually the larger one)
                nums = [int(x) for x in all_gb]
                if len(nums) >= 2:
                    # If we have 256 and 8, 256 is storage
                    potential_st = [x for x in nums if x > 64]
                    if potential_st:
                        num = max(potential_st)
                        if num == 256:
                            st_val = _ref_val(env, "quote_manage_ui.attr_val_storage_256ssd")
                        elif num == 512:
                            st_val = _ref_val(env, "quote_manage_ui.attr_val_storage_512ssd")
                        else:
                            st_val = _get_or_create_attr_value(env, env.ref("quote_manage_ui.attr_storage"), f"{num}GB SSD")
                elif len(nums) == 1 and nums[0] > 64:
                    num = nums[0]
                    if num == 256:
                        st_val = _ref_val(env, "quote_manage_ui.attr_val_storage_256ssd")
                    elif num == 512:
                        st_val = _ref_val(env, "quote_manage_ui.attr_val_storage_512ssd")
                    else:
                        st_val = _get_or_create_attr_value(env, env.ref("quote_manage_ui.attr_storage"), f"{num}GB SSD")
    
    if not st_val and "500GB" in t_up:
        st_val = _get_or_create_attr_value(env, env.ref("quote_manage_ui.attr_storage"), "500GB HDD")

    if st_val:
        add_line("quote_manage_ui.attr_storage", st_val)

    if "TOUCH" in t_up or "TOUCHSCREEN" in t_up:
        touch = _ref_val(env, "quote_manage_ui.attr_val_touchscreen_yes")
        if touch:
            add_line("quote_manage_ui.attr_touchscreen", touch)

    if "WAN" in t_up or "4G LTE" in t_up or " LTE" in t_up:
        wan = _ref_val(env, "quote_manage_ui.attr_val_wan_enabled")
        if wan:
            add_line("quote_manage_ui.attr_wan", wan)
    
    return series_val.name if series_val else None


def run_import(env):
    if not CSV_PATH.is_file():
        raise FileNotFoundError(CSV_PATH)

    sections = _section_maps(env)
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))

    agg = defaultdict(
        lambda: {
            "qty": 0,
            "cost_num": 0.0,
            "cost_w": 0.0,
            "titles": [],
            "brands": [],
            "sections": [],
            "conditions": [],
            "units": [],
            "notes": [],
        }
    )

    for r in rows:
        code = (r.get("default_code") or "").strip()
        if not code:
            continue
        a = agg[code]
        sec = (r.get("section") or "").strip()
        if sec:
            a["sections"].append(sec)
        q = _int(r.get("quantity"))
        a["qty"] += q
        cost = _float(r.get("cost_ex"))
        if cost is not None and q > 0:
            a["cost_num"] += cost * q
            a["cost_w"] += q
        elif cost is not None and q == 0:
            a["cost_num"] = cost
            a["cost_w"] = 1.0
        title = (r.get("title_raw") or "").strip()
        if title:
            a["titles"].append(title)
        brand = (r.get("brand") or "").strip()
        if brand:
            a["brands"].append(brand)
        cond = (r.get("condition_note") or "").strip()
        if cond:
            a["conditions"].append(cond)
        uid = (r.get("unit_identifiers") or "").strip()
        if uid:
            a["units"].append(uid)
        note = (r.get("row_note") or "").strip()
        if note:
            a["notes"].append(note)

    PT = env["product.template"].sudo()
    created = updated = stock_lines = 0

    for code, a in sorted(agg.items()):
        sec_key = (a["sections"][-1] if a["sections"] else "accessories").lower()
        if sec_key not in sections:
            sec_key = "accessories"

        categ_id, public_cmds, tag_cmds, ptype = sections[sec_key]
        if code.upper() == "CCIT0001":
            ptype = "service"
            categ_id = env.ref("quote_manage_ui.product_category_services").id
            public_cmds = [(6, 0, [env.ref("quote_manage_ui.public_cat_services").id])]
            tag_cmds = [(5, 0, 0)]

        titles = a["titles"] or [code]
        name = _clean_title(titles[0], code)
        desc_parts = []
        if len(titles) > 1:
            desc_parts.append("<p><strong>Alternate titles</strong></p><ul>")
            for t in titles[1:]:
                desc_parts.append(f"<li>{escape(t)}</li>")
            desc_parts.append("</ul>")
        if a["conditions"]:
            desc_parts.append(
                "<p><strong>Condition / variant</strong>: "
                + escape(", ".join(a["conditions"]))
                + "</p>"
            )
        if a["units"]:
            desc_parts.append(
                "<p><strong>Unit IDs</strong>: " + escape(" | ".join(a["units"])) + "</p>"
            )
        if a["notes"]:
            desc_parts.append(
                "<p><strong>Import notes</strong>: "
                + escape(", ".join(sorted(set(a["notes"]))))
                + "</p>"
            )
        desc_html = "".join(desc_parts) if desc_parts else False

        cost_avg = None
        if a["cost_w"] and a["cost_w"] > 0:
            cost_avg = a["cost_num"] / a["cost_w"]
        elif a["cost_num"]:
            cost_avg = a["cost_num"]

        list_price = cost_avg if cost_avg is not None else 0.0
        std_price = cost_avg if cost_avg is not None else 0.0

        brand_txt = a["brands"][-1] if a["brands"] else ""
        desc_sale = f"{brand_txt} · {code}".strip(" ·") if brand_txt else code

        tmpl = PT.search([("default_code", "=", code)], limit=1)
        # Determine tracking based on unit_identifiers
        # If it contains '|' or '/', we assume it's a list of unique serial numbers.
        # Otherwise, no tracking.
        uids_raw = " ".join(a["units"])
        has_sn_list = "|" in uids_raw or "/" in uids_raw
        
        tracking = "serial" if (ptype == "product" and has_sn_list) else "none"

        vals = {
            "name": name,
            "default_code": code,
            "categ_id": categ_id,
            "public_categ_ids": public_cmds,
            "product_tag_ids": [(5, 0, 0)] if ptype == "product" else tag_cmds,
            "type": ptype,
            "tracking": tracking,
            "list_price": list_price,
            "standard_price": std_price,
            "website_published": True,
            "sale_ok": True,
            "description_sale": desc_sale[:500],
            # Storable products: block the shop from ordering more than what's
            # in stock (Odoo defaults this to True = keep selling out-of-stock).
            "allow_out_of_stock_order": ptype != "product",
            "show_availability": ptype == "product",
        }
        if desc_html:
            vals["description"] = desc_html

        if tmpl:
            tmpl.write(vals)
            updated += 1
            t = tmpl
        else:
            vals["barcode"] = code
            t = PT.create(vals)
            created += 1

        series_name = _sync_template_attributes(
            env, t, brand=brand_txt, titles=a["titles"], ptype=ptype
        )
        if series_name and ptype == "product":
            t.write({"name": series_name})
        
        # Sync images based on title
        try:
            _sync_product_images(env, t, t.name)
        except Exception as e:
            print(f"Error syncing images for {t.name}: {e}")

        if "stock.quant" in env and ptype == "product" and a["qty"] > 0:
            wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)
            if wh:
                if len(t.product_variant_ids) != 1:
                    print(f"skip stock for {code}: {len(t.product_variant_ids)} variants")
                else:
                    variant = t.product_variant_id
                    
                    if tracking == "serial":
                        # Parse unit identifiers into a flat list
                        units = []
                        for u_str in a["units"]:
                            units.extend([x.strip() for x in u_str.replace("|", "/").split("/") if x.strip()])
                        
                        qty_to_assign = int(a["qty"])
                        for i in range(qty_to_assign):
                            lot_name = False
                            if i < len(units):
                                lot_name = units[i]
                            else:
                                # Generate placeholder serial if tracking is serial but no ID provided
                                lot_name = f"S/N-{code}-{i+1:03d}"
                            
                            lot = env["stock.lot"].sudo().search([
                                ("product_id", "=", variant.id),
                                ("name", "=", lot_name),
                                ("company_id", "=", env.company.id)
                            ], limit=1)
                            if not lot:
                                lot = env["stock.lot"].sudo().create({
                                    "product_id": variant.id,
                                    "name": lot_name,
                                    "company_id": env.company.id
                                })
                            
                            sq = env["stock.quant"].sudo().search([
                                ("product_id", "=", variant.id),
                                ("location_id", "=", wh.lot_stock_id.id),
                                ("lot_id", "=", lot.id)
                            ], limit=1)
                            
                            if sq:
                                sq.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 1.0})
                            else:
                                env["stock.quant"].sudo().with_context(inventory_mode=True).create({
                                    "product_id": variant.id,
                                    "location_id": wh.lot_stock_id.id,
                                    "lot_id": lot.id,
                                    "inventory_quantity_auto_apply": 1.0
                                })
                    else:
                        # No tracking or Lot tracking (simplified to no tracking for now)
                        sq = env["stock.quant"].sudo().search(
                            [
                                ("product_id", "=", variant.id),
                                ("location_id", "=", wh.lot_stock_id.id),
                                ("lot_id", "=", False),
                            ],
                            limit=1,
                        )
                        target = float(a["qty"])
                        if sq:
                            sq.with_context(inventory_mode=True).write(
                                {"inventory_quantity_auto_apply": target}
                            )
                        else:
                            env["stock.quant"].sudo().with_context(inventory_mode=True).create(
                                {
                                    "product_id": variant.id,
                                    "location_id": wh.lot_stock_id.id,
                                    "inventory_quantity_auto_apply": target,
                                }
                            )
                    stock_lines += 1

        env.cr.commit()

    return {"created": created, "updated": updated, "stock_batches": stock_lines, "sku_count": len(agg)}


# Odoo shell entry
result = run_import(env)
print(result)
