# 21-Key Lyre Auto Player 启动脚本 (管理员模式)
$ErrorActionPreference = "Stop"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Requesting administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Add FluidSynth to PATH
$env:PATH = "$ScriptDir\bin;$env:PATH"

Write-Host "[Admin Mode] Starting LyreAutoPlayer..." -ForegroundColor Green

# Run the application
& "$ScriptDir\.venv\Scripts\python.exe" "$ScriptDir\main.py"

# If error, pause
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nError occurred. Press any key to close..." -ForegroundColor Red
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
