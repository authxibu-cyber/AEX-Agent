"""
AEX Agent — Angel Wish theme.
Blackletter gothic display (figlet 'gothic', echoing the landing page's
Angel Wish font), Solarized-dark + gold palette lifted from docs/index.html:

    --bg #002b36  --bg-raise #073642  --ink #93a1a1
    --gold #b58900  --gold-bright #e6c04a

Shared by the Textual TUI and the classic rich TUI.
"""
from __future__ import annotations

from rich.text import Text

# ── Angel Wish palette (from docs/index.html :root) ──────────────────────
BG = "#002b36"
BG_RAISE = "#073642"
INK = "#93a1a1"
INK_DIM = "#708282"
GOLD = "#b58900"
GOLD_BRIGHT = "#e6c04a"
PARCHMENT = "#fdf6e3"

# 'AEX Agent' — figlet gothic (blackletter). Leading whitespace is
# load-bearing; do not re-indent.
GOTHIC = "\n".join([
    "  ___              _                ___                           ",
    " -   -_,   ,- _~, - -    /`        -   -_,                     ,  ",
    "(  ~/||   (' /| /   \\  /         (  ~/||    _                ||  ",
    "(  / ||  ((  ||/=    \\/          (  / ||   / \\  _-_  \\/\\ =||= ",
    " \\/==||  ((  ||     ==/\\==         \\/==||  || || || \\ || ||  ||  ",
    " /_ _||   ( / |      / \\          /_ _||  || || ||/   || ||  ||  ",
    "(  - \\,   -____- \\/   \\,       (  - \\, \\_-| \\,/  \\ \\  \\, ",
    "                                            /  \\                  ",
    "                                           '----`                 ",
])

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

GOTHIC_WIDTH = max(len(l) for l in GOTHIC.splitlines())
LOGO_WIDTH = max(len(l) for l in LOGO.splitlines())


def logo_splash(
    title: str = "",
    subtitle: str = "",
    style: str = GOLD_BRIGHT,
    accent: str = INK,
) -> Text:
    """Angel Wish splash: shield on the left, gothic blackletter beside it."""
    out = Text(style=style)
    shield = LOGO.splitlines()
    goth = GOTHIC.splitlines()
    art_top = max(0, (len(shield) - len(goth)) // 2)
    n_rows = max(len(shield), art_top + len(goth))
    for r in range(n_rows):
        row = Text()
        if r < len(shield):
            row.append(shield[r])
            row.append(" " * (LOGO_WIDTH - len(shield[r])))
        else:
            row.append(" " * LOGO_WIDTH)
        row.append("  ")
        if art_top <= r < art_top + len(goth):
            row.append(Text(goth[r - art_top], style=style))
        if r < n_rows - 1:
            row.append("\n")
        out.append(row)
    if subtitle:
        pad = max(0, (LOGO_WIDTH + 2 + GOTHIC_WIDTH - len(subtitle)) // 2)
        out.append("\n\n" + " " * pad)
        out.append(subtitle, style=f"dim {accent}")
    return out