# Command / Skill Naming Convention

## Problem

When a **Slash Command** (`.claude/commands/<name>.md`) and a **Skill** (`.claude/skills/<name>/SKILL.md`) share the **same name**, Claude Code prioritizes the Skill. Since Skills are designed as "Claude-only" by default, the user cannot directly invoke `/name` — it shows:

> "This slash command can only be invoked by Claude"

## Solution: Never Use Same Name

| 类型 | 位置 | 命名规则 |
|------|------|----------|
| Command | `.claude/commands/<name>.md` | 用户直接调用名 (e.g., `voteplan`) |
| Skill | `.claude/skills/<name>-core/SKILL.md` | 加 `-core` 后缀避免冲突 |

### Examples

| 功能 | Command | Skill |
|------|---------|-------|
| Voteplan | `voteplan.md` | `voteplan-core/SKILL.md` |
| Reflectloop | `reflectloop.md` | `reflectloop-core/SKILL.md` |
| Thinking | `thinking.md` | `thinking-router/SKILL.md` |

## Skill Frontmatter Requirements

每个 Skill 的 `SKILL.md` 必须有 frontmatter：

```yaml
---
name: <directory-name>        # 必须与目录名一致
description: <brief description>
allowed-tools: Bash(*), Read(*), Write(*), Edit(*)  # 可选
---
```

## Self-Check Script

定期运行以检测命名冲突：

```powershell
# PowerShell
$cmd   = Get-ChildItem .claude/commands -Filter *.md | ForEach-Object { $_.BaseName }
$skill = Get-ChildItem .claude/skills -Directory | ForEach-Object { $_.Name }
$conflicts = $cmd | Where-Object { $skill -contains $_ }
if ($conflicts) {
    Write-Host "[CONFLICT] Command/Skill name collision:" -ForegroundColor Red
    $conflicts | ForEach-Object { Write-Host "  - $_" }
} else {
    Write-Host "[OK] No naming conflicts" -ForegroundColor Green
}
```

## After Renaming

1. Update all references (use `grep -r "skills/<old-name>/"`)
2. Add/update frontmatter in SKILL.md
3. **Restart Claude Code** (required for skill changes to take effect)

---

*Created: 2025-12-28*
*Triggered by: /voteplan "only invoked by Claude" bug*
