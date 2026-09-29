#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "               AEX AGENT INSTALLER (POSIX/WSL)             "
echo "=========================================================="

AEX_HOME="${AEX_HOME:-$HOME/.aex}"
echo "[*] Initializing AEX_HOME at $AEX_HOME..."
mkdir -p "$AEX_HOME/memories" "$AEX_HOME/skills" "$AEX_HOME/sessions"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[*] Installing AEX Agent from $SCRIPT_DIR..."
python3 -m pip install -e "$SCRIPT_DIR"

echo ""
echo "[*] Ensuring the 'aex' command is on PATH..."
python3 -m aex_agent doctor || true

echo ""
echo "[OK] AEX Agent installed successfully!"
echo "Open a NEW shell, then run 'aex' or 'aex chat' to begin."
echo "If 'aex' is not found: run  python3 -m aex_agent doctor  to repair PATH."
