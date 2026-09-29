#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "               EX AGENT INSTALLER (POSIX/WSL)             "
echo "=========================================================="

EX_HOME="${EX_HOME:-$HOME/.ex}"
echo "[*] Initializing EX_HOME at $EX_HOME..."
mkdir -p "$EX_HOME/memories" "$EX_HOME/skills" "$EX_HOME/sessions"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[*] Installing EX Agent from $SCRIPT_DIR..."
python3 -m pip install -e "$SCRIPT_DIR"

echo ""
echo "[✔] EX Agent installed successfully!"
echo "Run 'ex' or 'ex chat' to begin."
