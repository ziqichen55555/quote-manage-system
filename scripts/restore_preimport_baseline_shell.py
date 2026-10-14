# -*- coding: utf-8 -*-
"""Reset production inventory to pre-import backup baseline (2026-09-11 04:20 UTC)."""
DRY_RUN = False
confirm_apply = "APPLY"

PT = env["product.template"].sudo().with_context(active_test=False)
PP = env["product.product"].sudo().with_context(active_test=False)
Quant = env["stock.quant"].sudo()
Lot = env["stock.lot"].sudo().with_context(active_test=False)
Importer = env["product.csv.importer"].sudo()

MISTAKE_NEW_IDS = list(range(929, 938))

# From scripts/preimport_sn_clean_20260911_0420.csv (119 units, 120 rows)
BASELINE_ROWS = [
    ("20JTS15500-BT70-CMOSP", 857, "PC0QA8R7"),
    ("20L8SBL100-BTU70-CMOSP", 828, "PC13Z0XV"),
    ("20L8SDCE00-8G-256G-T-BTU70-CMOSP", 862, "PC14S1EF"),
    ("20L8SDCE00-8G-256G-T-BTU70-CMOSP", 862, "PC14S1K7"),
    ("20L8SDCE00-8G-256G-T-BTU70-CMOSP", 862, "PC14S1KN"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1ACZJK"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1ADA7Q"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1EYJXN"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FSFVX"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FSFWS"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FSFXJ"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FSFYM"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVEPP"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVEQ8"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVEQS"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVERF"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVEW0"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVFCF"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVGK1"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVGPN"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVNCP"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVNDN"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVNEA"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVNFW"),
    ("20NYS4CP00-8G-256G-T-BT70-CMOSP", 831, "PC1FVNH4"),
    ("20NYS4CP00-8G-256G-T-BTU70-CMOSP", 833, "PC1EYJXF"),
    ("20NYS4CP00-8G-512G-T-BT70-CMOSP", 835, "PC1FSFVM"),
    ("20NYS4CP00-8G-512G-T-BT70-CMOSP", 835, "PC1FVGKJ"),
    ("20NYS4CP00-8G-512G-T-BT70-CMOSP", 835, "PC1FVGKV"),
    ("20T0003UAU-BT70-CMOSP", 863, "PC1M4HG2"),
    ("20T0003UAU-BT70-CMOSP", 863, "PC1TKK7H"),
    ("20T0003UAU-BT70-CMOSP", 863, "PC1TKK7K"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9GM"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9GP"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9H9"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9HT"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9HW"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9J0"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9J1"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9J8"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9J9"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9JC"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9JG"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9K0"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9K6"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9KL"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9M8"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9MA"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9MJ"),
    ("20T1S6C300-BT70-CMOSP", 839, "PC1PQ9MY"),
    ("20T1S6C300-BTU70-CMOSP", 840, "PC1PQ9HY"),
    ("20T1S6C300-BTU70-CMOSP", 840, "PC1PQ9LE"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2V9RKC"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2V9X2V"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2W5BRA"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2W5DSV"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WGAF0"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WHCQX"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WHCRB"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WHQG8"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WHXMZ"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WHXNG"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WJ57S"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WJ59A"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WJ59L"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WJ5B5"),
    ("20W4004TAU-16G-512G-T-BT70-CMOSP", 864, "PF2WJC5E"),
    ("20W4004TAU-24G-512G-T-BT70-CMOSP", 865, "PF2WJ59Z"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R1TP"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R1W9"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R3NY"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R3P5"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R3P6"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R3PT"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R3ZF"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R412"),
    ("20WN0025AU-BT70-CMOSP", 844, "PC27R4BT"),
    ("20WNA07YAU-BT70-CMOSP", 846, "GM048TKM"),
    ("20WNS1M500-BT70-CMOSP", 867, "PC23W0A2"),
    ("20WNS1M500-BT70-CMOSP", 867, "PC23W0A6"),
    ("20WNS1M500-BT70-CMOSP", 867, "PC23W0AR"),
    ("20WNS1M500-BT70-CMOSP", 867, "PC23W0B1"),
    ("20WNS1M500-BT70-CMOSP", 867, "PC23W0B6"),
    ("20WNS1M500-BT70-CMOSP", 867, "PC23W0C8"),
    ("20WNS1M500-BT70-CMOSP", 867, "PC23W0CZ"),
    ("20WNS1M500-BTU70-CMOSP", 868, "PC23W0BM"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CMZJX"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CMZJZ"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CMZK3"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CN0HD"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CN0HY"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CN0J4"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CN0JY"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CN0M2"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2CN0PC"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2FFDFP"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2FFDHT"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JLEXG"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JNSDG"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JNSFC"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JNSFN"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JNSH3"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JNSHD"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JNTPN"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JNTPP"),
    ("20WNS6LL00-BT70-CMOSP", 870, "PC2JNTS3"),
    ("20WNS8B700-BT70-CMOSP", 871, "PC2L9239"),
    ("30B5S0PF00-CMOSP", 848, "PC0MDC46"),
    ("ACERDV0817", 894, "2500296259"),
    ("BENQPB2240", 893, "PDP7500279TVO"),
    ("CF-54H1436VA-BT70-CMOSP", 902, "9FTSC49459"),
    ("CF-54H1436VA-BT70-CMOSP", 902, "9FTSC49592"),
    ("CF-54H1436VA-BT70-CMOSP", 902, "9FTSC49614"),
    ("CF-54J1436VA-BTU70-CMOSP", 886, "9FTSC49459"),
    ("EPEB1723", 890, "M9CF9X0075L"),
    ("NECM322WG", 891, "4540229EC"),
    ("NECME331WG", 889, "8240155RE"),
    ("NECV311WG", 892, "4640165EA"),
    ("", 905, "1DXD9Y3"),
    ("", 879, "5CD7134GC9"),
]

wh = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)
if not wh:
    raise RuntimeError("No warehouse")


def stock_quants(variant):
    return Quant.search([
        ("product_id", "=", variant.id),
        ("location_id", "child_of", wh.lot_stock_id.id),
    ])


def zero_variant(variant, label):
    n = 0
    for q in stock_quants(variant):
        if float(q.quantity or 0) == 0:
            continue
        sn = q.lot_id.name if q.lot_id else "(no lot)"
        print(f"    ZERO {label} {sn} qty={q.quantity:g}")
        if not DRY_RUN:
            q.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 0.0})
        n += 1
    return n


