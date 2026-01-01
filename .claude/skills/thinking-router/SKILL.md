# Thinking Router Skill

## Purpose
智能路由 `/thinking`（或 `/think`）到 `/thingking` 与 `/thingking_web`。
路由决策**完全基于工件**（`.claude/state/thinking/*.latest.yaml`）与 `latch.lock`，不依赖运行时 exit code。

## Sources of Truth
- `.claude/commands/thinking.md`：唯一事实源（命令职责、routing_rules、输出契约）
- `.claude/rules/65-thinking-envelope.md`：envelope 结构、STOP 规则、错误码
- `.claude/rules/70-mcp-cus.md`：secret-safe（尤其 env_check 输出约束）

## Trigger
- 用户输入 `/thinking` 或 `/think`
- 检测到 `$HOME/.claude/latch.lock` 存在
- blocker.latest.yaml 的 `needs` 指示需要继续（例如包含 `RESEARCH`）

## Inputs
- 用户输入：`/thinking [mode] [args...]`
- 工件目录：`.claude/state/thinking/`
  - blocker.latest.yaml（from /thingking）
  - trail.latest.yaml（from /thingking）
  - research.latest.yaml（from /thingking_web）
  - delta.latest.yaml（from /thingking_web）
  - plan.latest.yaml（from /thingking_web）
- 锁文件：`$HOME/.claude/latch.lock`（可选）

## Outputs (Envelope-First)
路由器的每次输出都必须以 `envelope:` 开头（包括 STOP 分支）。
路由器本身不写入工件文件，因此 `artifacts_written` 应为空数组。

### routed_to allowed values
仅允许以下三个值：
- `thingking`：路由到 `/thingking`
- `thingking_web`：路由到 `/thingking_web`
- `null`：STOP（不路由）

### Envelope template (router)
```yaml
envelope:
  command: thinking
  timestamp: <ISO8601>
  status: OK|ERROR
  error_code: <null|SEARCH_FAILED|MISSING_ARTIFACT|STALE_LOCK|SECRET_LEAK>
  # SECRET_LEAK 属于 70-mcp-cus 脱敏门禁引入的扩展错误码（允许超集），不改变 thinking.md 的最小枚举声明。
  missing_inputs: []
  artifacts_read:
    - <checked artifact paths>
  artifacts_written: []   # router writes nothing
  routed_to: <thingking|thingking_web|null>
  next: <suggested command or fix>
```

**STOP 条件**: 当 `status: ERROR` 时，只输出 envelope，不继续路由。

## Usage

```
/thinking              # 自动检测工件并路由
/thinking blocker      # 直接运行 /thingking
/thinking research AES # 直接运行 /thingking_web "AES"
/thinking full         # 先 /thingking 再 /thingking_web
```

## Command Mapping

| 模式 | 路由到 | 输出工件 |
|------|--------|----------|
| auto | (自动检测) | 取决于路由目标 |
| blocker | /thingking | blocker.latest.yaml, trail.latest.yaml |
| research | /thingking_web | research.latest.yaml, delta.latest.yaml, plan.latest.yaml |
| full | /thingking → /thingking_web | 所有工件 |

## Secret-Safe Rules

遵循 `70-mcp-cus.md` 脱敏规则：

1. **env_check 只输出状态**: `SET` 或 `UNSET`，绝不输出实际值
2. **禁止 URL 泄露**: 不得输出包含 `://` 的环境变量值
3. **检测即 STOP**: 如果输出中发现 URL/token 外观，立即 `error_code: SECRET_LEAK`

## Integration

### 与 Failure Latch 集成
当 `latch.lock` 存在时检查 PID + created_at：
- PID 不存在 OR age >= 1h → stale lock，警告并继续
- PID 存在 AND age < 1h → active lock，路由到 /thingking

### 与 MCP Search 集成
`/thingking_web` 使用 MCP 搜索优先级：
brave → tavily-remote → freebird → qwen_fallback → WebSearch (内置)

## Artifacts

状态工件目录：`.claude/state/thinking/`

| 工件 | 生成命令 | 关键字段 |
|------|----------|----------|
| blocker.latest.yaml | /thingking | envelope, needs |
| trail.latest.yaml | /thingking | envelope, complete |
| research.latest.yaml | /thingking_web | envelope, search_log |
| delta.latest.yaml | /thingking_web | envelope, complete |
| plan.latest.yaml | /thingking_web | envelope, ready |

## Benchmarking (Optional)

基准测试产物为**可选**输出，不是门禁：
- 输出目录：`.claude/state/thinking/bench/<run_id>/`
- 文件名不固定；路由决策**不依赖** bench 产物
- bench 产物不污染主工件目录

## References

- [thinking.md](.claude/commands/thinking.md) - **唯一事实源**
- [65-thinking-envelope.md](.claude/rules/65-thinking-envelope.md) - envelope 规范 + NO-FP 扫描
- [70-mcp-cus.md](.claude/rules/70-mcp-cus.md) - MCP 脱敏规则

## Deprecated

> cc-blocker, cc-trail, cc-research, cc-delta, cc-replan 已废弃。
> 功能已合并到 `/thingking`（本地分析）和 `/thingking_web`（Web 研究）。
> 如需历史兼容，参见 `.claude/_archive/60-cc-workflow.md`。

## Files
- SKILL.md (本文件)
- ROUTING.md (详细路由规则)
