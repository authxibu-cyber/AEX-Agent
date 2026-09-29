"""
Path self-healing for the `aex` command.

Problem: `pip install` on Windows without admin rights places console scripts in
the Python *user* site Scripts dir (%APPDATA%\\Python\\PythonXY\\Scripts), which is
NOT on PATH by default — the user installs successfully, then `aex` is "not
recognized" (and on Linux, ~/.local/bin is often missing from PATH the same way).

Fix: `python -m aex_agent doctor` (and the same check at CLI startup) detects
the gap and repairs it without admin rights:

  - Windows: appends the user Scripts dir to the *user* PATH registry value and
    drops an `aex.cmd` shim into a directory already on the old PATH
    (~/.local/bin if present, else the Scripts dir), so even terminal windows
    opened before the fix resolve `aex` immediately.
  - POSIX: falls back to ~/.local/bin (bin dir convention) with an executable
    shim, and reports the PATH export line if needed.

Everything is idempotent — running twice changes nothing.
"""
from __future__ import annotations

import os
import shutil
import sys
import sysconfig
from pathlib import Path

# ── locate where pip actually put our scripts ────────────────────────────

def _scripts_dir() -> Path:
    """Directory pip installs console scripts into for this interpreter."""
    # user-site install (pip without admin / --user)
    if "--user" in sys.argv or os.environ.get("PIP_USER", "").lower() in ("1", "true"):
        base = sysconfig.get_path("scripts", scheme="nt_user" if os.name == "nt" else "posix_user")
        if base:
            return Path(base)
    # normal install — scripts sit next to the interpreter
    return Path(sysconfig.get_path("scripts") or Path(sys.executable).parent)


def _real_exe() -> Path | None:
    """Path to the installed aex launcher this interpreter resolves.

    Searches everywhere pip may have put it: interpreter dir, system scripts
    dir, user-site scripts dir (pip --user installs land there).
    """
    exe_name = "aex.exe" if os.name == "nt" else "aex"
    candidates: list[Path] = [
        Path(sys.executable).parent / exe_name,
    ]
    sd = sysconfig.get_path("scripts")
    if sd:
        candidates.append(Path(sd) / exe_name)
    # user-site schemes (where `pip install --user` / non-admin installs place scripts)
    for scheme in ("nt_user", "posix_user"):
        try:
            usd = sysconfig.get_path("scripts", scheme=scheme)
            if usd:
                candidates.append(Path(usd) / exe_name)
        except (KeyError, ValueError):
            pass
    # derive from site.getusersitepackages(): .../PythonXY/site-packages -> .../PythonXY/Scripts
    try:
        import site
        usp = site.getusersitepackages()
        if usp:
            candidates.append(Path(usp).parent / ("Scripts" if os.name == "nt" else "bin") / exe_name)
    except Exception:
        pass
    for c in candidates:
        if c.exists():
            return c
    return None


def _cmd_on_path() -> bool:
    """Does `aex` resolve on the CURRENT PATH?"""
    return shutil.which("aex") is not None


# ── repairs ──────────────────────────────────────────────────────────────

def _fix_windows_user_path(scripts_dir: Path) -> str | None:
    """Append scripts_dir to the user PATH registry value. Returns action note."""
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                current, _ = winreg.QueryValueEx(key, "Path")
                current = str(current)
            except FileNotFoundError:
                current = ""
            entries = [e for e in current.split(";") if e.strip()]
            if str(scripts_dir) in entries:
                return None  # already there
            entries.append(str(scripts_dir))
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ if "%" in current else winreg.REG_SZ, ";".join(entries))
        return f"added {scripts_dir} to user PATH (registry)"
    except OSError:
        return None


def _make_cmd_shim(target: Path, shim_dir: Path) -> str | None:
    """Drop a tiny aex.cmd that forwards to the real exe. Idempotent."""
    shim_dir.mkdir(parents=True, exist_ok=True)
    shim = shim_dir / "aex.cmd"
    body = f'@echo off\r\n"{target}" %*\r\n'
    if shim.exists() and target.as_posix() in shim.read_text(errors="replace"):
        return None
    shim.write_text(body, encoding="ascii")
    return f"shim written: {shim}"


def _make_posix_shim(target: Path, shim_dir: Path) -> str | None:
    shim_dir.mkdir(parents=True, exist_ok=True)
    shim = shim_dir / "aex"
    body = f'#!/bin/sh\nexec "{target}" "$@"\n'
    if shim.exists() and str(target) in shim.read_text(errors="replace"):
        return None
    shim.write_text(body)
    shim.chmod(0o755)
    return f"shim written: {shim}"


# ── public API ───────────────────────────────────────────────────────────

def ensure_aex_on_path(verbose: bool = True) -> dict:
    """Make `aex` resolvable. Returns {'ok': bool, 'already': bool, 'actions': [...]}.

    Safe to call at CLI startup; when everything is fine it does nothing.
    """
    result = {"ok": True, "already": False, "actions": []}
    if _cmd_on_path():
        result["already"] = True
        return result

    exe = _real_exe()
    if exe is None:
        result["ok"] = False
        result["actions"].append("aex launcher not found — reinstall with pip")
        return result

    notes: list[str] = []
    if os.name == "nt":
        scripts_dir = exe.parent  # the dir pip actually placed the launcher in
        # 1. user PATH registry append (persistent, no admin needed)
        note = _fix_windows_user_path(scripts_dir)
        if note:
            notes.append(note)
        # 2. shim in a dir already on the OLD path (works in already-open terminals)
        path_dirs = [Path(p) for p in os.environ.get("PATH", "").split(";") if p.strip()]
        home = Path.home()
        shim_dir = None
        for cand in (home / ".local" / "bin", home / "bin"):
            if cand in path_dirs:
                shim_dir = cand
                break
        if shim_dir is not None:
            note = _make_cmd_shim(exe, shim_dir)
            if note:
                notes.append(note)
        else:
            # no pre-existing user dir on PATH: drop the shim next to the exe
            # (picked up by action 1 once a new terminal opens)
            note = _make_cmd_shim(exe, scripts_dir)
            if note:
                notes.append(note)
    else:
        # POSIX: prefer ~/.local/bin; report export line if PATH lacks it
        shim_dir = Path.home() / ".local" / "bin"
        note = _make_posix_shim(exe, shim_dir)
        if note:
            notes.append(note)
        if str(shim_dir) not in os.environ.get("PATH", ""):
            notes.append(f"NOTE: add to PATH ->  export PATH=\"{shim_dir}:$PATH\"  (or restart shell)")

    result["actions"] = notes
    if verbose and notes:
        print("\n[aex] Path self-healing applied:")
        for n in notes:
            print(f"  - {n}")
        print("  Open a NEW terminal (or restart this one) for `aex` to be found everywhere.\n")
    return result


if __name__ == "__main__":
    res = ensure_aex_on_path()
    if res["already"]:
        print("[aex] `aex` already on PATH — nothing to do.")
    elif res["ok"]:
        print(f"[aex] repaired. actions: {res['actions']}")
    else:
        print("[aex] could not repair:", res["actions"])