<#
.SYNOPSIS
    AEX Agent Native Windows PowerShell Installer.
    Sets up python environment, dependencies, AEX_HOME directory, and creates the 'aex' command.
#>

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "            AEX AGENT NATIVE WINDOWS INSTALLER             " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$exHome = if ($env:LOCALAPPDATA) { "$env:LOCALAPPDATA\ex" } else { "$HOME\.ex" }
Write-Host "[*] Target AEX_HOME: $exHome" -ForegroundColor Yellow

if (-not (Test-Path $exHome)) {
    New-Item -ItemType Directory -Path $exHome -Force | Out-Null
    New-Item -ItemType Directory -Path "$exHome\memories" -Force | Out-Null
    New-Item -ItemType Directory -Path "$exHome\skills" -Force | Out-Null
    New-Item -ItemType Directory -Path "$exHome\sessions" -Force | Out-Null
}

$repoDir = Split-Path -Parent $PSScriptRoot
Write-Host "[*] Installing AEX Agent in editable mode from $repoDir..." -ForegroundColor Yellow
python -m pip install -e $repoDir

Write-Host "`n[✔] Installation complete!" -ForegroundColor Green
Write-Host "You can now run AEX Agent using:" -ForegroundColor Cyan
Write-Host "  aex             - Launch full-screen interactive TUI (default)" -ForegroundColor White
Write-Host "  aex gateway     - Launch API server on :8642" -ForegroundColor White
Write-Host "  aex model       - Configure active model" -ForegroundColor White
Write-Host "  aex --help     - Show all commands`n" -ForegroundColor White
