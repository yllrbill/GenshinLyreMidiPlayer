@echo off
:: Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: Set working directory
cd /d "%~dp0"

:: Add FluidSynth to PATH
set PATH=%~dp0bin;%PATH%

:: Run the application
echo [Admin Mode] Starting LyreAutoPlayer...
.venv\Scripts\python.exe main.py

if %errorlevel% neq 0 (
    echo.
    echo Error occurred. Press any key to close...
    pause >nul
)
