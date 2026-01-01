---
description: 任务建案 + 索引更新：生成 TASK_ID + request.md + 更新 STATE/TASKS_INDEX（可选更新 REPO_MAP/PLANNER_PACK）
argument-hint: "<短标题> [约束可选] [--full] 例: /ai-intake fix-hotkey-bug 需要兼容Win11"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

你在 Claude Code 执行层工作。目标：**建案 + 更新索引**，让 Planner 能快速定位。

## 模式

| 参数 | 说明 |
|------|------|
| (默认) | 建案 + 更新 TASKS_INDEX.md |
| `--full` | 建案 + 更新全部索引（TASKS_INDEX + REPO_MAP + PLANNER_PACK） |

## 硬规则

- Minimal：默认只生成必要文件
- Deterministic：TASK_ID 格式固定为 `YYYYMMDD-HHMM-<slug>`
- Fail-closed：若 slug 为空或无效，停止并询问
- **Pause-after-intake**：建案完成后（Part 1 + Part 2 完成），**必须暂停**并询问用户下一步意图，**不得自动执行实现代码**

---

## Part 1: 建案

### A) 生成 TASK_ID

格式：`YYYYMMDD-HHMM-<slug>`

```
slug = 用户传入的 $1（短标题）
      → 转小写
      → 空格/特殊字符替换为 -
      → 截断到 30 字符
```

示例：`Fix Hotkey Bug` → `20260101-1430-fix-hotkey-bug`

### B) 创建任务目录

```
ops/ai/tasks/<TASK_ID>/
├── request.md              # 本命令生成
├── evidence/
│   └── context_pack.md     # 本命令生成（初始版本）
└── scratch/                # 空目录
```

### C) 生成 request.md

```markdown
# Task: <TASK_ID>

## Goal
(从用户输入提取，或询问补充)

## Constraints
- (用户传入的约束，如 $2)
- (其他已知约束)

## Acceptance Criteria
- [ ] (验收条件 1)
- [ ] (验收条件 2)

## Sensitive Data Warning
<!-- 如果任务涉及敏感数据，取消注释 -->
<!--
⚠️ 本任务涉及敏感数据：
- 类型：(API key / 密钥 / 个人信息)
- 处理：原始数据放 private/tasks/<TASK_ID>/，脱敏版放 evidence/
-->

## Planner Inputs
1. ops/ai/tasks/<TASK_ID>/request.md (本文件)
2. ops/ai/context/PLANNER_PACK.md
3. (其他相关文件)

---
*Created: YYYY-MM-DD HH:MM*
```

### D) 生成 evidence/context_pack.md（初始版本）

基于 `ops/ai/templates/context_pack.template.md` 模板生成，填入已知信息：

```markdown
# Context Pack for <TASK_ID>

> 固定 6 段结构，每段 3-6 行，避免长篇

## 1. Goal
(从 request.md Goal 提取)

## 2. What's Done
- (初始状态：无)

## 3. Current Blocker / Decision Needed
- 等待用户确认实现方向

## 4. Evidence Index
| File | Path | Summary |
|------|------|---------|
| request.md | ./ | 任务定义 |

## 5. Minimal Files to Read
1. ops/ai/tasks/<TASK_ID>/request.md - 任务定义

## 6. Next Actions Candidates
- [ ] A: 开始实现
- [ ] B: 需要更多信息

---
*Generated: YYYY-MM-DD HH:MM*
```

### E) 更新 STATE.md

```markdown
## Latest Task
- TASK_ID: <TASK_ID>
- Status: NEW
- Pointer: ops/ai/tasks/<TASK_ID>
```

---

## Part 2: 索引更新

### F) TASKS_INDEX.md（总是更新）

扫描 `ops/ai/tasks/*/` 目录，重建任务索引表：

```markdown
# Tasks Index

| TASK_ID | Status | Updated | Path | Summary |
|---------|--------|---------|------|---------|
| <TASK_ID> | NEW | YYYY-MM-DD | ops/ai/tasks/.../ | (从 request.md Goal 提取) |
```

**状态读取规则**（sorted by TASK_ID）：
1. 从 `handoff.md` 读取 Status
2. 若无 handoff.md，检查 evidence/ 内容
3. 默认：NEW

### G) REPO_MAP.md（--full 时更新）

**优先**：调用 `repo-mapper` subagent 生成

```markdown
# Repository Map

## Project Overview
(一句话描述)

## Entry Points
| Entry | Path | Purpose |
|-------|------|---------|

## Key Modules (sorted)
- `src/core/` - ...

## Build / Run / Test Commands
...

## Risk Areas
...
```

### H) PLANNER_PACK.md（--full 时更新）

```markdown
# Planner Pack

## 1. Project Summary
(3-5 行)

## 2. Key Paths (按重要性)
1. CLAUDE.md
2. ops/ai/state/STATE.md
3. ...

## 3. Common Commands
| 操作 | 命令 |

## 4. Current Focus
(从 STATE.md)

## 5. Risk Areas
...

## 6. Active Tasks
(从 TASKS_INDEX.md 读取 IN_PROGRESS)
```

---

## 输出（8 行以内）

```
✅ 任务已建案: <TASK_ID>

已创建/更新:
- ops/ai/tasks/<TASK_ID>/request.md
- ops/ai/tasks/<TASK_ID>/evidence/context_pack.md
- ops/ai/state/STATE.md
- ops/ai/state/TASKS_INDEX.md
- ops/ai/context/REPO_MAP.md (--full)
- ops/ai/context/PLANNER_PACK.md (--full)

下一步: 确认 request.md 内容，告知是否开始实现
```
