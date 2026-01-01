# Voteplan Verification Checklist

> **推荐**：直接运行 `verify_voteplan.ps1` 脚本而非复制粘贴下方命令。
> ```powershell
> powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/voteplan/verify_voteplan.ps1 <vote_id>
> ```

## 敏感扫描 Patterns

> **单一事实源**：[patterns.yaml](patterns.yaml)
>
> 所有检查必须使用 patterns.yaml 中定义的正则表达式。

| Pattern | 用途 |
|---------|------|
| `PATTERN_TOKEN_PCRE2` | API tokens (tvly-, sk-, xai-) |
| `PATTERN_URL_SECRET_PCRE2` | URL 中的敏感参数 |
| `PATTERN_PRAGMA` | allowlist pragma（禁止在公开工件） |
| `PATTERN_TIMESTAMP_RFC3339` | 时间戳格式验证（允许可选小数秒） |

### rg Exit Code 语义

| Exit Code | 含义 | 敏感扫描结果 |
|-----------|------|-------------|
| 0 | 有匹配 | **FAIL** - 发现敏感信息 |
| 1 | 无匹配 | **OK** - 安全 |
| 2 | 错误 | **ERROR** - 路径/权限问题 |

---

## 最小验收清单

在 `/voteplan` 执行完成后，验证以下所有项目：

---

## 1. 目录结构验证

```powershell
$vote_id = "<VOTE_ID>"  # 替换为实际 vote_id

# 公开工件目录
Test-Path ".claude/state/planvote-search/$vote_id"
Test-Path ".claude/state/planvote-search/$vote_id/summary.md"
Test-Path ".claude/state/planvote-search/$vote_id/score_log.yaml"
Test-Path ".claude/state/planvote-search/$vote_id/candidates"
Test-Path ".claude/state/planvote-search/$vote_id/query_manifest.yaml"  # 可复跑

# 候选计划（至少 2 个）
@(Get-ChildItem ".claude/state/planvote-search/$vote_id/candidates/plan_*.yaml" | Sort-Object Name).Count -ge 2

# 主输出
Test-Path ".claude/state/voteplan.$vote_id.yaml"

# 私有目录（可选，有敏感内容时才创建）
# Test-Path ".claude/state/private/planvote/$vote_id"
```

**预期**: 全部返回 `True`

---

## 2. Envelope 合规性验证

```powershell
$vote_id = "<VOTE_ID>"

# 主输出第一行必须是 "envelope:"
(Get-Content ".claude/state/voteplan.$vote_id.yaml" -TotalCount 1) -eq "envelope:"

# score_log 第一行必须是 "envelope:"
(Get-Content ".claude/state/planvote-search/$vote_id/score_log.yaml" -TotalCount 1) -eq "envelope:"

# 每个候选计划第一行必须是 "envelope:"（排序遍历）
Get-ChildItem ".claude/state/planvote-search/$vote_id/candidates/plan_*.yaml" | Sort-Object Name | ForEach-Object {
    $first = (Get-Content $_.FullName -TotalCount 1)
    if ($first -ne "envelope:") { Write-Host "[FAIL] $($_.Name): $first" }
}
```

**预期**: 无 `[FAIL]` 输出

---

## 3. 敏感信息扫描（NO-FP）

> Patterns 引用自 [patterns.yaml](patterns.yaml)

