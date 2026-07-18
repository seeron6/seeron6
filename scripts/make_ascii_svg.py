#!/usr/bin/env python3
"""Render the prepped portrait as an animated ASCII-art SVG.

The image is downsampled to a character grid. Brightness drives character
density (dark pixels -> dense glyphs, white background -> blank space), so the
portrait emerges as monochrome "ink" that reads on both light and dark GitHub
themes. Each row is revealed by a staggered left-to-right wipe (SMIL), and the
animation freezes on its final frame.

Usage:
  python scripts/make_ascii_svg.py [source-prepped.png]

Output:
  seeron-ascii.svg
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SRC_DEFAULT = "source-prepped.png"
OUT = "seeron-ascii.svg"

# Density ramp: index 0 = lightest (blank), last = darkest (most ink).
RAMP = " .`:-=+*cs#%@"

# Character grid width (columns). Rows are derived to preserve aspect.
COLS = 92
# Monospace cell geometry (em fractions). Courier-like advance width ~0.6em,
# line height 1.15em -> each cell is roughly twice as tall as wide.
CHAR_W = 0.60
LINE_H = 1.15
FONT_PX = 13.0

# Background is white after prep; treat near-white as blank space.
WHITE_CUTOFF = 244
# Contrast-stretch percentiles computed over the subject (non-white) pixels.
LO_PCT, HI_PCT = 4, 96

# Ink colour: pure WHITE on dark themes, pure BLACK on light themes.
# The always-visible "base" layer is drawn at reduced opacity (static-safe on
# any renderer); the full-opacity "lit" layer wipes in per row on top.
INK_DARK = "#ffffff"      # white on a dark background
INK_LIGHT = "#000000"     # black on a light background
BASE_OPACITY = 0.55       # resting visibility of the base layer
BG = "none"               # transparent background
WIPE_DUR = 0.5            # seconds for one row to wipe in
ROW_STAGGER = 0.026       # seconds between consecutive rows starting


def load_grid(src: Path):
    img = Image.open(src).convert("L")
    aspect = img.height / img.width
    rows = max(1, int(round(COLS * aspect * (CHAR_W / LINE_H))))
    small = img.resize((COLS, rows), Image.LANCZOS)
    return np.asarray(small, dtype=np.float32), rows


def to_chars(gray: np.ndarray) -> list[str]:
    bg_mask = gray >= WHITE_CUTOFF
    subject = gray[~bg_mask]
    if subject.size:
        lo = float(np.percentile(subject, LO_PCT))
        hi = float(np.percentile(subject, HI_PCT))
    else:
        lo, hi = 0.0, 255.0
    if hi <= lo:
        hi = lo + 1.0
    # Normalize brightness to 0..1, then invert so dark -> more ink.
    norm = np.clip((gray - lo) / (hi - lo), 0.0, 1.0)
    ink = 1.0 - norm
    idx = np.rint(ink * (len(RAMP) - 1)).astype(int)

    lines = []
    for r in range(gray.shape[0]):
        chars = []
        for c in range(gray.shape[1]):
            if bg_mask[r, c]:
                chars.append(" ")
            else:
                chars.append(RAMP[idx[r, c]])
        # Trim trailing spaces (keeps the SVG smaller; leading kept for align).
        lines.append("".join(chars).rstrip())
    return lines


def build_svg(lines: list[str], rows: int) -> str:
    char_w = FONT_PX * CHAR_W
    line_h = FONT_PX * LINE_H
    width = round(COLS * char_w, 1)
    height = round(rows * line_h + FONT_PX * 0.4, 1)

    # Per-row wipe delays applied only to the "lit" layer.
    delays = "\n".join(
        f"  #l{i}{{animation-delay:{round(i * ROW_STAGGER, 3)}s}}"
        for i, line in enumerate(lines) if line
    )

    style = f"""<style>
  text{{font-family:'Courier New',Courier,monospace;font-size:{FONT_PX}px;white-space:pre}}
  .base{{fill:{INK_DARK};opacity:{BASE_OPACITY}}}
  .lit{{fill:{INK_DARK};animation:wipe {WIPE_DUR}s cubic-bezier(.4,0,.2,1) both}}
  @keyframes wipe{{from{{clip-path:inset(0 100% 0 0)}}to{{clip-path:inset(0 0 0 0)}}}}
  @media (prefers-color-scheme: light){{
    .base{{fill:{INK_LIGHT}}}
    .lit{{fill:{INK_LIGHT}}}
  }}
  @media (prefers-reduced-motion: reduce){{.lit{{animation:none;clip-path:none}}}}
{delays}
</style>"""

    def layer(group_cls: str, text_cls: str, id_prefix: str | None) -> list[str]:
        # group_cls carries inherited fill; per-row animation must live on the
        # individual <text> elements (with ids) so the stagger delays apply.
        out = [f'<g class="{group_cls}" xml:space="preserve">']
        for i, line in enumerate(lines):
            if not line:
                continue
            y = round((i + 0.82) * line_h, 2)
            text = html.escape(line, quote=True)
            attrs = ""
            if id_prefix:
                attrs += f'id="{id_prefix}{i}" '
            if text_cls:
                attrs += f'class="{text_cls}" '
            out.append(
                f'<text {attrs}x="0" y="{y}" '
                f'textLength="{round(len(line) * char_w, 2)}" '
                f'lengthAdjust="spacingAndGlyphs">{text}</text>'
            )
        out.append("</g>")
        return out

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="ASCII portrait of Seeron Sivashankar">',
        style,
        f'<rect width="100%" height="100%" fill="{BG}"/>',
    ]
    parts += layer("base", "", None)     # always-visible dim portrait (group fill)
    parts += layer("", "lit", "l")       # bright portrait, wipes in per row
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(SRC_DEFAULT)
    if not src.exists():
        sys.exit(f"[ascii] prepped image not found: {src} (run prep_photo.py first)")
    gray, rows = load_grid(src)
    lines = to_chars(gray)
    svg = build_svg(lines, rows)
    Path(OUT).write_text(svg, encoding="utf-8")
    print(f"[ascii] wrote {OUT}  grid={COLS}x{rows}  rows_drawn={sum(1 for l in lines if l)}")


if __name__ == "__main__":
    main()
