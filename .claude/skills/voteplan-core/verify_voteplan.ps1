# Voteplan Verification Script
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/voteplan/verify_voteplan.ps1 <vote_id>
#
# Patterns reference: patterns.yaml (Single Source of Truth)

param([string]$vote_id)

if (-not $vote_id) {
    Write-Host "Usage: .\verify_voteplan.ps1 <vote_id>"
    Write-Host "Example: .\verify_voteplan.ps1 251228153042-a7f3"
    exit 1
}

$fail_count = 0
$warn_count = 0
$error_count = 0
$pub_dir = ".claude/state/planvote-search/$vote_id"
$main_output_path = ".claude/state/voteplan.$vote_id.yaml"

# === Sensitive Patterns (from patterns.yaml - Single Source of Truth) ===
$PATTERN_TOKEN = '(tvly-|sk-|xai-)[A-Za-z0-9_-]{10,}'
$PATTERN_URL_SECRET = 'https?://[^\s"]+[?&](api_key|apikey|token|access_token|tavilyApiKey)=[^&\s"]+'
$PATTERN_PRAGMA = 'pragma:\s*allowlist-secret'
$PATTERN_TIMESTAMP_RFC3339 = '^\s*timestamp:\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z'

# === rg Exit Code Semantics ===
# 0 = matches found
# 1 = no matches found (OK for sensitive scans)
# 2 = error (file not found, permission denied, etc.)

# Helper function: Run rg and check exit code for sensitive scans
# Returns: "OK" (exit 1), "FAIL" (exit 0), "ERROR" (exit 2)
function Test-NoSensitive {
    param([string]$Pattern, [string]$Path, [switch]$Pcre2)

    if (-not (Test-Path $Path)) {
        return "ERROR_PATH"
    }

    if ($Pcre2) {
        $null = rg -q -P $Pattern $Path 2>$null
    } else {
        $null = rg -q $Pattern $Path 2>$null
    }
    $exitCode = $LASTEXITCODE

    switch ($exitCode) {
        0 { return "FAIL" }      # matches found - sensitive leak!
        1 { return "OK" }        # no matches - safe
        2 { return "ERROR" }     # rg error
        default { return "ERROR" }
    }
}

# Helper function: Run rg and check exit code for required patterns
# Returns: "OK" (exit 0), "FAIL" (exit 1), "ERROR" (exit 2)
function Test-HasPattern {
    param([string]$Pattern, [string]$Path, [switch]$Pcre2)

    if (-not (Test-Path $Path)) {
        return "ERROR_PATH"
    }

    if ($Pcre2) {
        $null = rg -q -P $Pattern $Path 2>$null
    } else {
        $null = rg -q $Pattern $Path 2>$null
    }
    $exitCode = $LASTEXITCODE

    switch ($exitCode) {
        0 { return "OK" }        # matches found - pattern exists
        1 { return "FAIL" }      # no matches - pattern missing
        2 { return "ERROR" }     # rg error
        default { return "ERROR" }
    }
}

Write-Host "=== Voteplan Verification: $vote_id ===" -ForegroundColor Cyan
Write-Host "Patterns from: patterns.yaml (Single Source of Truth)"
Write-Host ""

# 1. Main output exists
Write-Host "[1/10] Checking main output..." -ForegroundColor Yellow
if (-not (Test-Path $main_output_path)) {
    Write-Host "  [FAIL] Main output not found: $main_output_path" -ForegroundColor Red
    $fail_count++
} else {
    Write-Host "  [OK] Main output exists" -ForegroundColor Green
}

# 2. Envelope-first
Write-Host "[2/10] Checking envelope-first..." -ForegroundColor Yellow
$first = (Get-Content $main_output_path -TotalCount 1 -ErrorAction SilentlyContinue)
if ($first -ne "envelope:") {
    Write-Host "  [FAIL] Envelope-first violation (got: $first)" -ForegroundColor Red
    $fail_count++
} else {
    Write-Host "  [OK] Envelope-first compliant" -ForegroundColor Green
}

# 3. Sensitive scans (using exit code semantics)
Write-Host "[3/10] Scanning for sensitive tokens..." -ForegroundColor Yellow