```powershell
$vote_id = "<VOTE_ID>"
$pub_dir = ".claude/state/planvote-search/$vote_id"
$main_output = ".claude/state/voteplan.$vote_id.yaml"

# === Patterns from patterns.yaml ===
$PATTERN_TOKEN = '(tvly-|sk-|xai-)[A-Za-z0-9_-]{10,}'
$PATTERN_URL_SECRET = 'https?://[^\s"]+[?&](api_key|apikey|token|access_token|tavilyApiKey)=[^&\s"]+'
$PATTERN_PRAGMA = 'pragma:\s*allowlist-secret'

# === rg exit codes: 0=matches (FAIL), 1=no matches (OK), 2=error (ERROR) ===

# 3.1 Token 模式
rg -P $PATTERN_TOKEN $pub_dir
$exit1 = $LASTEXITCODE
# 预期: exit code 1 (无匹配)

# 3.2 URL 携带 secret
rg -P $PATTERN_URL_SECRET $pub_dir
$exit2 = $LASTEXITCODE
# 预期: exit code 1 (无匹配)

# 3.3 pragma 出现在公开工件（禁止）
rg $PATTERN_PRAGMA $pub_dir
$exit3 = $LASTEXITCODE
# 预期: exit code 1 (无匹配)

# 3.4 主输出也检查 token
rg -P $PATTERN_TOKEN $main_output
$exit4 = $LASTEXITCODE
# 预期: exit code 1 (无匹配)

# 判断结果
if ($exit1 -eq 0 -or $exit2 -eq 0 -or $exit3 -eq 0 -or $exit4 -eq 0) {
    Write-Host "[FAIL] 发现敏感信息"
} elseif ($exit1 -eq 2 -or $exit2 -eq 2 -or $exit3 -eq 2 -or $exit4 -eq 2) {
    Write-Host "[ERROR] rg 执行错误"
} else {
    Write-Host "[OK] 敏感扫描通过"
}
```

**预期**: 全部 exit code = 1 (无匹配)

---

## 4. Timestamp RFC3339 格式验证

> Pattern 引用自 [patterns.yaml](patterns.yaml) `PATTERN_TIMESTAMP_RFC3339`

```powershell
$vote_id = "<VOTE_ID>"
$main_output = ".claude/state/voteplan.$vote_id.yaml"

# Pattern 允许可选小数秒
$PATTERN_TIMESTAMP_RFC3339 = '^\s*timestamp:\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z'

# timestamp 必须是 RFC3339 格式（4位年 + 可选小数秒 + Z 后缀）
rg $PATTERN_TIMESTAMP_RFC3339 $main_output
$exit_valid = $LASTEXITCODE
# 预期: exit code 0 (匹配成功)

# 检查是否有非法格式（2位年、无Z等）
rg 'timestamp:\s*\d{2}-' $main_output
$exit_invalid = $LASTEXITCODE
# 预期: exit code 1 (无匹配)

# 判断结果
if ($exit_valid -eq 0 -and $exit_invalid -eq 1) {
    Write-Host "[OK] Timestamp RFC3339 格式正确"
} elseif ($exit_valid -eq 2 -or $exit_invalid -eq 2) {
    Write-Host "[ERROR] rg 执行错误"
} else {
    Write-Host "[FAIL] Timestamp 格式不符合 RFC3339"
}
```

**预期**: 第一条 exit=0 (有匹配)，第二条 exit=1 (无匹配)

---

## 5. 候选计划落盘验证

```powershell
$vote_id = "<VOTE_ID>"

# 检查候选数量（2-4 个）
$count = @(Get-ChildItem ".claude/state/planvote-search/$vote_id/candidates/plan_*.yaml" | Sort-Object Name).Count
($count -ge 2) -and ($count -le 4)

# 检查每个候选的 new_plan.steps 存在（排序遍历）
Get-ChildItem ".claude/state/planvote-search/$vote_id/candidates/plan_*.yaml" | Sort-Object Name | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -notmatch 'new_plan:') { Write-Host "[FAIL] $($_.Name): missing new_plan" }
    if ($content -notmatch 'steps:') { Write-Host "[FAIL] $($_.Name): missing steps" }
}
```

**预期**: 候选数量在 2-4 之间，无 `[FAIL]` 输出

---

## 6. query_manifest.yaml 验证（可复跑）

```powershell
$vote_id = "<VOTE_ID>"
$manifest_path = ".claude/state/planvote-search/$vote_id/query_manifest.yaml"

# 文件存在
Test-Path $manifest_path

# 必须包含关键字段
$manifest = Get-Content $manifest_path -Raw -ErrorAction SilentlyContinue
if ($manifest) {
    @('vote_id:', 'timestamp:', 'tools:', 'queries:') | ForEach-Object {
        if ($manifest -notmatch $_) { Write-Host "[FAIL] Missing: $_" }
    }
}
```

**预期**: 文件存在，无 `[FAIL]` 输出

---

## 7. score_log 完整性验证

