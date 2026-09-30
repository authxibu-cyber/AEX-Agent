#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "               Merlin AGENT INSTALLER (POSIX/WSL)             "
echo "=========================================================="

MERLIN_HOME="${MERLIN_HOME:-$HOME/.merlin}"
echo "[*] Initializing MERLIN_HOME at $MERLIN_HOME..."
mkdir -p "$MERLIN_HOME/memories" "$MERLIN_HOME/skills" "$MERLIN_HOME/sessions"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[*] Installing Merlin Agent from $SCRIPT_DIR..."
python3 -m pip install -e "$SCRIPT_DIR"

echo ""
echo "[*] Ensuring the 'merlin' command is on PATH..."
python3 -m merlin_agent doctor || true

echo ""
echo "[OK] Merlin Agent installed successfully!"
echo "Open a NEW shell, then run 'merlin' or 'merlin chat' to begin."
echo "If 'merlin' is not found: run  python3 -m merlin_agent doctor  to repair PATH."
