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

# SKU -> filenames (case-insensitive match inside pictures dir).
SKU_FILE_MANIFEST: dict[str, list[str]] = {
  # ThinkPad T14s Gen 1 — share real warehouse photos (not 99px PNG thumbs).
    "20T0003UAU": ["t14s.jpg", "t14s side.jpg"],
    "20T1S6C300": ["t14s.jpg", "t14s side.jpg"],
  # ThinkPad T14s Gen 2i
    "20WN0025AU": ["T14s G2.jpg", "T14s G2 2.jpg"],
    "20WNA07YAU": ["T14s G2.jpg", "T14s G2 2.jpg"],
    "20WNS6LL00": ["T14s G2.jpg", "T14s G2 2.jpg"],
  # ThinkPad T15
    "20W4004TAU": ["T15 1.jpg", "T15 2.jpg", "T15 3.jpg"],
  # Dell Latitude
    "LAT3301": ["lattitude 3301.jpg", "lattitude 3301 2.jpg"],
    "LATITUDE 3301": ["lattitude 3301.jpg", "lattitude 3301 2.jpg"],
    "LAT5590": ["latitude 5590.jpg", "latitude 5590 2.jpg"],
    "LAT5591": ["latitude 5590.jpg", "latitude 5590 2.jpg"],
  # Toughbook
    "CF 54 MK 3": ["CF 54 1.jpg", "CF54 2.jpg", "CF54 3.jpg"],
    "FZ55-1": ["FZ 55.jfif"],
  # Desktops
    "30B4S1QA00": ["P510.jpg"],
    "30B4S3WF00": ["P510.jpg"],
    "10MLS1BU00": ["M910s.jpg", "M910s back.jpg"],
    "10MLS5RS00": ["M910s.jpg", "M910s back.jpg"],
    "4518PT1": ["M91p.jfif"],
    "10A8A06QAU": ["M93p.jfif"],
    "10AXS27900": ["M73 Tiny.webp", "m73 tINY.jfif"],
  # Docks / monitors (bundles)
    "26D32AA": ["Hp G5 F.jpg", "Hp G5 R.jpg", "HP G5 back.jpg"],
    "3FF69AA": ["Hp G4.jpg"],
    "BUNDLES24E450": ["dual monitor bundle 1.jpg", "dual monitor bundle 2.jpg"],
    "22C450": ["22 bundle dock.jpg", "22bundle dock 2.jpg"],
}

SKIP_NAME_PATTERNS = re.compile(
    r"(gen\s*1\.png$|gen\s*2i\.png$|whatsapp|whiteboard|service\.jpeg$)",
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
