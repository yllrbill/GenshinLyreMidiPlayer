# 以管理员身份启动 LyreAutoPlayer
# 右键此文件 -> 使用 PowerShell 运行

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$pythonPath = Join-Path $scriptDir ".venv\Scripts\python.exe"
$mainPath = Join-Path $scriptDir "main.py"

if (-not (Test-Path $pythonPath)) {
    Write-Host "错误: 找不到 Python: $pythonPath" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "启动 LyreAutoPlayer..." -ForegroundColor Green
& $pythonPath $mainPath
pause
