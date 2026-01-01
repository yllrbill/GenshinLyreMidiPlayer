---
description: 任务收尾与交接：生成 context_pack + 确保证据/hand off/STATE 更新（执行前若信息不足先询问）
argument-hint: "<TASK_ID 可选> [DONE|BLOCKED|DRAFT 可选] 例: /ai-end 2026-01-01-piano DONE"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

你在 Claude Code 执行层工作。目标：把当前任务"收尾到可交接状态"，让 Planner（ChatGPT）用最小上下文继续决策。

## 状态定义

| 状态 | 含义 | 行为 |
|------|------|------|
| **DONE** | 任务完成 | 更新 STATE.md 为 DONE，生成完整交接包 |
| **BLOCKED** | 任务阻塞 | 更新 STATE.md 为 BLOCKED，记录阻塞点 |
| **DRAFT** | 中场复盘 | **不更新 STATE.md 状态**，只打包交接材料供 Planner 决策 |

**DRAFT 模式用途**：中途需要 Planner 介入决策时使用，不宣告完成/阻塞。

## 硬规则

- Fail-closed：缺关键文件/测试失败/证据不足就标记 BLOCKED，不要假装完成。
- Evidence-first：所有关键命令输出落盘到 ops/ai/tasks/<TASK_ID>/evidence/ 下。
- Secret-safe：若日志可能含敏感信息，只在 evidence 中保存"脱敏版摘要"；原始敏感内容放 private/，不要提交到 git。

## 执行步骤

### A) 选择 TASK_ID
1) 若用户传了 $1 则用它；否则从 ops/ai/state/STATE.md 读取 latest task。
2) 若仍无法确定：列出 ops/ai/tasks/*（sorted）并询问用户选哪一个，然后停止等待。

### B) 准备目录
- 确保存在：ops/ai/tasks/<TASK_ID>/evidence/
- 若不存在 request.md：停止并说明缺口。

### C) 生成/更新 evidence（最小交接包）

**必须生成的工件**：

| 文件 | 路径 | 用途 |
|------|------|------|
| context_pack.md | evidence/ | 给决策层的低 token 摘要 |
| diff.patch | evidence/ | 当前改动（WIP 也行） |
| tests.log | evidence/ | 关键失败段（如果跑过测试） |
| execute.log | evidence/ | 关键命令与输出摘要 |
| handoff.md | 任务目录 | Evidence Index + "现在卡在哪里/需要决策什么" |

**生成步骤**：

1) **execute.log**：写入/追加 git status、git log -1、以及本次收尾步骤的关键输出（不要贴长日志，必要时只摘录失败段+上下文）

2) **tests.log**：若存在测试命令（plan.md 或 REPO_MAP.md 中能找到）：运行并把输出写入；失败则后续状态倾向 BLOCKED

3) **diff.patch**：生成 `git diff`（包括 staged 和 unstaged），用于给 Planner 审阅

4) **context_pack.md**：
   - **优先**：调用 `context-packer` subagent 产出"低 token"摘要（路径索引、失败点、下一步）
   - subagent 有独立上下文窗口，适合做打包/映射重活，减少主会话变长风险
   - 若无 subagent：自己按模板写（不贴大量源码，给路径+要点）

### D) handoff + STATE

1) **handoff.md**：写/更新 ops/ai/tasks/<TASK_ID>/handoff.md
   - 必须包含 **Evidence Index**：列出 evidence 文件路径
   - **DRAFT 模式**：重点写"现在卡在哪里 / 需要 Planner 决策什么"

2) **STATE.md**：更新 ops/ai/state/STATE.md
   - Latest Task = <TASK_ID>
   - **DRAFT 模式**：Status 保持不变（或标记为 IN_PROGRESS）
   - **DONE/BLOCKED 模式**：Status = DONE 或 BLOCKED
   - Next Actions：按优先级列出 3-5 条

### E) 最后输出（8 行以内）

```
状态: DONE / BLOCKED / DRAFT
任务: <TASK_ID>

Planner 最小阅读清单:
1. ops/ai/tasks/<TASK_ID>/evidence/context_pack.md
2. ops/ai/tasks/<TASK_ID>/handoff.md
3. ops/ai/tasks/<TASK_ID>/evidence/diff.patch
4. ops/ai/tasks/<TASK_ID>/evidence/tests.log (如果存在)

下一步建议: <具体命令或决策请求>
```
