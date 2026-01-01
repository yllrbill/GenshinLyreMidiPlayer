@echo off
:: 以管理员身份运行 LyreAutoPlayer
:: 右键此文件 -> 以管理员身份运行

cd /d "%~dp0"
echo Starting LyreAutoPlayer as Administrator...
.venv\Scripts\python.exe main.py
pause
