<#
.SYNOPSIS
    AEX Agent Native Windows PowerShell Installer.
    Installs the package, then makes `aex` resolvable on PATH (works for
    non-admin pip installs that land scripts in %APPDATA%\Python\*\Scripts).
#>

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "            AEX AGENT NATIVE WINDOWS INSTALLER            " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$repoDir = Split-Path -Parent $PSScriptRoot
Write-Host "[*] Installing AEX Agent from $repoDir..." -ForegroundColor Yellow
python -m pip install "$repoDir"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] pip install failed - see output above." -ForegroundColor Red
    exit 1
}

Write-Host "[*] Ensuring the 'aex' command is on PATH..." -ForegroundColor Yellow
python -m aex_agent doctor

Write-Host ""
Write-Host "[OK] Installation complete!" -ForegroundColor Green
Write-Host "Open a NEW terminal, then:" -ForegroundColor Cyan
Write-Host "  aex             - Launch full-screen interactive TUI (default)" -ForegroundColor White
Write-Host "  aex setup       - Configure provider / model / API key" -ForegroundColor White
Write-Host "  aex gateway     - Launch API server on :8642" -ForegroundColor White
Write-Host "  aex --help      - Show all commands" -ForegroundColor White
Write-Host ""
Write-Host "If 'aex' is still not recognized in an old terminal: open a new one,"
Write-Host "or run  python -m aex_agent doctor  to repair PATH automatically." -ForegroundColor DarkGray
