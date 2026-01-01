---
name: planner
description: Create a task plan by reading ops/ai/state/STATE.md and the latest task's request.md + context_pack.md, then output plan.md and (when requested) patch.diff. Use when the user invokes $planner or asks to generate a plan from those three files.
---

# Planner

## Overview

Generate a concise plan from ops/ai/state/STATE.md and the latest task's request.md + context_pack.md. Produce plan.md and, if requested or when changes were made, provide patch.diff containing the unified diff for plan.md.

## Workflow

### Step 1: Locate TASK_ID (骨架感知)

**输入定位规则（按顺序执行，Fail-closed）**：

1. **读取 STATE.md**：`ops/ai/state/STATE.md`

2. **解析 TASK_ID**：
   - 查找 `## Latest Task` 章节
   - 从中提取 `- TASK_ID: <value>` 行
   - 正则：`^- TASK_ID:\s*(.+)$`

   ```
   # 你的 STATE.md 实际格式：
   ## Latest Task
   - TASK_ID: 20260101-2137-octave-policy-feature
   - Status: DONE
   - Pointer: ops/ai/tasks/20260101-2137-octave-policy-feature
   ```

3. **Fallback**：如果 STATE.md 解析失败
   - 列出 `ops/ai/tasks/*/` 目录（只扫这一层）
   - sorted 后取最后一个目录名作为 TASK_ID
   - 如果 tasks 目录为空：**STOP** - 提示"请先让 Claude 执行 /ai-intake 立案生成 task"

4. **读取任务文件**：
   - 必需：`ops/ai/tasks/<TASK_ID>/request.md`（不存在则 fail-closed）
   - 可选：`ops/ai/tasks/<TASK_ID>/evidence/context_pack.md`
   - 降级：若无 context_pack.md，尝试读 `handoff.md`

5. **输出路径固定**：
   - `ops/ai/tasks/<TASK_ID>/plan.md`
   - 可选：`ops/ai/tasks/<TASK_ID>/patch.diff`

### Step 2: Draft plan.md

Keep it short and actionable. Recommended sections:

```markdown
# Plan: <TASK_ID>

## Goal/Scope
(1-2 sentences from request.md)

## Constraints/Assumptions
- (bullets)

## Plan Steps
1. Step 1 - (description)
2. Step 2 - (description)
3. Step 3 - (description)
(3-7 steps max)

## Acceptance Checklist
- [ ] (aligned to request.md / context_pack.md)

## Risks/Dependencies
- (if any)

---
*Generated: YYYY-MM-DD HH:MM*
```

### Step 3: Write plan.md

Write to `ops/ai/tasks/<TASK_ID>/plan.md`.

### Step 4: Provide patch.diff (optional)

When requested (or when explicitly asked to include it):
- patch.diff is a unified diff of the plan.md change relative to the previous version
- If plan.md is new, include the full file in the diff

## Output Expectations

- `plan.md` must live in `ops/ai/tasks/<TASK_ID>/`
- Use clear, minimal language and avoid speculation
- Do not ask for TASK_ID; resolve it via STATE.md or the ops/ai/tasks/* fallback
- Ask a brief clarification question only if required files are missing or no task directories exist

## Error Handling

| Condition | Action |
|-----------|--------|
| STATE.md 不存在 | 尝试 fallback 到 tasks/* 枚举 |
| TASK_ID 解析失败 | 尝试 fallback 到 tasks/* 枚举 |
| tasks 目录为空 | **STOP** - 提示运行 /ai-intake |
| request.md 不存在 | **STOP** - fail-closed |
| context_pack.md 不存在 | 降级读 handoff.md，或仅用 request.md |
