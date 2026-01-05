---
description: 执行计划文件中的步骤 - 读取 plan.md 或 plan.latest.yaml 并逐步执行
argument-hint: [--plan <path>] [--dry-run] [--step N]
---

# /planner-execute Command

执行 `.claude/private/plan.md` 或指定计划文件中的步骤。

## 执行流程

1. **读取计划文件**
   - 优先读取 `.claude/private/plan.md`（用户自定义计划）
   - 若为空，回退到 `.claude/state/thinking/plan.latest.yaml`

2. **解析步骤**
   - Markdown 格式：识别 `## Step N` 或 `1. `, `2. ` 等编号
   - YAML 格式：读取 `steps:` 数组

3. **逐步执行**
   - 显示当前步骤
   - 执行步骤中的命令
   - 记录结果到 `.claude/state/planner/execute.log`

4. **失败处理**
   - 遵循 Fail-Fast 原则
   - 失败时停止，写入 blocker 信息

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--plan` | `.claude/private/plan.md` | 计划文件路径 |
| `--dry-run` | `false` | 仅显示步骤，不执行 |
| `--step` | `all` | 执行特定步骤编号 |

## 计划文件格式

### Markdown 格式 (.md)

```markdown
# 计划标题

## 目标
描述本次计划的目标

## 步骤

### Step 1: 步骤名称
描述步骤内容
\`\`\`bash
command_to_execute
\`\`\`

### Step 2: 下一步骤
...
```

### YAML 格式 (.yaml)

```yaml
title: 计划标题
goal: 计划目标

steps:
  - id: P-1
    action: 步骤描述
    commands:
      - "python script.py"
    verification:
      - "预期输出"

  - id: P-2
    action: 下一步骤
    commands:
      - "next command"
```

## 使用示例

```powershell
# 执行默认计划
/planner-execute

# 预览计划（不执行）
/planner-execute --dry-run

# 执行特定步骤
/planner-execute --step 3

# 使用自定义计划文件
/planner-execute --plan ops/ai/tasks/xxx/plan.md
```

## 执行协议

### 开始执行
```
=== PLANNER-EXECUTE ===
Plan: <plan_path>
Steps: N
Mode: execute|dry-run
========================
```

### 步骤输出
```
[Step 1/N] <step_title>
> <command>
<output>
[OK] Step 1 completed
```

### 失败输出
```
[Step 3/N] <step_title>
> <command>
<error_output>
[FAIL] Step 3 failed
Exit code: 1
Blocker: <error_description>

=== STOPPED (Fail-Fast) ===
```

## 与其他命令的关系

| 命令 | 用途 |
|------|------|
| `/thinking` | 分析问题，生成 blocker |
| `/voteplan` | 多源搜索，生成候选计划 |
| **`/planner-execute`** | 执行计划步骤 |
| `/reflectloop` | 在沙箱中执行计划 |
| `/verify` | 验收执行结果 |

## 输出工件

| 工件 | 路径 | 说明 |
|------|------|------|
| 执行日志 | `.claude/state/planner/execute.log` | 步骤执行记录 |
| 失败记录 | `.claude/state/planner/failed_step.yaml` | 失败步骤详情 |

---

*Created: 2026-01-06*
