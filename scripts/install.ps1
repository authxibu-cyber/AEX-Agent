<#
.SYNOPSIS
    EX Agent Native Windows PowerShell Installer.
    Sets up python environment, dependencies, EX_HOME directory, and creates the 'ex' command.
#>

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "            EX AGENT NATIVE WINDOWS INSTALLER             " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$exHome = if ($env:LOCALAPPDATA) { "$env:LOCALAPPDATA\ex" } else { "$HOME\.ex" }
Write-Host "[*] Target EX_HOME: $exHome" -ForegroundColor Yellow

if (-not (Test-Path $exHome)) {
    New-Item -ItemType Directory -Path $exHome -Force | Out-Null
    New-Item -ItemType Directory -Path "$exHome\memories" -Force | Out-Null
    New-Item -ItemType Directory -Path "$exHome\skills" -Force | Out-Null
    New-Item -ItemType Directory -Path "$exHome\sessions" -Force | Out-Null
}

$repoDir = Split-Path -Parent $PSScriptRoot
Write-Host "[*] Installing EX Agent in editable mode from $repoDir..." -ForegroundColor Yellow
python -m pip install -e $repoDir

Write-Host "`n[✔] Installation complete!" -ForegroundColor Green
Write-Host "You can now run EX Agent using:" -ForegroundColor Cyan
Write-Host "  ex chat        - Launch interactive terminal TUI" -ForegroundColor White
Write-Host "  ex gateway     - Launch API server on :8642" -ForegroundColor White
Write-Host "  ex model       - Configure active model" -ForegroundColor White
Write-Host "  ex --help      - Show all commands`n" -ForegroundColor White
