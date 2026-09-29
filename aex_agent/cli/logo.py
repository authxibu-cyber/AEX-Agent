"""
AEX Agent ASCII emblem — compact winged shield beside gradient word art.
Shared splash for the Textual TUI and the classic rich TUI.
"""
from __future__ import annotations

from rich.text import Text

# Compact winged-shield (density-downsampled 2x from the original art —
# shape preserved). Leading whitespace is load-bearing, do not re-indent.
LOGO = "\n".join([
    "     -#-",
    "      #",
    "    -=%+-",
    "-***++=#=++***-",
    "*+=+: +#+ :+=+*",
    "+*:   +#+   :*+",
    ".#-   *#*   -#.",
    " %+-  %#%  -+%",
    "  %-= ### =-%",
    "   +%-###-%+",
    "     -*#*-",
    "      %",
])

# "AEX AGENT" gradient word art (as provided by the King).
WORDART = "\n".join([
    "░░░░░  ░░░░░░░ ░░   ░░       ░░░░░   ░░░░░░  ░░░░░░░ ░░░    ░░ ░░░░░░░░ ",
    "▒▒   ▒▒ ▒▒     ▒▒ ▒▒      ▒▒   ▒▒ ▒▒     ▒▒      ▒▒▒▒   ▒▒    ▒▒     ",
    "▒▒▒▒▒▒▒ ▒▒▒▒▒    ▒▒▒       ▒▒▒▒▒▒▒ ▒▒   ▒▒▒ ▒▒▒▒▒   ▒▒ ▒▒  ▒▒    ▒▒     ",
    "▓▓   ▓▓ ▓▓     ▓▓ ▓▓      ▓▓   ▓▓ ▓▓    ▓▓ ▓▓      ▓▓  ▓▓ ▓▓    ▓▓     ",
    "██   ██ ███████ ██   ██     ██   ██  ██████  ██████ ██   ████    ██     ",
])

LOGO_WIDTH = max(len(line) for line in LOGO.splitlines())
WORDART_WIDTH = max(len(line) for line in WORDART.splitlines())
SPLASH_WIDTH = LOGO_WIDTH + 2 + WORDART_WIDTH


def logo_splash(
    title: str = "",
    subtitle: str = "",
    style: str = "#e5b567",
    accent: str = "#56b6c2",
) -> Text:
    """Shield + word art side-by-side, with an optional caption line beneath."""
    out = Text(style=style)
    shield_lines = LOGO.splitlines()
    art_lines = WORDART.splitlines()
    art_rows = len(art_lines)
    # vertically center the word art against the shield
    art_top = max(0, (len(shield_lines) - art_rows) // 2)
    n_rows = max(len(shield_lines), art_rows + art_top)
    for r in range(n_rows):
        row = Text()
        if 0 <= r < len(shield_lines):
            row.append(shield_lines[r])
            pad = LOGO_WIDTH - len(shield_lines[r])
            row.append(" " * pad)
        else:
            row.append(" " * LOGO_WIDTH)
        row.append("  ")
        if art_top <= r < art_top + art_rows:
            row.append(Text(art_lines[r - art_top], style=style))
        if r < n_rows - 1:
            row.append("\n")
        out.append(row)
    if title or subtitle:
        tail = f"{title}  {subtitle}".strip()
        pad = max(0, (SPLASH_WIDTH - len(tail)) // 2)
        out.append("\n\n" + " " * pad)
        out.append(tail, style=f"bold {accent}")
    return out