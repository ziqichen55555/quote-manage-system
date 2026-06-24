# -*- coding: utf-8 -*-
"""Map Re-Ware shop SKUs to image files on the local USB drive (U盘).

Default folder: ``Sales Pictures`` on the first removable drive that contains it
(usually ``D:\\Sales Pictures`` when the PRINTER USB is plugged in).
Override with env ``SALES_PICTURES_DIR`` or ``--pictures-dir``.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

# Legacy default — correct when the Co-Creative USB is mounted as D:
FALLBACK_SALES_PICTURES_DIR = Path(r"D:\Sales Pictures")


def find_sales_pictures_dir() -> Path:
    """Locate ``Sales Pictures`` on a removable (U盘) drive, else fallback."""
    override = __import__("os").environ.get("SALES_PICTURES_DIR", "").strip()
    if override:
        return Path(override)

    try:
        import ctypes

        drive_mask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if not (drive_mask & (1 << i)):
                continue
            letter = chr(ord("A") + i)
            root = Path(f"{letter}:\\")
            candidate = root / "Sales Pictures"
            if not candidate.is_dir():
                continue
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(str(root))
            # 2 = DRIVE_REMOVABLE (U盘 / SD)
            if drive_type == 2:
                return candidate
    except Exception:
        pass

    if FALLBACK_SALES_PICTURES_DIR.is_dir():
        return FALLBACK_SALES_PICTURES_DIR

    return FALLBACK_SALES_PICTURES_DIR


DEFAULT_SALES_PICTURES_DIR = find_sales_pictures_dir()
MIN_IMAGE_SIDE = 400
MIN_FILE_BYTES = 45_000

# SKU -> filenames on the U盘 Sales Pictures folder (quality-checked on upload).
# ~30 shop products with warehouse-grade photos; small .jfif / PNG thumbs excluded.
SKU_FILE_MANIFEST: dict[str, list[str]] = {
    # --- Laptops (11 SKUs) ---
    "20T0003UAU": ["t14s.jpg", "t14s side.jpg"],
    "20T1S6C300": ["t14s.jpg", "t14s side.jpg"],
    "20WN0025AU": ["T14s G2.jpg", "T14s G2 2.jpg"],
    "20WNA07YAU": ["T14s G2.jpg", "T14s G2 2.jpg"],
    "20WNS6LL00": ["T14s G2.jpg", "T14s G2 2.jpg"],
    "20W4004TAU": ["T15 1.jpg", "T15 2.jpg", "T15 3.jpg", "T15 4.jpg"],
    "20NYS4CP00": ["T490s open.jpg", "T490s closed.jpg", "T490s with monitors.jpg"],
    "CF 54 MK 3": [
        "CF 54 1.jpg",
        "CF54 2.jpg",
        "CF54 3.jpg",
        "CF 54 4.jpg",
        "CF54 5.jpg",
    ],
    "LAT3301": ["lattitude 3301.jpg", "lattitude 3301 2.jpg", "lattitude 3301 3.jpg"],
    "LAT5590": ["latitude 5590.jpg", "latitude 5590 2.jpg"],
    "LAT5591": ["latitude 5590.jpg", "latitude 5590 2.jpg"],
    # --- Desktops (6 SKUs, 3 image sets) ---
    "30B4S1QA00": ["P510.jpg"],
    "30B4S3WF00": ["P510.jpg"],
    "10MLS1BU00": ["M910s.jpg", "M910s back.jpg"],
    "10MLS15E00": ["M910s.jpg", "M910s back.jpg"],
    "10MLS5RS00": ["M910s.jpg", "M910s back.jpg"],
    "10AXS27900": ["M73 Tiny.webp"],
    # --- Docks (4 SKUs) ---
    "26D32AA": ["Hp G5 F.jpg", "Hp G5 R.jpg", "HP G5 back.jpg", "new g5 box.jpg"],
    "3FF69AA": ["Hp G4.jpg"],
    "40AF0135AU": ["Lenovo hybrid dock.jpg", "Lenovo hybrid dock full.jpg"],
    "40AJ0135AU": ["lenovo dock cable.jpeg"],
    # --- Monitors & bundles (5 SKUs) ---
    "BUNDLES24E450": ["Dual monitor bundle 1.jpg", "Dual monitor bundle 2.jpg", "dual monitor bundle 3.jpg"],
    "22C450": ["22 bundle dock.jpg", "22bundle dock 2.jpg"],
    "BUNDLESA1450": ["dual monitor 1.jpg", "Dual moniotr 2.jpg", "dual monitor setup.jpg"],
    "F24T450FQEXXY": ["Samsung F24T.webp"],
    "S24E450": ["single screen.jpg", "single screen 2.jpg"],
    # --- Accessories (1 SKU) ---
    "CCITREWAREBAG": ["backpack.jpg", "Back pack 2.jpg"],
    # --- Networking (2 SKUs) ---
    "MR18-HW": ["MR18 1.jpg", "MR18 2.jpg", "MR18 3.jpg"],
    "WS-3750X-48P": ["Cisco Cx3750x.jpg", "Cisco CX3750x back.jpg"],
    # --- Services (1 SKU) ---
    "CCIT0001": ["Service.JPEG"],
}

SKIP_NAME_PATTERNS = re.compile(
    r"(gen\s*1\.png$|gen\s*2i\.png$|whatsapp|whiteboard)",
    re.I,
)


def image_dimensions(data: bytes) -> tuple[int, int] | None:
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as im:
            return im.size
    except Exception:
        return None


def image_quality_ok(path: Path, data: bytes | None = None) -> tuple[bool, str]:
    if SKIP_NAME_PATTERNS.search(path.name):
        return False, "skipped by name pattern (likely thumbnail)"
    raw = data if data is not None else path.read_bytes()
    if len(raw) < MIN_FILE_BYTES:
        return False, f"file too small ({len(raw)} bytes)"
    dims = image_dimensions(raw)
    if dims:
        w, h = dims
        if max(w, h) < MIN_IMAGE_SIDE:
            return False, f"too small ({w}x{h})"
    return True, "ok"


def resolve_picture_files(
    pictures_dir: Path,
    filenames: list[str],
) -> list[Path]:
    """Resolve manifest filenames to existing paths (case-insensitive)."""
    if not pictures_dir.is_dir():
        raise FileNotFoundError(f"Pictures folder not found: {pictures_dir}")
    index = {p.name.casefold(): p for p in pictures_dir.iterdir() if p.is_file()}
    out: list[Path] = []
    for name in filenames:
        hit = index.get(name.casefold())
        if hit:
            out.append(hit)
    return out


def scan_suggestions(pictures_dir: Path) -> list[dict]:
    """List usable images and guessed SKU hints for --scan."""
    rows = []
    if not pictures_dir.is_dir():
        return rows
    for path in sorted(pictures_dir.iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".jfif"}:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        ok, reason = image_quality_ok(path, data)
        dims = image_dimensions(data)
        rows.append(
            {
                "file": path.name,
                "bytes": len(data),
                "dims": f"{dims[0]}x{dims[1]}" if dims else "?",
                "usable": ok,
                "note": reason,
            }
        )
    return rows


def manifest_for_sku(sku: str) -> list[str]:
    key = (sku or "").strip().upper()
    for manifest_key, files in SKU_FILE_MANIFEST.items():
        if manifest_key.upper() == key:
            return list(files)
    return []


def load_sku_images(pictures_dir: Path, sku: str) -> list[Path]:
    files = manifest_for_sku(sku)
    if not files:
        return []
    paths = resolve_picture_files(pictures_dir, files)
    good = []
    for path in paths:
        ok, _reason = image_quality_ok(path)
        if ok:
            good.append(path)
    return good


def manifest_report(pictures_dir: Path | None = None) -> list[dict]:
    """One row per mapped SKU: resolved files and upload readiness."""
    root = pictures_dir or find_sales_pictures_dir()
    rows = []
    for sku in sorted(SKU_FILE_MANIFEST.keys(), key=lambda s: s.upper()):
        wanted = manifest_for_sku(sku)
        resolved = load_sku_images(root, sku)
        rows.append(
            {
                "sku": sku,
                "wanted": wanted,
                "resolved": [p.name for p in resolved],
                "ready": bool(resolved),
                "main": resolved[0].name if resolved else "",
                "gallery": [p.name for p in resolved[1:]],
            }
        )
    return rows