# 3a. Token pattern in public directory
$result_token = Test-NoSensitive -Pattern $PATTERN_TOKEN -Path $pub_dir -Pcre2
switch ($result_token) {
    "OK" { Write-Host "  [OK] No sensitive tokens in public artifacts" -ForegroundColor Green }
    "FAIL" {
        Write-Host "  [FAIL] Sensitive token detected in public artifacts" -ForegroundColor Red
        $fail_count++
    }
    "ERROR" {
        Write-Host "  [ERROR] rg error scanning for tokens" -ForegroundColor Magenta
        $error_count++
    }
    "ERROR_PATH" {
        Write-Host "  [ERROR] Path not found: $pub_dir" -ForegroundColor Magenta
        $error_count++
    }
}

# 3b. URL with secret params
$result_url = Test-NoSensitive -Pattern $PATTERN_URL_SECRET -Path $pub_dir -Pcre2
switch ($result_url) {
    "OK" { Write-Host "  [OK] No secret URLs in public artifacts" -ForegroundColor Green }
    "FAIL" {
        Write-Host "  [FAIL] URL with secret parameter detected" -ForegroundColor Red
        $fail_count++
    }
    "ERROR" {
        Write-Host "  [ERROR] rg error scanning for secret URLs" -ForegroundColor Magenta
        $error_count++
    }
    "ERROR_PATH" { } # Already reported
}

# 3c. Pragma in public artifacts (forbidden)
$result_pragma = Test-NoSensitive -Pattern $PATTERN_PRAGMA -Path $pub_dir
switch ($result_pragma) {
    "OK" { Write-Host "  [OK] No forbidden pragma in public artifacts" -ForegroundColor Green }
    "FAIL" {
        Write-Host "  [FAIL] Forbidden pragma found in public artifacts" -ForegroundColor Red
        $fail_count++
    }
    "ERROR" {
        Write-Host "  [ERROR] rg error scanning for pragma" -ForegroundColor Magenta
        $error_count++
    }
    "ERROR_PATH" { } # Already reported
}

# 3d. Token pattern in main output
$result_main_token = Test-NoSensitive -Pattern $PATTERN_TOKEN -Path $main_output_path -Pcre2
switch ($result_main_token) {
    "OK" { Write-Host "  [OK] No sensitive tokens in main output" -ForegroundColor Green }
    "FAIL" {
        Write-Host "  [FAIL] Sensitive token detected in main output" -ForegroundColor Red
        $fail_count++
    }
    "ERROR" {
        Write-Host "  [ERROR] rg error scanning main output" -ForegroundColor Magenta
        $error_count++
    }
    "ERROR_PATH" { } # Already reported in check 1
}

# 4. Candidates count
Write-Host "[4/10] Checking candidates..." -ForegroundColor Yellow
$candidates = @(Get-ChildItem "$pub_dir/candidates/plan_*.yaml" -ErrorAction SilentlyContinue | Sort-Object Name)
$candidates_count = $candidates.Count
if ($candidates_count -lt 2) {
    Write-Host "  [FAIL] Too few candidates: $candidates_count (expected 2-4)" -ForegroundColor Red
    $fail_count++
} elseif ($candidates_count -gt 4) {
    Write-Host "  [WARN] Too many candidates: $candidates_count (expected 2-4)" -ForegroundColor Yellow
    $warn_count++
} else {
    Write-Host "  [OK] Candidates count: $candidates_count" -ForegroundColor Green
}

# 5. score_log exists and has required fields
Write-Host "[5/10] Checking score_log.yaml..." -ForegroundColor Yellow
$score_log_path = "$pub_dir/score_log.yaml"
$score_log = $null
if (-not (Test-Path $score_log_path)) {
    Write-Host "  [FAIL] score_log.yaml not found" -ForegroundColor Red
    $fail_count++
} else {
    Write-Host "  [OK] score_log.yaml exists" -ForegroundColor Green
    $score_log = Get-Content $score_log_path -Raw -ErrorAction SilentlyContinue

    # Check required fields
    $required = @('candidates:', 'ranking:', 'winner:')
    foreach ($field in $required) {
        if ($score_log -notmatch [regex]::Escape($field)) {
            Write-Host "  [FAIL] Missing field: $field" -ForegroundColor Red
            $fail_count++
        }
    }
}

