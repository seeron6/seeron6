#!/usr/bin/env python3
"""Preprocess a source portrait for ASCII rendering.

Pipeline (per the blog technique):
  1. Remove the background with rembg (isolates the subject).
  2. Auto-crop to the subject's bounding box with a little padding.
  3. Composite onto a solid white background so empty areas map to blank
     characters in the ASCII ramp.
  4. Enhance local contrast with OpenCV CLAHE (falls back to PIL autocontrast).

Usage:
  python scripts/prep_photo.py [source-photo.jpg]

Output:
  source-prepped.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

SRC_DEFAULT = "source-photo.jpg"
OUT = "source-prepped.png"


def remove_background(img: Image.Image) -> Image.Image:
    """Return an RGBA image with the background removed, if rembg is available."""
    try:
        from rembg import remove
    except Exception as exc:  # rembg / onnxruntime not installed
        print(f"[prep] rembg unavailable ({exc}); keeping full image.")
        return img.convert("RGBA")
    print("[prep] removing background with rembg ...")
    cut = remove(img)
    if cut.mode != "RGBA":
        cut = cut.convert("RGBA")
    return cut


def autocrop_to_subject(cut: Image.Image, pad_frac: float = 0.05) -> Image.Image:
    """Crop to the alpha bounding box (the subject) plus padding."""
    alpha = np.array(cut.split()[-1])
    ys, xs = np.where(alpha > 40)
    if xs.size == 0 or ys.size == 0:
        return cut
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    pad = int(pad_frac * max(x1 - x0, y1 - y0))
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(cut.width, x1 + pad)
    y1 = min(cut.height, y1 + pad)
    return cut.crop((x0, y0, x1, y1))


def composite_on_white(cut: Image.Image) -> Image.Image:
    bg = Image.new("RGBA", cut.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, cut).convert("RGB")


def enhance_contrast(img: Image.Image) -> Image.Image:
    """CLAHE on the L channel via OpenCV; PIL autocontrast as a fallback."""
    try:
        import cv2
    except Exception as exc:
        print(f"[prep] OpenCV unavailable ({exc}); using PIL autocontrast.")
        return ImageOps.autocontrast(img, cutoff=1)
    print("[prep] applying CLAHE contrast ...")
    arr = np.array(img)
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    l = clahe.apply(l)
    merged = cv2.merge((l, a, b))
    out = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
    return Image.fromarray(out)


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(SRC_DEFAULT)
    if not src.exists():
        sys.exit(f"[prep] source photo not found: {src}")

    img = Image.open(src).convert("RGB")
    # Correct any EXIF orientation from phone cameras.
    img = ImageOps.exif_transpose(img)

    cut = remove_background(img)
    cut = autocrop_to_subject(cut)
    comp = composite_on_white(cut)
    comp = enhance_contrast(comp)

    comp.save(OUT)
    print(f"[prep] wrote {OUT} ({comp.width}x{comp.height})")


if __name__ == "__main__":
    main()
