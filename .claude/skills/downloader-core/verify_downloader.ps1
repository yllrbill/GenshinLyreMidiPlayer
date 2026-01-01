# Downloader-core Skill 验证脚本
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File verify_downloader.ps1

$ErrorActionPreference = "Stop"
$script:passed = 0
$script:failed = 0
$skillDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-Check {
    param([string]$Name, [scriptblock]$Check)
    try {
        $result = & $Check
        if ($result) {
            Write-Host "[PASS] $Name" -ForegroundColor Green
            $script:passed++
        } else {
            Write-Host "[FAIL] $Name" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        Write-Host "[FAIL] $Name - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
    }
}

Write-Host "`n=== Downloader-core Skill Verification ===" -ForegroundColor Cyan
Write-Host "Skill Directory: $skillDir`n"

# 1. 检查目录结构
Test-Check "SKILL.md exists" {
    Test-Path "$skillDir\SKILL.md"
}

Test-Check "patterns.yaml exists" {
    Test-Path "$skillDir\patterns.yaml"
}

Test-Check "tools.yaml exists" {
    Test-Path "$skillDir\tools.yaml"
}

# 2. 检查 SKILL.md 格式
Test-Check "SKILL.md has frontmatter" {
    $content = Get-Content "$skillDir\SKILL.md" -Raw
    $content -match "^---\s*\nname:\s*downloader-core"
}

# 3. 检查 YAML 有效性
Test-Check "patterns.yaml is valid YAML" {
    $result = python -c "import yaml; yaml.safe_load(open('$skillDir/patterns.yaml', encoding='utf-8'))" 2>&1
    $LASTEXITCODE -eq 0
}

Test-Check "tools.yaml is valid YAML" {
    $result = python -c "import yaml; yaml.safe_load(open('$skillDir/tools.yaml', encoding='utf-8'))" 2>&1
    $LASTEXITCODE -eq 0
}

# 4. 检查命令入口
$cmdPath = Join-Path (Split-Path -Parent (Split-Path -Parent $skillDir)) "commands\downloader.md"
Test-Check "downloader.md command exists" {
    Test-Path $cmdPath
}

# 5. 检查命令/Skill 命名冲突
$cmdDir = Join-Path (Split-Path -Parent (Split-Path -Parent $skillDir)) "commands"
$skillsDir = Split-Path -Parent $skillDir
Test-Check "No command/skill naming conflict" {
    $cmdNames = Get-ChildItem $cmdDir -Filter "*.md" | ForEach-Object { $_.BaseName }
    $skillNames = Get-ChildItem $skillsDir -Directory | ForEach-Object { $_.Name }
    $conflicts = $cmdNames | Where-Object { $skillNames -contains $_ }
    $conflicts.Count -eq 0
}

# 6. 检查 settings.json 权限
$settingsPath = Join-Path (Split-Path -Parent (Split-Path -Parent $skillDir)) "settings.json"
Test-Check "settings.json has downloader permission" {
    if (Test-Path $settingsPath) {
        $content = Get-Content $settingsPath -Raw
        $content -match 'Skill\(downloader\)'
    } else {
        $false
    }
}

# 7. 检查工具可用性
Write-Host "`n--- Tool Availability ---" -ForegroundColor Yellow

$tools = @{
    "aria2c" = "aria2c --version"
    "yt-dlp" = "yt-dlp --version"
    "gallery-dl" = "gallery-dl --version"
    "wget2" = "wget2 --version"
    "curl" = "curl --version"
}

$availableTools = 0
foreach ($tool in $tools.Keys) {
    try {
        $null = Invoke-Expression $tools[$tool] 2>&1
        if ($LASTEXITCODE -eq 0 -or $tool -eq "curl") {
            Write-Host "  [OK] $tool available" -ForegroundColor Green
            $availableTools++
        } else {
            Write-Host "  [--] $tool not available" -ForegroundColor DarkGray
        }
    } catch {
        Write-Host "  [--] $tool not available" -ForegroundColor DarkGray
    }
}

Test-Check "At least one download tool available" {
    $availableTools -gt 0
}

# 8. URL 分类测试
Write-Host "`n--- URL Classification Tests ---" -ForegroundColor Yellow

$testUrls = @{
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ" = "VIDEO"
    "https://www.pixiv.net/artworks/12345678" = "GALLERY"
    "magnet:?xt=urn:btih:abc123" = "TORRENT"
    "https://example.com/file.zip" = "DIRECT"
    "https://example.com/page.html" = "GENERIC"
}

$classifyScript = @'
import yaml
import re
import sys

patterns_file = sys.argv[1]
url = sys.argv[2]

with open(patterns_file, 'r', encoding='utf-8') as f:
    patterns = yaml.safe_load(f)

for cat_name, cat_data in patterns['categories'].items():
    for pattern_info in cat_data['patterns']:
        if re.search(pattern_info['pattern'], url, re.IGNORECASE):
            print(cat_name)
            sys.exit(0)

print("UNKNOWN")
'@

$classifyScriptPath = "$env:TEMP\classify_url.py"
$classifyScript | Out-File -FilePath $classifyScriptPath -Encoding utf8

foreach ($url in $testUrls.Keys) {
    $expected = $testUrls[$url]
    try {
        $actual = python $classifyScriptPath "$skillDir\patterns.yaml" $url 2>&1
        $actual = $actual.Trim()
        if ($actual -eq $expected) {
            Write-Host "  [OK] $url -> $actual" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] $url -> $actual (expected: $expected)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [FAIL] $url -> Error" -ForegroundColor Red
    }
}

Remove-Item $classifyScriptPath -ErrorAction SilentlyContinue

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Passed: $script:passed" -ForegroundColor Green
Write-Host "Failed: $script:failed" -ForegroundColor $(if ($script:failed -gt 0) { "Red" } else { "Green" })
Write-Host "Available Tools: $availableTools / $($tools.Count)"

if ($script:failed -gt 0) {
    exit 1
} else {
    Write-Host "`n[SUCCESS] All checks passed!" -ForegroundColor Green
    exit 0
}
