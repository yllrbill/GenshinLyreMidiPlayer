# AGENTS.md

本仓库任务骨架在 `ops/ai/`：

- **STATE**: `ops/ai/state/STATE.md`
- **任务目录**: `ops/ai/tasks/<TASK_ID>/`
- **request**: `ops/ai/tasks/<TASK_ID>/request.md`
- **context_pack**: `ops/ai/tasks/<TASK_ID>/evidence/context_pack.md`
- **plan**: `ops/ai/tasks/<TASK_ID>/plan.md`

## TASK_ID 获取规则

1. 读取 `ops/ai/state/STATE.md` 的 `## Latest Task` 章节
2. 解析 `- TASK_ID: <value>` 行（注意格式是 `- TASK_ID:` 而非 `latest_task_id:`）
3. 若无法解析：列出 `ops/ai/tasks/*/` 目录，sorted 后取最后一个
4. 若 tasks 目录为空：停止并提示"请先让 Claude 执行 /ai-intake 立案"

## 禁止行为

- ❌ 不要在仓库根查找 STATE.md / request.md / context_pack.md
- ❌ 不要全仓库遍历（只扫描 `ops/ai/tasks/*/` 一层）
