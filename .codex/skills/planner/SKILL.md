---
name: planner
description: Create a task plan from ops/ai/state/STATE.md and the latest task's request.md + context_pack.md, OR maintain ChatGPT/Claude prompt docs (agents.md + d:\dw11\piano\.claude\private\plan.md) from a chat transcript. Use when the user invokes $planner, asks to generate a plan, or asks to update agents.md/Claude plan from chat logs.
---

# Planner

## Overview

本技能支持两类工作流，按用户请求选择其一；不明确时先问一句确认。

- **Workflow A**：基于 `ops/ai/state/STATE.md` 生成任务计划（原 planner 流程）
- **Workflow B**：维护 ChatGPT/Claude 持久提示词（`agents.md` + `d:\dw11\piano\.claude\private\plan.md`）

Generate a concise plan from ops/ai/state/STATE.md and the latest task's request.md + context_pack.md. Produce plan.md and, if requested or when changes were made, provide patch.diff containing the unified diff for plan.md.

## Workflow A - Task Plan (ops/ai)

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

## Workflow B - 持久提示词维护 (ChatGPT/Claude)

### 触发条件（任一满足即可）
- 用户提到 `agents.md` / ChatGPT 维持上下文 / Claude 提示词 / “基于聊天生成提示词”
- 用户明确要求生成或更新 `D:\dw11\piano\LyreAutoPlayer\ops\ai\context\agents.md` 或 `d:\dw11\piano\.claude\private\plan.md`

### 关键约束
- 只在 `LyreAutoPlayer/ops/ai/context/agents.md` 内维护 ChatGPT 持久信息；**文件路径与文件名固定**，不要新建/改名该目录下的其它文件。
- `LyreAutoPlayer/ops/ai/context/PROJECT_SUMMARY.md` 只读不改。
- Claude 执行提示词**仅**写入 `d:\dw11\piano\.claude\private\plan.md`，不要写入其它 `plan.md` 位置或变体路径。
- 对话内容必须来自用户提供的聊天记录或明确指向的文件；缺失则先请求用户贴出。

### 步骤
1. 读取 `LyreAutoPlayer/ops/ai/context/agents.md`（不存在则用模板创建）
2. 读取 `LyreAutoPlayer/ops/ai/context/PROJECT_SUMMARY.md`
3. 读取用户贴出的聊天记录（必需）；如未提供，先询问
4. 如聊天中引用仓库文件或模块，再按需读取相关文件（避免全仓库扫描）
5. 更新 `agents.md`：
   - 合并新增约束/关键背景/决定/待确认项
   - 保留已有内容，除非被明确推翻
   - 结构保持稳定，避免大改版
6. 生成 `d:\dw11\piano\.claude\private\plan.md`（Claude 专用提示词，唯一输出位置）
7. 回复用户时只做简要总结 + 列出更新文件路径，不贴整段内容

### agents.md 模板（ChatGPT 专用）
```
# ChatGPT Context (固定文件)

## 关键目标
- ...

## 持久约束
- ...

## 关键背景/决定
- ...

## 待确认
- ...

## 给用户的提示词
主要目标：
阶段步骤：
步骤内容（从哪改、改动代码摘要）：
约束：
```

### d:\dw11\piano\.claude\private\plan.md 模板（Claude 专用）
```
# Claude Prompt

## 主要目标
- 一句话目标（与用户请求一致）
- 完成标准/验收点（可验证）

## 阶段步骤
1. 读取/确认输入（聊天记录 + context/必要文件）
2. 修改实现（按文件/模块分组）
3. 验证/输出（测试或人工验证点）

## 步骤内容（从哪改、改动代码摘要）
1. 从哪改：<path or module>
   改动代码摘要：<改什么/为什么>

## 约束
- 语言/路径/禁止事项（仅列相关）
- 若信息缺失，先向用户确认
```
