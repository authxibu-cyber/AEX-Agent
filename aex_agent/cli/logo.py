"""
AEX Agent ASCII emblem — the winged shield.
Shared splash for the Textual TUI and the classic rich TUI.
"""
from __future__ import annotations

from rich.text import Text

# Winged-shield emblem — leading whitespace is load-bearing, do not re-indent.
LOGO = "\n".join([
    "                                                      ",
    "                                        ####",
    "                                         ##",
    "                                         ##",
    "                                         ##",
    "                                      #++++++#",
    "                                        %###",
    "                             ...-%##### %##% #####%-...",
    "                            ###%#::     %##%     ::#%###",
    "                           .## -%##*=.  %##%  .=*##%- ##.",
    "                            ## =        ####        = ##",
    "                            ## =        ####        = ##",
    "                            ##:.+       ####       +.:##",
    "                            +#* *       ####       * *#+",
    "                             ## +      :####:      + ##",
    "                             *#+ *     -####-     * +#*",
    "                              ##:.=    *####*    =.:##",
    "                               ##  =   ######   =  ##",
    "                                ##  #  ######  #  ##",
    "                                 ###   ######   ###",
    "                                   ### ###### ###",
    "                                     # -####- #",
    "                                        ####",
    "                                        :##:",
    "                                         **",
])

LOGO_WIDTH = max(len(line) for line in LOGO.splitlines())


def logo_splash(
    title: str,
    subtitle: str = "",
    style: str = "#e5b567",
    accent: str = "#56b6c2",
) -> Text:
    """Emblem + a centered title/subtitle line beneath it, as one rich Text."""
    out = Text(LOGO, style=style)
    tail = f"{title}  {subtitle}".strip() if subtitle else title
    pad = max(0, (LOGO_WIDTH - len(tail)) // 2)
    out.append("\n" + " " * pad + tail, style=f"bold {accent}")
    return out