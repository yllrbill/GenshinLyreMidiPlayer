# /modelrouter - 模型路由与追踪

根据任务复杂度自动分析并追踪模型建议历史。

> **注意**: 用户使用订阅计划，模型切换不可能。此命令只做**复杂度分析 + 使用追踪**。

## Usage

```
/modelrouter              # 查看当前会话统计
/modelrouter status       # 详细状态（含最近任务）
/modelrouter stats [day|week|month]  # 周期统计
/modelrouter analyze "<prompt>"  # 分析 prompt 复杂度
/modelrouter track "<prompt>" <model>  # 记录使用
```

## 执行方式

此命令通过调用 Python 脚本执行：

```powershell
# 查看状态
python D:/dw11/.claude/skills/modelrouter-core/modelrouter.py status

# 分析复杂度
python D:/dw11/.claude/skills/modelrouter-core/modelrouter.py analyze "your prompt here"

# 记录使用
python D:/dw11/.claude/skills/modelrouter-core/modelrouter.py track "prompt" opus

# 周期统计
python D:/dw11/.claude/skills/modelrouter-core/modelrouter.py stats day
```

## Behavior

### 默认（无参数）

显示当前会话统计摘要：

```
Session: 2025-12-30T10:00:00Z
Tasks: 5
Models: haiku(2) sonnet(2) opus(1)
Complexity: EASY(2) MEDIUM(2) HARD(1)
```

### status

显示详细状态，包括最近 5 个任务：

```
Session: 2025-12-30T10:00:00Z
Override: none

Recent Tasks:
1. [HARD→opus] "Reverse engineer the encryption..."
2. [MEDIUM→sonnet] "Analyze the error handling..."
3. [EASY→haiku] "What is the file structure..."
...
```

### stats [period]

显示指定周期的聚合统计：

```
Period: 2025-12-30 (day)
Total Tasks: 25
Models Used:
  haiku: 10 (40%)
  sonnet: 12 (48%)
  opus: 3 (12%)
Complexity Distribution:
  EASY: 10 (40%)
  MEDIUM: 12 (48%)
  HARD: 3 (12%)
```

### track "<prompt>" <model>

记录一次使用（分析复杂度并记录实际使用的模型）：

```
Tracked: T-251230-0001
  Level: HARD
  Score: 70
  Suggested: opus
  Actual: opus
  Override: False
```

### analyze "<prompt>"

分析给定 prompt 的复杂度，不实际执行任务：

```
Prompt: "Reverse engineer the encryption algorithm"
Analysis:
  Keywords found:
    - "reverse engineer" (+40, category: reverse_engineering)
    - "encryption" (+30, category: crypto)
  Length: 45 chars (+0)
  Context: 0 files (+0)
  ---
  Total Score: 70
  Level: HARD
  Model: opus
```

**实现逻辑** (来自 patterns.yaml):

1. **关键词匹配**: 按 hard_keywords → medium_keywords → easy_indicators 顺序匹配
2. **长度计算**: short(≤200)=0, medium(201-500)=+10, long(>500)=+20
3. **阈值判定**: HARD≥50 → opus, MEDIUM≥25 → sonnet, EASY<25 → haiku
4. **写入状态**: `.claude/state/modelrouter/session.latest.yaml`

**Envelope 输出**:

```yaml
envelope:
  command: modelrouter
  timestamp: <ISO8601>
  status: OK
  error_code: null  # 或 LATCHED (当 latch.lock 存在时仍返回结果)
  artifacts_written:
    - .claude/state/modelrouter/session.latest.yaml

metrics:
  routing:
    complexity_level: HARD
    complexity_score: 70
    model_selected: opus
    keyword_matches:
      - pattern: "reverse.*engineer"
        weight: 40
        category: reverse_engineering
    length_score: 0
```

## Integration

### 与 Task 工具协同

当调用 Task 工具时，可以先运行 `/modelrouter analyze` 获取模型建议，然后使用 `Task(model=<suggested>)` 启动子代理。

### Skill 调用

Modelrouter 作为 Skill (`modelrouter-core`) 可被其他命令/Skill 内部调用，获取路由建议。

## State Files

| 文件 | 用途 |
|------|------|
| `.claude/state/modelrouter/session.latest.yaml` | 当前会话记录 |
| `.claude/state/modelrouter/history/YYYYMMDD/` | 历史记录 |
| `.claude/state/modelrouter/aggregates/` | 聚合统计 |

## Sources of Truth

- **Skill 定义**: `.claude/skills/modelrouter-core/SKILL.md`
- **复杂度 Patterns**: `.claude/skills/modelrouter-core/patterns.yaml`

## Examples

### 查看当前状态
```
User: /modelrouter
```

### 分析复杂度
```
User: /modelrouter analyze "Implement a caching system for the API"
```

### 强制使用 opus
```
User: /modelrouter override opus
```

---

*Created: 2025-12-30*
*Related Skill: modelrouter-core*