```powershell
$vote_id = "<VOTE_ID>"
$score_log = Get-Content ".claude/state/planvote-search/$vote_id/score_log.yaml" -Raw

# 必须包含以下字段
$required = @('scoring_formula:', 'candidates:', 'ranking:', 'winner:', 'total:', 'evidence_refs:')
$required | ForEach-Object {
    if ($score_log -notmatch $_) { Write-Host "[FAIL] Missing: $_" }
}

# 检查 winner 存在且有 plan_index
if ($score_log -notmatch 'winner:\s*\n\s*plan_index:') { Write-Host "[FAIL] winner.plan_index missing" }
```

**预期**: 无 `[FAIL]` 输出

---

## 8. Tie-Breaker 可复现验证

```powershell
$vote_id = "<VOTE_ID>"

# 提取所有候选的 total 分数
$score_log = Get-Content ".claude/state/planvote-search/$vote_id/score_log.yaml" -Raw

# 检查 tie-break 相关字段
if ($score_log -match 'tiebreak_applied:\s*true') {
    # 如果有 tie-break，必须有 tiebreak_field 和 tiebreak_reason
    if ($score_log -notmatch 'tiebreak_field:') { Write-Host "[FAIL] tiebreak_field missing" }
    if ($score_log -notmatch 'tiebreak_reason:') { Write-Host "[FAIL] tiebreak_reason missing" }
}
```

**预期**: 无 `[FAIL]` 输出

---

## 9. 评分公式验证

```powershell
$vote_id = "<VOTE_ID>"
$score_log = Get-Content ".claude/state/planvote-search/$vote_id/score_log.yaml" -Raw

# 公式必须锁死
if ($score_log -notmatch 'total = 3 \* success \+ 2 \* evidence \+ 1 \* conciseness \+ 2 \* risk_score') {
    Write-Host "[FAIL] Scoring formula mismatch"
}

# 检查最大分数
if ($score_log -notmatch 'max_score:\s*40') {
    Write-Host "[WARN] max_score should be 40"
}
```

**预期**: 无 `[FAIL]` 输出

---

## 10. 主输出与 winner 一致性

```powershell
$vote_id = "<VOTE_ID>"

# 从 score_log 提取 winner.plan_index
$score_log = Get-Content ".claude/state/planvote-search/$vote_id/score_log.yaml" -Raw
if ($score_log -match 'winner:\s*\n\s*plan_index:\s*(\d+)') {
    $winner_index = $matches[1]

    # 从主输出提取 new_plan
    $main_output = Get-Content ".claude/state/voteplan.$vote_id.yaml" -Raw

    # 主输出必须包含 new_plan
    if ($main_output -notmatch 'new_plan:') {
        Write-Host "[FAIL] Main output missing new_plan"
    }

    # 检查 scoring_summary.winner.plan_index 一致
    if ($main_output -match 'plan_index:\s*(\d+)') {
        if ($matches[1] -ne $winner_index) {
            Write-Host "[FAIL] Winner index mismatch: score_log=$winner_index, main=$($matches[1])"
        }
    }
}
```

**预期**: 无 `[FAIL]` 输出

---

## 总结

| 检查项 | 预期 |
|--------|------|
| 目录结构 | 全部存在（含 query_manifest.yaml） |
| Envelope-first | 全部以 `envelope:` 开头 |
| 敏感扫描 | 无命中（patterns from patterns.yaml） |
| Timestamp | RFC3339 格式（允许可选小数秒） |
| 候选计划 | 2-4 个，含 new_plan + steps |
| query_manifest | 存在且含必要字段 |
| score_log | 完整（formula, candidates, ranking, winner） |
| Tie-breaker | 有则完整记录 |
| 评分公式 | 锁死公式 + max_score=40 |
| 主输出一致性 | winner 与 score_log 匹配 |

## 参考

- [patterns.yaml](patterns.yaml) - 敏感扫描 Patterns 单一事实源
- [SKILL.md](SKILL.md) - 完整 Skill 规范
- [verify_voteplan.ps1](verify_voteplan.ps1) - 自动验证脚本

---

*创建时间: 2025-12-28*
*更新时间: 2025-12-28 - patterns.yaml 单一事实源，rg exit-code 语义，可选小数秒*
