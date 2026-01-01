# Thinking Router - Detailed Routing Rules

本文档是 `thinking.md` 的补充说明，**以 thinking.md 为唯一事实源**。

## Artifact-Based Routing

路由决策完全基于工件文件与其 envelope 字段，不依赖运行时状态（如 last_bash_exit_code）。

### 工件路径
```
.claude/state/thinking/
├── blocker.latest.yaml   # from /thingking
├── trail.latest.yaml     # from /thingking
├── research.latest.yaml  # from /thingking_web
├── delta.latest.yaml     # from /thingking_web
└── plan.latest.yaml      # from /thingking_web
```

### Routing Rules (ordered)
```yaml
routing_rules:
  # 1) Latch lock 检测（失败优先）
  - condition: "latch.lock exists AND age < 1h"
    route: /thingking
    reason: "Recent failure detected - need blocker analysis"

  - condition: "latch.lock exists AND age >= 1h"
    action: "Warn stale lock, suggest manual cleanup"
    route: /thingking
    warn: "STALE_LOCK"
    reason: "Stale lock detected"

  # 2) 无 blocker → 先本地分析
  - condition: "blocker.latest.yaml missing"
    route: /thingking
    reason: "No blocker card exists"

  # 3) blocker 指示需要研究 → web
  - condition: "blocker.latest.yaml exists AND blocker.needs contains RESEARCH"
    route: /thingking_web
    reason: "Blocker needs external research"

  # 4) research 完成但 delta/plan 不完整 → web 继续
  - condition: "research.latest.yaml exists AND research.envelope.status = OK AND (delta.latest.yaml missing OR delta.complete != true OR plan.latest.yaml missing OR plan.ready != true)"
    route: /thingking_web
    reason: "Research complete, continue with delta/plan"

  # 5) 上游错误传播（STOP）
  - condition: "research.latest.yaml exists AND envelope.status = ERROR"
    route: null
    action: "Output ERROR envelope then STOP"
    reason: "Upstream error - cannot continue"
```

## routed_to allowed values

仅允许以下三个值：

| 值 | 含义 |
|----|------|
| `thingking` | 路由到本地分析命令 |
| `thingking_web` | 路由到 Web 研究命令 |
| `null` | STOP - 不路由 |

## Latch Lock 检测

检查 `$HOME/.claude/latch.lock`：

**文件格式（YAML）**：
```yaml
pid: 12345
created_at: 2025-12-28T10:30:00Z
reason: BASH_FAILED
```

**Stale 判定**：
- PID 不存在 → stale
- age >= 1 hour → stale
- PID 存在且 age < 1 hour → active

**处理**：
- stale：输出警告（error_code=STALE_LOCK），并建议用户手动清理；仍可路由到 /thingking
- active：直接路由到 /thingking

## Error Handling

### STOP 条件（必须 STOP）

当检测到以下情况时，输出 ERROR envelope 然后 STOP（routed_to: null）：

1. research.latest.yaml 的 envelope.status = ERROR
2. 检测到 SECRET_LEAK（例如 env_check 中出现 `://`）
3. 所有必要工件缺失且无法推断下一步（MISSING_ARTIFACT）

### Error Codes

| 错误码 | 含义 | 触发条件 |
|--------|------|----------|
| MISSING_ARTIFACT | 工件缺失 | 依赖的 .latest.yaml 不存在且无法推断 |
| SEARCH_FAILED | 搜索失败 | /thingking_web 的上游 envelope 报错 |
| STALE_LOCK | 过期锁 | latch.lock 超过 1 小时或 PID 不存在 |
| SECRET_LEAK | 敏感信息泄露 | env_check 发现 URL/token |

> SECRET_LEAK 属于 70-mcp-cus 脱敏门禁引入的扩展错误码（允许超集），不改变 thinking.md 的最小枚举声明。

## Full Workflow Sequence

当执行 `/thinking full` 时：

```
1) /thingking
   ↓ 生成 blocker.latest.yaml, trail.latest.yaml
2) /thingking_web
   ↓ 生成 research.latest.yaml, delta.latest.yaml, plan.latest.yaml
```

## Benchmarking (Optional)

- 输出目录：`.claude/state/thinking/bench/<run_id>/`
- 路由决策**不依赖** bench 产物
- bench 文件名不固定；如出现 bench_report.md 也仅是"可选报告名之一"，不得写成门禁/硬规则/锁死要求

## References

- [thinking.md](.claude/commands/thinking.md) - **唯一事实源**
- [65-thinking-envelope.md](.claude/rules/65-thinking-envelope.md) - envelope 规范
- [70-mcp-cus.md](.claude/rules/70-mcp-cus.md) - MCP 脱敏规则

## Deprecated

以下内容已废弃，不再作为路由条件：

- `last_bash_exit_code` - 改用 latch.lock 工件
- `last_tool_exit_code` - 改用 latch.lock 工件
- `external_signal` - 改用工件状态
- `--force`、`--skip`、`--verbose` 参数 - thinking.md 中不存在
- cc-blocker, cc-trail, cc-research, cc-delta, cc-replan - 已合并到 /thingking 和 /thingking_web
