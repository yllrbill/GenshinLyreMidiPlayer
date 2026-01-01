---
description: Bootstrap ops/ai skeleton (create folders + base docs)
argument-hint: (no args)
---

你的任务：在仓库内初始化双代理骨架目录 ops/ai/** 与模板文件；若文件已存在，不要覆盖，先询问用户是否要合并或跳过。

执行步骤（必须按顺序）：

1) 检查以下路径是否存在（存在则记录，不存在则创建目录）：
   - ops/ai/state
   - ops/ai/context
   - ops/ai/templates
   - ops/ai/tasks
   - private/

2) 检查以下文件是否存在：
   - ops/ai/README.md
   - ops/ai/state/STATE.md
   - ops/ai/context/PROMPTS.md
   - ops/ai/context/REPO_MAP.md
   - ops/ai/context/DECISIONS.md
   - ops/ai/templates/request.template.md
   - ops/ai/templates/plan.template.md
   - ops/ai/templates/handoff.template.md
   - ops/ai/templates/context_pack.template.md
   - private/.gitignore
   - private/README.md

3) 若文件不存在：按 ops/ai/README.md 中定义的协议创建初始版本。

4) 如果文件已存在：不要覆盖；改为输出"建议补齐的缺失段落清单"，让用户确认后再编辑。

5) 最后输出：
   - 创建/修改了哪些文件（sorted 列表）
   - 跳过了哪些已存在的文件（sorted 列表）
   - 下一步建议：运行 `/ai-task-new <TASK_ID> <short-goal>` 创建第一个任务

## 模板内容参考

若需创建文件，使用以下内容：

### ops/ai/README.md
```markdown
# Dual-Agent Workflow (ChatGPT Planner + Claude Executor)

## Roles
- **ChatGPT = Planner (决策层)**：只产出 plan.md / patch.diff / 验收标准，不直接改仓库、不跑命令。
- **Claude Code = Executor (执行层)**：按 plan 落地改代码、跑命令、产证据、写 handoff，并更新 STATE.md。

## Ground Rules
- **Single Source of Truth**: repo files under `ops/ai/**`
- **Deterministic**: 任何遍历/选择都必须 sorted，并说明规则
- **Evidence-first**: 每步要可复跑 + 可验收（日志、diff、测试输出）
- **Fail-closed**: 验收失败必须停下并写 BLOCKED
```

### ops/ai/state/STATE.md
```markdown
# Project State

## Latest Task
- TASK_ID: (none)
- Status: (INIT)
- Pointer: ops/ai/tasks/(none)

## Current Focus
- (write current focus here)

## Known Issues / Risks
- (bullet list)

## Next Actions
- (bullet list, sorted by priority)

## How to Resume in a New Session
1. Read `ops/ai/state/STATE.md`
2. Read `ops/ai/context/REPO_MAP.md`
3. Read latest task folder `request.md` + `handoff.md` + `evidence/*`
4. Continue from "Next Actions"
```

### ops/ai/context/PROMPTS.md
```markdown
# Prompts

## ChatGPT (Planner) - Session Opener
你是"决策层（Planner）"，不直接改仓库、不运行命令。优先读：
- ops/ai/state/STATE.md
- ops/ai/context/REPO_MAP.md
- ops/ai/tasks/<TASK_ID>/request.md

你的输出必须可执行：≤10步计划 + 影响文件 + 验收命令 + 证据清单；信息不足则先列 Context Pack 请求。

## Claude (Executor) - Session Opener
你是"执行层（Executor）"，先读：
- CLAUDE.md
- ops/ai/state/STATE.md
- ops/ai/tasks/<TASK_ID>/request.md + plan.md (+patch.diff)

先给≤10条执行计划，再动手。Evidence-first、Fail-closed、Minimal change。
```

### private/.gitignore
```
*
!.gitignore
!README.md
```
