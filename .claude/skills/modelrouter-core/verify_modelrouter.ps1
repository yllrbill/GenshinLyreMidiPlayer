# Modelrouter Verification Script
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/modelrouter-core/verify_modelrouter.ps1

$ErrorActionPreference = "Stop"
$script:passed = 0
$script:failed = 0

function Test-Check {
    param([string]$Name, [scriptblock]$Test)
    try {
        $result = & $Test
        if ($result) {
            Write-Host "[PASS] $Name" -ForegroundColor Green
            $script:passed++
        } else {
            Write-Host "[FAIL] $Name" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        Write-Host "[FAIL] $Name - $_" -ForegroundColor Red
        $script:failed++
    }
}

Write-Host "=== Modelrouter Verification ===" -ForegroundColor Cyan
Write-Host ""

# 1. Skill structure
Test-Check "SKILL.md exists" {
    Test-Path ".claude/skills/modelrouter-core/SKILL.md"
}

Test-Check "patterns.yaml exists" {
    Test-Path ".claude/skills/modelrouter-core/patterns.yaml"
}

Test-Check "Command file exists" {
    Test-Path ".claude/commands/modelrouter.md"
}

# 2. Frontmatter validation
Test-Check "SKILL.md has valid frontmatter" {
    $content = Get-Content ".claude/skills/modelrouter-core/SKILL.md" -Raw
    $content -match "^---\s*\nname:\s*modelrouter-core"
}

# 3. patterns.yaml valid YAML
Test-Check "patterns.yaml is valid YAML" {
    python -c "import yaml; yaml.safe_load(open('.claude/skills/modelrouter-core/patterns.yaml', encoding='utf-8'))" 2>$null
    $LASTEXITCODE -eq 0
}

# 4. No naming conflicts
Test-Check "No command/skill naming conflict" {
    $cmds = Get-ChildItem ".claude/commands" -Filter "*.md" -ErrorAction SilentlyContinue | ForEach-Object { $_.BaseName }
    $skills = Get-ChildItem ".claude/skills" -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }
    $conflicts = $cmds | Where-Object { $skills -contains $_ }
    $conflicts.Count -eq 0
}

# 5. State directory writable
Test-Check "State directory writable" {
    $testFile = ".claude/state/modelrouter/verify_test.tmp"
    New-Item -ItemType File -Path $testFile -Force | Out-Null
    $exists = Test-Path $testFile
    Remove-Item $testFile -Force -ErrorAction SilentlyContinue
    $exists
}

# 6. Settings.json has permission
Test-Check "settings.json has modelrouter permission" {
    $settings = Get-Content ".claude/settings.json" -Raw | ConvertFrom-Json
    $settings.permissions.allow -contains "Skill(modelrouter)" -or
    $settings.permissions.allow -contains "Skill(modelrouter:*)"
}

# 7. No secret leaks
Test-Check "No hardcoded secrets in skill files" {
    $result = & rg -l "(api_key|token|password)\s*[:=]\s*[^$\s<`"']+" ".claude/skills/modelrouter-core/" 2>&1
    [string]::IsNullOrEmpty($result) -or $result -match "No files"
}

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Passed: $script:passed" -ForegroundColor Green
Write-Host "Failed: $script:failed" -ForegroundColor $(if ($script:failed -gt 0) { "Red" } else { "Green" })

if ($script:failed -gt 0) {
    exit 1
} else {
    Write-Host ""
    Write-Host "All checks passed!" -ForegroundColor Green
    exit 0
}