def resolve_target_variant(sku, tmpl_id):
    tmpl = PT.browse(tmpl_id)
    if not tmpl.exists():
        raise RuntimeError(f"Missing template id={tmpl_id} sku={sku!r}")
    if sku and (tmpl.default_code or "") != sku:
        alt = PT.search([("default_code", "=", sku), ("id", "!=", tmpl_id)], limit=1)
        if alt:
            print(f"  WARN tmpl {tmpl_id} code={tmpl.default_code!r} != {sku!r}, using id={alt.id}")
            tmpl = alt
        else:
            print(f"  WARN tmpl {tmpl_id} code mismatch: {tmpl.default_code!r} vs {sku!r}")
    return tmpl.product_variant_ids[:1]


def apply_serial(target_variant, serial_name):
    serial_name = (serial_name or "").strip()
    if not serial_name:
        return "empty"

    dest = Quant.search([
        ("product_id", "=", target_variant.id),
        ("location_id", "child_of", wh.lot_stock_id.id),
        ("lot_id.name", "=", serial_name),
        ("quantity", ">", 0),
    ], limit=1)
    if dest:
        return "ok"

    other_lots = Lot.search([
        ("name", "=", serial_name),
        ("company_id", "=", env.company.id),
        ("product_id", "!=", target_variant.id),
    ])
    for lot in other_lots:
        src_q = Quant.search([
            ("lot_id", "=", lot.id),
            ("product_id", "=", lot.product_id.id),
            ("location_id", "child_of", wh.lot_stock_id.id),
            ("quantity", ">", 0),
        ], limit=1)
        if src_q and not DRY_RUN:
            Importer._move_serial_lot_to_variant(lot, target_variant, wh)
            return "moved"
        if src_q and DRY_RUN:
            print(f"    [DRY] move {serial_name} from {lot.product_id.default_code} -> {target_variant.default_code}")
            return "would_move"

    target_lot = Lot.search([
        ("product_id", "=", target_variant.id),
        ("name", "=", serial_name),
        ("company_id", "=", env.company.id),
    ], limit=1)
    if not target_lot and not DRY_RUN:
        target_lot = Lot.create({
            "product_id": target_variant.id,
            "name": serial_name,
            "company_id": env.company.id,
        })
    elif not target_lot and DRY_RUN:
        print(f"    [DRY] create lot {serial_name} on {target_variant.default_code or target_variant.id}")
        return "would_create"

    dest_q = Quant.search([
        ("product_id", "=", target_variant.id),
        ("location_id", "child_of", wh.lot_stock_id.id),
        ("lot_id", "=", target_lot.id),
    ], limit=1)
    label = target_variant.default_code or f"tmpl{target_variant.product_tmpl_id.id}"
    print(f"    SET {serial_name} -> {label}")
    if DRY_RUN:
        return "would_set"
    if dest_q:
        dest_q.with_context(inventory_mode=True).write({"inventory_quantity_auto_apply": 1.0})
    else:
        Quant.with_context(inventory_mode=True).create({
            "product_id": target_variant.id,
            "location_id": wh.lot_stock_id.id,
            "lot_id": target_lot.id,
            "inventory_quantity_auto_apply": 1.0,
        })
    return "set"


