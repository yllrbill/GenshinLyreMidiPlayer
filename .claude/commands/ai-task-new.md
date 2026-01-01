---
description: Create a new task request (interactive; asks before writing request.md)
argument-hint: <TASK_ID> [short-goal]
---

你要创建一个新任务请求文件：`ops/ai/tasks/<TASK_ID>/request.md`

## 命令参数
- TASK_ID = `$1`
- short goal = 其余参数 `$ARGUMENTS`（可为空）

## 硬规则
- **在用户确认前：禁止创建/修改任何文件与目录。**
- 先问问题 → 用户回答 → 你复述成一版 request.md 草稿 → 用户确认 "确认创建" 后才落盘。
- 输出必须 deterministic（列清单时 sorted）。

---

## 交互流程

### A) 检查 TASK_ID

首先检查 `$1` 是否为空：
- 若为空：请用户提供 TASK_ID（建议格式：`YYYY-MM-DD-<N>` 或 `<feature-name>`），然后**停止等待回答**。
- 若非空：继续到步骤 B。

### B) 向用户提出问题

一次性列出以下问题，便于用户回答：

```
我需要收集以下信息来创建 request.md：

1) **目标（Goal）**：一句话描述要做什么？
   （候选默认值：$ARGUMENTS）

2) **Non-goals（明确不做什么）**：有哪些边界？
   - 例如：不重构、不改 API 签名、不涉及 XX 模块

3) **约束/偏好**：
   - 最小改动？是否允许重构？
   - 目标平台/版本？（如 Python 3.11, Windows）
   - 其他技术约束？

4) **验收标准（Acceptance Criteria）**：至少 3 条可验证的断言
   - 例如：运行 `pytest` 全部通过
   - 例如：`python main.py --help` 输出包含 `--version`

5) **参考文件/目录**：必须参考哪些路径？
   - 例如：`src/main.py`, `docs/API.md`, `tests/`

6) **敏感信息**：是否涉及密钥/隐私？
   - 如果有，只允许"变量名/掩码"，禁止明文
```

**然后停止等待用户回答。**

### C) 生成草稿

用户回答后：

1) 按 `ops/ai/templates/request.template.md` 的结构生成 request.md 草稿。

2) 在草稿末尾增加 **Planner Inputs** 段落：
   ```markdown
   ## Planner Inputs
   建议 ChatGPT 决策层优先读取以下文件：
   - (sorted list of file paths)
   ```

3) 输出完整草稿，并询问：
   ```
   ---
   以上是 request.md 草稿。

   请回复：
   - "确认创建" → 我将创建文件
   - "修改：<具体修改内容>" → 我将调整后重新输出草稿
   ```

### D) 落盘（仅在用户回复"确认创建"后）

执行以下操作：

1) 创建目录 `ops/ai/tasks/<TASK_ID>/evidence`（如不存在）

2) 写入 `ops/ai/tasks/<TASK_ID>/request.md`（草稿内容）

3) 更新 `ops/ai/state/STATE.md`：
   - `Latest Task` → TASK_ID
   - `Status` → DRAFT
   - `Pointer` → `ops/ai/tasks/<TASK_ID>`

4) 输出下一步指令：
   ```
   ✅ 任务请求已创建：ops/ai/tasks/<TASK_ID>/request.md

   下一步：
   1. 把以下文件发给 ChatGPT 决策层：
      - ops/ai/state/STATE.md
      - ops/ai/tasks/<TASK_ID>/request.md
      - (Planner Inputs 中列出的参考文件)
   2. 让决策层生成 plan.md 和/或 patch.diff
   3. 收到 plan 后运行：/ai-task-pack <TASK_ID>
   ```

---

## 模板参考

@ops/ai/templates/request.template.md
