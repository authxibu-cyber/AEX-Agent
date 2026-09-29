"""
AEX Agent — boot-splash logo.

The binary-art emblem ("Aex Agent" drawn in 0/1 pixels — crossed swords
+ shield + blockletter wordmark) lives in assets/ascii_logo.txt so its
leading whitespace is never mangled by source indentation.

Palette (Solarized-dark + gold, shared with docs/index.html):
    --bg #002b36  --bg-raise #073642  --ink #93a1a1
    --gold #b58900  --gold-bright #e6c04a  parchment #fdf6e3

Shared by the Textual TUI and the classic rich TUI.
"""
from __future__ import annotations

import os

from rich.text import Text

# ── palette ────────────────────────────────────────────────────────────────
BG = "#002b36"
BG_RAISE = "#073642"
INK = "#93a1a1"
INK_DIM = "#708282"
GOLD = "#b58900"
GOLD_BRIGHT = "#e6c04a"
PARCHMENT = "#fdf6e3"

_ASSET = os.path.join(os.path.dirname(__file__), "assets", "ascii_logo.txt")


def _load_logo() -> list:
    try:
        with open(_ASSET, encoding="utf-8") as f:
            lines = [l.rstrip() for l in f.read().splitlines()]
        while lines and not lines[-1].strip():
            lines.pop()
        return lines
    except Exception:
        return []


def _render_row(line: str, on: str, off: str) -> Text:
    """Row -> Text: '1' cells glow gold-bright, '0' cells dim solarized ink."""
    row = Text()
    for ch in line:
        if ch == "1":
            row.append("1", style=on)
        elif ch == "0":
            row.append("0", style=off)
        else:
            row.append(" ")
    return row


def logo_splash(
    title: str = "",
    subtitle: str = "",
    style: str = GOLD_BRIGHT,
    accent: str = INK,
    width: int = 0,
) -> Text:
    """Boot splash: the binary-art emblem, centered; subtitle line below.

    width: available terminal columns. When the art won't fit, falls back
    to a one-line title so nothing wraps or clips.
    """
    art = _load_logo()
    if not art:
        out = Text(title or "Merlin", style=style)
        if subtitle:
            out.append("\n" + subtitle, style=f"dim {accent}")
        return out

    logo_w = max(len(l) for l in art)

    if width and width < logo_w:
        out = Text(title or "Merlin", style=style)
        if subtitle:
            out.append("\n" + subtitle, style=f"dim {accent}")
        return out

    avail = width or (logo_w + 4)
    pad = max(0, (avail - logo_w) // 2)
    out = Text()
    for i, line in enumerate(art):
        out.append(" " * pad)
        out.append(_render_row(line, on=f"bold {style}", off=f"dim {accent}"))
        if i < len(art) - 1:
            out.append("\n")
    if subtitle:
        sub_pad = max(0, (avail - len(subtitle)) // 2)
        out.append("\n\n" + " " * sub_pad)
        out.append(subtitle, style=f"dim {accent}")
    return out