baseline_tmpl_ids = sorted({tid for _sku, tid, _sn in BASELINE_ROWS})
touch_tmpl_ids = sorted(set(baseline_tmpl_ids) | set(MISTAKE_NEW_IDS))

print("=" * 72)
print("RESTORE PRE-IMPORT BASELINE (db-20260911-042017)")
print(f"DRY_RUN={DRY_RUN} rows={len(BASELINE_ROWS)} tmpl_ids={len(baseline_tmpl_ids)}")
print("=" * 72)

stats = {"zeroed": 0, "applied": 0, "archived": 0}

print("\n--- Phase 1: zero stock on baseline + mistake products ---")
for tid in touch_tmpl_ids:
    tmpl = PT.browse(tid)
    if not tmpl.exists():
        print(f"SKIP missing tmpl {tid}")
        continue
    variant = tmpl.product_variant_ids[:1]
    ref = tmpl.default_code or f"ID{tid}"
    before = float(tmpl.qty_available or 0)
    if before == 0:
        continue
    print(f"\n{ref} (ID={tid}) on_hand={before:g}")
    stats["zeroed"] += zero_variant(variant, ref)

if not DRY_RUN:
    env.cr.commit()
    print("\nPhase 1 committed.")

print("\n--- Phase 2: apply baseline SNs ---")
expected_by_sku = {}
for sku, tmpl_id, serial in BASELINE_ROWS:
    variant = resolve_target_variant(sku, tmpl_id)
    ref = variant.default_code or f"ID{tmpl_id}"
    expected_by_sku[ref] = expected_by_sku.get(ref, 0) + 1
    result = apply_serial(variant, serial)
    stats["applied"] += 1 if result in ("set", "moved", "ok", "would_set", "would_move", "would_create") else 0

print("\n--- Phase 3: archive mistaken import products 929-937 ---")
for mid in MISTAKE_NEW_IDS:
    tmpl = PT.browse(mid)
    if not tmpl.exists():
        continue
    print(f"  ID={mid} {tmpl.default_code} active={tmpl.active} on_hand={tmpl.qty_available:g}")
    if not DRY_RUN:
        variant = tmpl.product_variant_ids[:1]
        zero_variant(variant, tmpl.default_code or str(mid))
        tmpl.write({"active": False, "sale_ok": False, "website_published": False})
        tmpl.product_variant_ids.write({"active": False})
    stats["archived"] += 1

print("\n--- Phase 4: ensure baseline products active ---")
for tid in baseline_tmpl_ids:
    tmpl = PT.browse(tid)
    if not tmpl.exists():
        continue
    if not DRY_RUN:
        tmpl.write({"active": True, "sale_ok": True, "website_published": True})
        tmpl.product_variant_ids.write({"active": True})

print("\n--- Verification ---")
mismatch = 0
for ref, want in sorted(expected_by_sku.items()):
    tmpl = PT.search([("default_code", "=", ref)], limit=1) if ref and not ref.startswith("ID") else PT.browse(0)
    if not tmpl and ref.startswith("ID"):
        tmpl = PT.browse(int(ref[2:]))
    if not tmpl and ref == "":
        continue
    if not tmpl:
        # no-sku products: match by tmpl id from rows
        continue
    got = int(tmpl.qty_available or 0)
    ok = got == want
    flag = "OK" if ok else "MISMATCH"
    if not ok:
        mismatch += 1
    print(f"  {flag} {ref or f'ID{tmpl.id}'}: want={want} got={got}")

# no-sku products
for sku, tid, serial in BASELINE_ROWS:
    if sku:
        continue
    tmpl = PT.browse(tid)
    want = sum(1 for s, t, _ in BASELINE_ROWS if t == tid and not s)
    got = int(tmpl.qty_available or 0)
    ok = got == want
    if not ok:
        mismatch += 1
    print(f"  {'OK' if ok else 'MISMATCH'} ID{tid} ({tmpl.name}): want={want} got={got}")

total_got = 0
for tid in baseline_tmpl_ids:
    total_got += int(PT.browse(tid).qty_available or 0)
print(f"\nTotal baseline units: want={len(BASELINE_ROWS)} got={total_got} zeroed_quants={stats['zeroed']}")

print("\n" + "=" * 72)
if mismatch:
    print(f"DONE with {mismatch} SKU mismatches")
else:
    print("DONE — all baseline SKUs match")

if DRY_RUN:
    print("\nPreview only. Set DRY_RUN=False to apply.")
    env.cr.rollback()
else:
    env.cr.commit()
    print("\nCommitted.")
