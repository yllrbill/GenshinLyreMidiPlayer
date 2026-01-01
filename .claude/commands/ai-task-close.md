---
description: Close current task (write handoff + update STATE)
argument-hint: <TASK_ID>
---

目标：确保任务收尾工件齐全（handoff + evidence 索引 + STATE 更新）。在写入前，如果关键文件缺失，先列缺失清单并询问是否继续。

## 命令参数
- TASK_ID = `$1`

## 硬规则
- 输出必须 deterministic（列清单时 sorted）
- 如果关键 evidence 缺失，必须先询问用户是否继续
- Secret-safe：禁止输出明文密钥/token

---

## Subagent 调用

根据任务需要，可调用以下 subagent：

| Subagent | 用途 | 调用时机 |
|----------|------|----------|
| `test-runner` | 运行测试并收集日志 | 若 tests.log 缺失且需要验证 |
| `code-reviewer` | 审查代码变更 | 若有 diff.patch 且需要 review |
| `context-packer` | 生成 Context Pack | 若任务 BLOCKED 需要发给 Planner |

**Use the `test-runner` subagent if tests.log is missing and user wants to run tests before closing.**

**Use the `code-reviewer` subagent if there are code changes (diff.patch exists) and user wants a review report.**

---

## 执行步骤

### 1) 验证输入

检查 TASK_ID 是否有效：
- 若 `$1` 为空：从 `ops/ai/state/STATE.md` 读取 Latest Task 作为默认值
- 若仍为空：提示用户提供 TASK_ID，然后停止
- 若 `ops/ai/tasks/<TASK_ID>/` 不存在：报错并停止

### 2) 检查 Evidence 完整性

检查以下文件是否存在：

| 文件 | 必需 | 说明 |
|------|------|------|
| `ops/ai/tasks/<TASK_ID>/request.md` | 是 | 任务请求 |
| `ops/ai/tasks/<TASK_ID>/plan.md` | 否 | 执行计划 |
| `ops/ai/tasks/<TASK_ID>/evidence/execute.log` | 建议 | 执行日志 |
| `ops/ai/tasks/<TASK_ID>/evidence/diff.patch` | 建议 | 变更补丁 |
| `ops/ai/tasks/<TASK_ID>/evidence/tests.log` | 建议 | 测试日志 |
| `ops/ai/tasks/<TASK_ID>/handoff.md` | 否 | 将由本命令生成 |

如果"建议"文件缺失，输出警告并询问：
```
⚠️ 以下 evidence 文件缺失：
- (sorted list)

选项：
- "继续" → 生成 handoff 并标注缺失项
- "跑测试" → 调用 test-runner subagent 收集测试日志
- "补充" → 停止，等你补充后重新运行
```

### 3) 生成 handoff.md

如果 `handoff.md` 不存在，按 `ops/ai/templates/handoff.template.md` 生成：

```markdown
# Handoff - <TASK_ID>

## Goal
(从 request.md 提取)

## Scope Done / Not Done
- Done:
  - (从 plan.md 或 execute.log 推断)
- Not Done:
  - (未完成的步骤)

## Changes (file list)
(从 diff.patch 提取，sorted)

## Commands Run (with evidence links)
1. `command` → [execute.log](evidence/execute.log)

## Tests/Verification
- (从 tests.log 提取结果摘要)
- Evidence: [tests.log](evidence/tests.log)

## Evidence Index
| File | Status | Description |
|------|--------|-------------|
| execute.log | ✅/❌ | 执行日志 |
| tests.log | ✅/❌ | 测试输出 |
| diff.patch | ✅/❌ | 变更补丁 |
| context_pack.md | ✅/❌ | Context Pack |
| review_report.md | ✅/❌ | Code Review |

## Next Steps (priority)
1. (根据测试结果或阻塞点)
2. ...

## Risks/Notes
- (bullet list)

---

*Completed: YYYY-MM-DD*
```

如果 `handoff.md` 已存在，询问是否覆盖：
```
handoff.md 已存在。是否覆盖？
- "覆盖" → 重新生成
- "保留" → 跳过，只更新 STATE.md
```

### 4) 确定任务状态

根据以下规则确定 Status：

| 条件 | Status |
|------|--------|
| tests.log 存在且无 FAIL/ERROR | DONE |
| tests.log 存在且有 FAIL/ERROR | BLOCKED |
| tests.log 不存在，execute.log 无错误 | DONE (unverified) |
| execute.log 有错误 | BLOCKED |
| 其他 | UNKNOWN |

### 5) 更新 STATE.md

更新 `ops/ai/state/STATE.md`：

```markdown
## Latest Task
- TASK_ID: <TASK_ID>
- Status: <DONE|BLOCKED|UNKNOWN>
- Pointer: ops/ai/tasks/<TASK_ID>
- Closed: YYYY-MM-DD

## Next Actions
- (从 handoff.md Next Steps 复制)
```

### 6) 输出总结

```
✅ 任务 <TASK_ID> 已关闭

状态: <DONE|BLOCKED|UNKNOWN>

文件更新:
- (created/updated) ops/ai/tasks/<TASK_ID>/handoff.md
- (updated) ops/ai/state/STATE.md

给 Planner 的阅读清单:
1. ops/ai/tasks/<TASK_ID>/handoff.md
2. ops/ai/tasks/<TASK_ID>/evidence/diff.patch
3. ops/ai/tasks/<TASK_ID>/evidence/execute.log
4. ops/ai/tasks/<TASK_ID>/evidence/tests.log

下一步建议:
- (如果 DONE) 创建新任务: /ai-task-new <next-task-id>
- (如果 BLOCKED) 生成 Context Pack 发给 Planner: /ai-task-pack <TASK_ID>
```

---

## 模板参考

@ops/ai/templates/handoff.template.md
