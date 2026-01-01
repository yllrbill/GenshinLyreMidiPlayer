@echo off
:: 自动请求管理员权限并运行 LyreAutoPlayer
:: 双击此文件即可

:: 检查是否已是管理员
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run
) else (
    goto :elevate
)

:elevate
:: 请求管理员权限
powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
exit /b

:run
cd /d "%~dp0"
echo Starting LyreAutoPlayer as Administrator...
.venv\Scripts\python.exe main.py
pause
