---
description: 恢复上下文（读 STATE + 最新任务 + 证据），输出≤10步下一步计划与需要运行的命令
argument-hint: "[TASK_ID 可选] 例: /ai-resume 2026-01-01-piano-001"
allowed-tools: Read, Glob, Grep
---

你在 Claude Code 的执行层中工作。目标：**在不问我重复问题的前提下**，从仓库工件恢复上下文并给出下一步可执行计划。遵守：

- Continuity-first：优先读仓库事实（STATE、任务目录、证据日志），不要依赖聊天记忆。
- Deterministic：任何"自动选择"必须排序（sorted）并说明规则。
- Fail-closed：缺关键文件/证据就明确报缺口，不要猜测。
- Secret-safe：不要把疑似密钥/个人信息原文输出；如必须引用日志，最多摘录失败段+少量上下文，并对 token/key 做遮罩。

步骤：

A) 选择 TASK_ID
1) 若用户传入了 TASK_ID（参数），使用它。
2) 否则读取 `ops/ai/state/STATE.md`，寻找 "current_task / latest_task / TASK_ID" 类字段。
3) 若 STATE 中没有，则列出目录 `ops/ai/tasks/*/`，按目录名 **字典序排序**，选择最后一个作为最新任务（并在输出中说明该规则）。

B) 读取最小集（按存在性）
- `CLAUDE.md`
- `ops/ai/state/STATE.md`
- `ops/ai/context/REPO_MAP.md`（若存在）
- `ops/ai/tasks/<TASK_ID>/request.md`
- `ops/ai/tasks/<TASK_ID>/plan.md`（若存在）
- `ops/ai/tasks/<TASK_ID>/handoff.md`（若存在）
- `ops/ai/tasks/<TASK_ID>/evidence/` 下最新的 `tests.log / execute.log / diff.patch / context_pack.md`（若存在）

C) 输出（必须包含以下段落）
1) **Current status**：一句话概括任务在做什么、做到哪、是否阻塞（引用文件路径作为证据索引）。
2) **Missing / Risks**：列出缺失文件、可疑点（例如：plan 缺失、测试未跑、证据不全）。
3) **Plan Steps**（如果 plan.md 存在）：
   - **直接从 `plan.md` 提取步骤**，不要自己重新分析
   - 原样输出 plan.md 中的 "Plan Steps" / "Steps" / "Execution Steps" 章节
   - 标注哪些步骤已完成（根据 evidence/ 日志、handoff.md 判断）
   - 标注当前应执行的步骤（第一个未完成的步骤）
4) **Next ≤10 steps**（如果 plan.md 不存在或无有效步骤）：
   - 此时才自己生成计划
   - 每步写 "要做什么 + 影响文件 + 预期命令（如有）+ 验收标准/证据落点"
5) **Recommended command**：告诉我下一条应该运行的命令（例如继续执行 plan 中的某步），并说明原因。

D) 行为约束
- 本命令只读，不写文件、不跑破坏性命令。
- 若用户想继续执行改动，输出后停止，等我下达执行命令。
