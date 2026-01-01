---
name: modelrouter-core
description: 自动路由 Skill - 根据任务复杂度选择 haiku/sonnet/opus 并追踪模型选择
allowed-tools: Read(*), Write(.claude/state/modelrouter/*), Glob(*), Task(*)
model_preference: haiku
---

# Modelrouter Core Skill

## Purpose

Modelrouter 是**自动模型路由 + 选择追踪**模块。根据任务复杂度自动选择最合适的模型，并记录路由决策。

**核心能力**：
- 复杂度判断（EASY/MEDIUM/HARD）
- 模型选择（haiku/sonnet/opus）
- 路由决策追踪
- 历史记录与统计

## Sources of Truth

> **本文件是 Modelrouter 的唯一事实源。**

| 文件 | 角色 |
|------|------|
| `.claude/skills/modelrouter-core/SKILL.md` | **唯一事实源** |
| `.claude/skills/modelrouter-core/patterns.yaml` | 复杂度检测 Patterns |
| `.claude/rules/65-thinking-envelope.md` | Envelope 规范（继承） |

---

## Trigger

1. **隐式调用**：每次 Task 工具使用前可参考路由建议
2. **显式调用**：
   - `/modelrouter` - 查看当前会话统计
   - `/modelrouter status` - 详细状态
   - `/modelrouter stats [period]` - 周期统计 (day/week/month)
   - `/modelrouter override <model>` - 强制使用指定模型

---

## Complexity Assessment Algorithm

### Score Calculation

```
total_score = keyword_score + length_score + context_score
```

### 1. Keyword Score (patterns.yaml 定义)

**HARD keywords** (任一匹配即加分):
| Pattern | Weight | Examples |
|---------|--------|----------|
| `refactor`, `architect` | 30 | "refactor this module" |
| `design.*system`, `system.*design` | 35 | "design a caching system" |
| `cryptograph`, `encrypt`, `decrypt` | 30 | "decrypt this file" |
| `reverse.*engineer`, `decompil` | 40 | "reverse engineer the DLL" |
| `security.*audit`, `exploit` | 35 | "security audit the API" |

**MEDIUM keywords**:
| Pattern | Weight | Examples |
|---------|--------|----------|
| `analyze`, `investigate` | 15 | "analyze this error" |
| `troubleshoot`, `debug` | 15 | "debug the crash" |
| `fix.*bug`, `trace` | 15 | "fix the login bug" |
| `implement`, `create`, `build` | 10 | "implement a function" |
| `compare`, `review`, `explain.*how` | 15 | "review this code" |

### 2. Length Score

| Condition | Score |
|-----------|-------|
| prompt > 500 chars | +20 |
| prompt > 200 chars | +10 |
| prompt <= 200 chars | +0 |

### 3. Context Score

| Condition | Score |
|-----------|-------|
| context files >= 5 | +20 |
| context files >= 2 | +10 |
| context files < 2 | +0 |

### Classification Thresholds

| Score Range | Level | Model |
|-------------|-------|-------|
| >= 50 | HARD | opus |
| 25-49 | MEDIUM | sonnet |
| < 25 | EASY | haiku |

---

## Model Mapping

### Default Mapping

| Complexity | Model | Rationale |
|------------|-------|-----------|
| EASY | haiku | 快速、低成本，适合简单任务 |
| MEDIUM | sonnet | 平衡性能与成本，适合常规开发 |
| HARD | opus | 最强能力，适合复杂推理 |

### Override Rules (Priority Order)

1. **User explicit** (`--model=X`): 最高优先级
2. **Skill preference** (frontmatter `model_preference`): 中优先级
3. **Complexity routing**: 默认行为

### Skill-Level Defaults

以下 Skill 有预设的模型偏好：

| Skill | Default Model | Rationale |
|-------|---------------|-----------|
| thinking | opus | 深度推理需要 |
| voteplan | sonnet | 多源合成 |
| reflectloop | sonnet | 执行监控 |
| bootstrap | haiku | 简单状态检查 |
| websearch | haiku | 查询生成 |

---

## Outputs (Envelope-First)

所有输出必须以 `envelope:` 开头，符合 `.claude/rules/65-thinking-envelope.md` 规范。

### Routing Decision Output

```yaml
envelope:
  command: modelrouter
  timestamp: 2025-12-30T10:30:00Z
  status: OK
  error_code: null
  artifacts_written:
    - .claude/state/modelrouter/session.latest.yaml
  next: null

metrics:
  routing:
    complexity_level: MEDIUM
    complexity_score: 35
    complexity_reasoning:
      - "keyword: analyze (+15)"
      - "context: 3 files (+10)"
      - "length: 250 chars (+10)"
    model_selected: sonnet
    model_override: null
    override_reason: null
```

### Session Summary Output

```yaml
envelope:
  command: modelrouter
  timestamp: 2025-12-30T12:00:00Z
  status: OK

session:
  started_at: 2025-12-30T10:00:00Z
  project_dir: "d:/dw11"

tasks:
  - task_id: "T-251230-0001"
    timestamp: 2025-12-30T10:05:00Z
    prompt_preview: "Analyze the encryption..."
    complexity:
      level: HARD
      score: 60
    model:
      selected: opus
      override: null
    status: completed

summary:
  total_tasks: 5
  models_used:
    haiku: 2
    sonnet: 2
    opus: 1
  complexity_distribution:
    EASY: 2
    MEDIUM: 2
    HARD: 1
```

---

## Error Codes

| Code | Meaning | Handling |
|------|---------|----------|
| ROUTING_FAILED | 无法判断复杂度 | 默认使用 sonnet |
| STORAGE_FAILED | 无法写入状态 | 警告但继续执行 |
| INVALID_OVERRIDE | 无效的覆盖参数 | 忽略覆盖，使用默认 |
| LATCHED | 会话已锁定 | 跳过写入，仅返回路由结果 |

---

## Failure Latch 处理

当 Failure Latch 机制激活时 (`latch.lock` 存在)，modelrouter-core 的行为：

### 检测逻辑

```
1. 检查 $HOME/.claude/latch.lock 是否存在
2. 如果存在 → 设置 status=OK, error_code=LATCHED
3. 跳过状态写入 (.claude/state/modelrouter/*)
4. 仍然返回路由结果 (model selection)
```

### 输出示例 (Latched)

```yaml
envelope:
  command: modelrouter
  timestamp: <ISO8601>
  status: OK
  error_code: LATCHED
  warnings:
    - "Session latched - state write skipped"
  artifacts_written: []
  next: "Remove-Item $HOME/.claude/latch.lock to unlock"

metrics:
  routing:
    complexity_level: MEDIUM
    model_selected: sonnet
    # 路由结果仍然有效
```

### 设计原则

1. **路由功能不受影响** - 即使无法写入状态，模型选择仍然有效
2. **Fail-Safe** - 状态写入失败不阻塞主流程
3. **可观测性** - 通过 `error_code: LATCHED` 和 warnings 明确告知状态
4. **与 Failure Latch 兼容** - 尊重 Fail-Closed 原则，不绕过锁定机制

---

## State Storage

### Directory Structure

```
.claude/state/modelrouter/
├── session.latest.yaml       # 当前会话摘要
├── history/                   # 历史记录 (按日期)
│   └── YYYYMMDD/
│       └── <session_id>.yaml
└── aggregates/                # 聚合统计
    ├── daily/
    │   └── YYYYMMDD.yaml
    └── weekly/
        └── YYYY-WNN.yaml
```

### Retention Policy

| Type | Retention |
|------|-----------|
| session.latest.yaml | 当前会话 |
| history/ | 30 天 |
| aggregates/daily/ | 90 天 |
| aggregates/weekly/ | 1 年 |

---

## Integration with Task Tool

Modelrouter 为 Task 工具提供模型选择建议：

```
用户请求 → Modelrouter 分析 → 选择模型 → Task(model=X) → 记录结果
```

### Integration Flow

1. **分析**: 解析 prompt 和 context
2. **评分**: 计算 complexity score
3. **路由**: 选择 model
4. **记录**: 写入 session.latest.yaml
5. **执行**: 返回建议给调用方

---

## Usage Examples

### Example 1: Simple Query (EASY → haiku)

```
User: "What is the file structure of this project?"

Modelrouter:
  score: 10 (no keywords, short prompt, no context)
  level: EASY
  model: haiku
```

### Example 2: Code Analysis (MEDIUM → sonnet)

```
User: "Analyze the error handling in this function"

Modelrouter:
  score: 35
    - keyword: "analyze" (+15)
    - length: 280 chars (+10)
    - context: 2 files (+10)
  level: MEDIUM
  model: sonnet
```

### Example 3: Complex Task (HARD → opus)

```
User: "Reverse engineer the encryption algorithm in neox_engine.dll"

Modelrouter:
  score: 70
    - keyword: "reverse engineer" (+40)
    - keyword: "encryption" (+30)
  level: HARD
  model: opus
```

---

## Verification

```powershell
# 验证 Skill 结构
Test-Path ".claude/skills/modelrouter-core/SKILL.md"

# 验证状态目录可写
New-Item -ItemType File -Path ".claude/state/modelrouter/test.txt" -Force
Remove-Item ".claude/state/modelrouter/test.txt"

# 验证无命名冲突
$cmds = Get-ChildItem ".claude/commands" -Filter "*.md" | ForEach-Object { $_.BaseName }
$skills = Get-ChildItem ".claude/skills" -Directory | ForEach-Object { $_.Name }
$conflicts = $cmds | Where-Object { $skills -contains $_ }
# 预期: 无冲突 (modelrouter command, modelrouter-core skill)
```

---

*Created: 2025-12-30*
*Priority: MEDIUM*
*Status: ACTIVE*