# 6. query_manifest.yaml exists and has required fields
Write-Host "[6/10] Checking query_manifest.yaml..." -ForegroundColor Yellow
$manifest_path = "$pub_dir/query_manifest.yaml"
if (-not (Test-Path $manifest_path)) {
    Write-Host "  [FAIL] query_manifest.yaml not found" -ForegroundColor Red
    $fail_count++
} else {
    Write-Host "  [OK] query_manifest.yaml exists" -ForegroundColor Green
    $manifest = Get-Content $manifest_path -Raw -ErrorAction SilentlyContinue

    # Check required fields
    $manifest_required = @('vote_id:', 'timestamp:', 'tools:', 'queries:')
    foreach ($field in $manifest_required) {
        if ($manifest -notmatch [regex]::Escape($field)) {
            Write-Host "  [FAIL] Missing field in query_manifest: $field" -ForegroundColor Red
            $fail_count++
        }
    }
}

# 7. Tie-breaker completeness
Write-Host "[7/10] Checking tie-breaker..." -ForegroundColor Yellow
if ($score_log -and ($score_log -match 'tiebreak_applied:\s*true')) {
    if ($score_log -notmatch 'tiebreak_field:') {
        Write-Host "  [FAIL] tiebreak_field missing" -ForegroundColor Red
        $fail_count++
    } else {
        Write-Host "  [OK] Tie-breaker fields complete" -ForegroundColor Green
    }
} else {
    Write-Host "  [OK] No tie-break applied (or not applicable)" -ForegroundColor Green
}

# 8. Scoring formula
Write-Host "[8/10] Checking scoring formula..." -ForegroundColor Yellow
if ($score_log -and ($score_log -notmatch 'total = 3 \* success \+ 2 \* evidence \+ 1 \* conciseness \+ 2 \* risk_score')) {
    Write-Host "  [WARN] Scoring formula may not match expected format" -ForegroundColor Yellow
    $warn_count++
} else {
    Write-Host "  [OK] Scoring formula matches" -ForegroundColor Green
}

# 9. Winner consistency
Write-Host "[9/10] Checking winner consistency..." -ForegroundColor Yellow
$main_output = Get-Content $main_output_path -Raw -ErrorAction SilentlyContinue
if ($main_output -and ($main_output -notmatch 'new_plan:')) {
    Write-Host "  [FAIL] Main output missing new_plan" -ForegroundColor Red
    $fail_count++
} else {
    Write-Host "  [OK] Main output contains new_plan" -ForegroundColor Green
}

# 10. Timestamp RFC3339 format check (allows optional fractional seconds)
Write-Host "[10/10] Checking timestamp RFC3339 format..." -ForegroundColor Yellow
$result_timestamp = Test-HasPattern -Pattern $PATTERN_TIMESTAMP_RFC3339 -Path $main_output_path
switch ($result_timestamp) {
    "OK" { Write-Host "  [OK] Timestamp is RFC3339 compliant" -ForegroundColor Green }
    "FAIL" {
        Write-Host "  [FAIL] timestamp not in RFC3339 format (expected: YYYY-MM-DDTHH:MM:SS[.fff]Z)" -ForegroundColor Red
        $fail_count++
    }
    "ERROR" {
        Write-Host "  [ERROR] rg error checking timestamp" -ForegroundColor Magenta
        $error_count++
    }
    "ERROR_PATH" { } # Already reported
}

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Checks: 10 | Fails: $fail_count | Warnings: $warn_count | Errors: $error_count"

if ($error_count -gt 0) {
    Write-Host "[ERROR] $error_count error(s) occurred during verification" -ForegroundColor Magenta
    exit 2
} elseif ($fail_count -eq 0) {
    if ($warn_count -gt 0) {
        Write-Host "[PASS] All checks passed with $warn_count warning(s) for vote_id: $vote_id" -ForegroundColor Yellow
    } else {
        Write-Host "[PASS] All checks passed for vote_id: $vote_id" -ForegroundColor Green
    }
    exit 0
} else {
    Write-Host "[FAIL] $fail_count check(s) failed" -ForegroundColor Red
    exit 1
}
