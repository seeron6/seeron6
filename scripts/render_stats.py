#!/usr/bin/env python3
"""Render self-contained GitHub stats cards from data/github-stats.json.

Produces two clean, theme-aware SVG cards (numbers + language breakdown) with a
subtle staggered "power-on" glow. Every frame keeps content fully visible, so
the cards render in any context and on both GitHub themes. Values are white on
dark, black on light — matching the ASCII portrait.

Usage:
  python scripts/render_stats.py

Outputs:
  github-stats.svg
  top-langs.svg
"""
from __future__ import annotations

import html
import json
from pathlib import Path

DATA = Path("data/github-stats.json")
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def base_style(extra: str = "") -> str:
    return f"""<style>
  text{{font-family:{FONT}}}
  .panel{{fill:#0d1117;stroke:#30363d}}
  .title{{fill:#58a6ff;font-weight:700;font-size:17px}}
  .label{{fill:#c9d1d9;font-size:14px}}
  .value{{fill:#ffffff;font-weight:700;font-size:14px}}
  .muted{{fill:#8b949e;font-size:13px}}
  .accent{{fill:#58a6ff}}
  .rule{{stroke:#21262d}}
  @media (prefers-color-scheme: light){{
    .panel{{fill:#ffffff;stroke:#d0d7de}}
    .title{{fill:#0969da}} .label{{fill:#1f2328}} .value{{fill:#000000}}
    .muted{{fill:#59636e}} .accent{{fill:#0969da}} .rule{{stroke:#d8dee4}}
  }}
  .rv{{animation:glow 2.4s ease-out forwards}}
  @keyframes glow{{0%{{filter:none}}9%{{filter:drop-shadow(0 0 5px currentColor)}}
    26%{{filter:none}}100%{{filter:none}}}}
  @media (prefers-reduced-motion: reduce){{.rv{{animation:none}}}}
{extra}
</style>"""


def stats_card(d: dict) -> str:
    W, H, PAD = 480, 200, 24
    rows = [
        ("Commits (last year)", d["commits_year"]),
        ("Pull Requests", d["prs"]),
        ("Public Repositories", d["repos"]),
        ("Stars Earned", d["stars"]),
        ("Followers", d["followers"]),
    ]
    delays = "\n".join(f"  #s{i}{{animation-delay:{0.15+i*0.12:.2f}s}}" for i in range(len(rows)))
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" role="img" aria-label="{esc(d["name"])} GitHub stats">',
        base_style(delays),
        f'<rect class="panel" x="1" y="1" width="{W-2}" height="{H-2}" rx="10" stroke-width="1.5"/>',
        f'<text class="title" x="{PAD}" y="36">{esc(d["name"])}’s GitHub Stats</text>',
        f'<line class="rule" x1="{PAD}" y1="50" x2="{W-PAD}" y2="50" stroke-width="1"/>',
    ]
    y = 80
    for i, (label, val) in enumerate(rows):
        p.append(
            f'<g class="rv" id="s{i}">'
            f'<circle class="accent" cx="{PAD+5}" cy="{y-5}" r="3.5"/>'
            f'<text class="label" x="{PAD+18}" y="{y}">{esc(label)}</text>'
            f'<text class="value" x="{W-PAD}" y="{y}" text-anchor="end">{esc(val)}</text>'
            f'</g>'
        )
        y += 23
    p.append("</svg>")
    return "\n".join(p)


def langs_card(d: dict) -> str:
    W, H, PAD = 360, 200, 24
    langs = d["languages"]
    delays = "\n".join(f"  #g{i}{{animation-delay:{0.2+i*0.1:.2f}s}}" for i in range(len(langs)))
    bar_x, bar_y, bar_w, bar_h = PAD, 70, W - 2 * PAD, 11

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" role="img" aria-label="Most used languages">',
        base_style(delays),
        f'<rect class="panel" x="1" y="1" width="{W-2}" height="{H-2}" rx="10" stroke-width="1.5"/>',
        f'<text class="title" x="{PAD}" y="36">Most Used Languages</text>',
        f'<line class="rule" x1="{PAD}" y1="50" x2="{W-PAD}" y2="50" stroke-width="1"/>',
        # rounded stacked bar
        f'<clipPath id="barclip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" '
        f'height="{bar_h}" rx="{bar_h/2}"/></clipPath>',
        f'<g clip-path="url(#barclip)">',
    ]
    x = bar_x
    scale = bar_w / max(sum(l["pct"] for l in langs), 1)
    for l in langs:
        seg = l["pct"] * scale
        p.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{seg+0.6:.1f}" height="{bar_h}" '
                 f'fill="{esc(l["color"])}"/>')
        x += seg
    p.append("</g>")

    # legend, two columns
    col_w = (W - 2 * PAD) / 2
    ly0 = 104
    for i, l in enumerate(langs):
        col, row = i % 2, i // 2
        lx = PAD + col * col_w
        ly = ly0 + row * 26
        p.append(
            f'<g class="rv" id="g{i}">'
            f'<circle cx="{lx+5}" cy="{ly-4}" r="5.5" fill="{esc(l["color"])}"/>'
            f'<text class="label" x="{lx+18}" y="{ly}">{esc(l["name"])}</text>'
            f'<text class="muted" x="{lx+col_w-14}" y="{ly}" text-anchor="end">{l["pct"]}%</text>'
            f'</g>'
        )
    p.append("</svg>")
    return "\n".join(p)


def main() -> None:
    d = json.loads(DATA.read_text())
    Path("github-stats.svg").write_text(stats_card(d), encoding="utf-8")
    Path("top-langs.svg").write_text(langs_card(d), encoding="utf-8")
    print(f"[stats] wrote github-stats.svg + top-langs.svg for {d['user']}")


if __name__ == "__main__":
    main()
