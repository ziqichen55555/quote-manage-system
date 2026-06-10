# -*- coding: utf-8 -*-
"""
Add the Re-Ware logo badge to hero / carousel photos (offline, before upload).

Requires Pillow:
  pip install Pillow

Examples (run from repo root or anywhere):

  # Watermark one photo → hero/ folder (JPEG)
  python quote-manage-system/custom_addons/quote_manage_ui/scripts/watermark_hero_images.py \\
      path/to/photo.jpg -o hero-gc-new.jpg

  # Batch: every image in a folder
  python .../watermark_hero_images.py path/to/photos/ -o ../static/src/img/hero/

  # Regenerate the header icon mark (reware-mark.png) from reware-logo.png
  python .../watermark_hero_images.py --mark-only

After generating files, replace carousel slides in Website Editor (Replace image)
or update snippets.xml, then bump the module / clear frontend assets if needed.

Watermark style matches the Grandcarers hero slides: full re-ware logo on a soft
white rounded badge, bottom-right, ~16% of photo height.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow is required: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
IMG_ROOT = SCRIPT_DIR.parent / "static" / "src" / "img"
DEFAULT_LOGO = IMG_ROOT / "brand" / "reware-logo.png"
DEFAULT_HERO_DIR = IMG_ROOT / "hero"
DEFAULT_MARK_OUT = IMG_ROOT / "brand" / "reware-mark.png"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def make_mark(logo_path: Path, out_path: Path) -> None:
    """Crop the sprout/power icon from the full logo; knock out the white background."""
    logo = Image.open(logo_path).convert("RGB")
    w, h = logo.size

    icon = logo.crop((0, 0, w, int(h * 0.72)))
    gray = icon.convert("L")
    mask = gray.point(lambda p: 255 if p < 235 else 0)
    bbox = mask.getbbox()
    if bbox:
        pad = 8
        l, t, r, b = bbox
        l = max(0, l - pad)
        t = max(0, t - pad)
        r = min(icon.width, r + pad)
        b = min(icon.height, b + pad)
        icon = icon.crop((l, t, r, b))

    framed = Image.new("RGB", (icon.width + 6, icon.height + 6), (255, 255, 255))
    framed.paste(icon, (3, 3))

    sentinel = (255, 0, 255)
    cw, ch = framed.size
    for corner in ((0, 0), (cw - 1, 0), (0, ch - 1), (cw - 1, ch - 1)):
        ImageDraw.floodfill(framed, corner, sentinel, thresh=40)

    rgba = framed.convert("RGBA")
    px = rgba.load()
    for y in range(ch):
        for x in range(cw):
            if px[x, y][:3] == sentinel:
                px[x, y] = (0, 0, 0, 0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(out_path)
    print(f"wrote {out_path}  ({rgba.width}x{rgba.height})")


def watermark_photo(
    src: Path,
    dst: Path,
    logo_path: Path,
    *,
    logo_height_ratio: float = 0.16,
    margin_ratio: float = 0.03,
    badge_opacity: int = 235,
    jpeg_quality: int = 88,
) -> None:
    """Paste the full logo on a rounded white badge at the bottom-right."""
    photo = Image.open(src).convert("RGB")
    pw, ph = photo.size

    logo = Image.open(logo_path).convert("RGB")
    target_h = max(1, int(ph * logo_height_ratio))
    scale = target_h / logo.height
    logo = logo.resize((max(1, int(logo.width * scale)), target_h), Image.LANCZOS)

    pad = int(target_h * 0.16)
    radius = int(target_h * 0.14)
    badge_w = logo.width + pad * 2
    badge_h = logo.height + pad * 2
    badge = Image.new("RGB", (badge_w, badge_h), (255, 255, 255))
    badge.paste(logo, (pad, pad))

    mask = Image.new("L", (badge_w, badge_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, badge_w - 1, badge_h - 1], radius=radius, fill=badge_opacity
    )

    margin = int(ph * margin_ratio)
    x = pw - badge_w - margin
    y = ph - badge_h - margin
    photo.paste(badge, (x, y), mask)

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix.lower() in (".jpg", ".jpeg"):
        photo.save(dst, "JPEG", quality=jpeg_quality, optimize=True)
    else:
        photo.save(dst)
    print(f"wrote {dst}  ({pw}x{ph})")


def _resolve_output(src: Path, out: Path) -> Path:
    if out.is_dir():
        return out / f"{src.stem}.jpg"
    return out


def _collect_inputs(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_SUFFIXES))
        elif p.suffix.lower() in IMAGE_SUFFIXES:
            files.append(p)
        else:
            print(f"skip (not an image): {p}", file=sys.stderr)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Watermark Re-Ware hero/carousel photos with the logo badge."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="Source photo(s) or folder(s). Omit when using --mark-only.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file or directory (default: static/src/img/hero/<name>.jpg).",
    )
    parser.add_argument(
        "--logo",
        type=Path,
        default=DEFAULT_LOGO,
        help=f"Logo PNG (default: {DEFAULT_LOGO.relative_to(SCRIPT_DIR.parent.parent.parent)})",
    )
    parser.add_argument(
        "--mark-only",
        action="store_true",
        help="Only regenerate brand/reware-mark.png for the site header.",
    )
    parser.add_argument(
        "--mark-out",
        type=Path,
        default=DEFAULT_MARK_OUT,
        help="Output path for --mark-only.",
    )
    args = parser.parse_args(argv)

    if not args.logo.is_file():
        print(f"logo not found: {args.logo}", file=sys.stderr)
        return 1

    if args.mark_only:
        make_mark(args.logo, args.mark_out)
        return 0

    inputs = _collect_inputs(args.inputs)
    if not inputs:
        parser.print_help()
        print("\nProvide at least one image or folder, or use --mark-only.", file=sys.stderr)
        return 1

    if len(inputs) == 1 and args.output and not args.output.suffix:
        args.output.mkdir(parents=True, exist_ok=True)

    for src in inputs:
        if args.output:
            dst = _resolve_output(src, args.output)
        else:
            dst = DEFAULT_HERO_DIR / f"{src.stem}.jpg"
        watermark_photo(src, dst, args.logo)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
