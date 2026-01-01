# Reflectloop Routing & Integration

本文档说明 Reflectloop 如何被其它命令/Skill 调用和串联。

> **唯一事实源**: [SKILL.md](SKILL.md)

## 推荐调用链

```
┌─────────────────────────────────────────────────────────────────────┐
│                     推荐调用链 (Recommended)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  /thingking_web                                                      │
│       │                                                              │
│       ▼                                                              │
│  plan.latest.yaml  ──────────►  /reflectloop (Skill)                │
│                                      │                               │
│                         ┌────────────┴────────────┐                  │
│                         ▼                         ▼                  │
│                    [SUCCESS]                  [FAIL]                 │
│                         │                         │                  │
│                         ▼                         ▼                  │
│                  patch + summary         blocker.latest.yaml         │
│                  → 手动合并               + latch.lock               │
│                                                   │                  │
│                                                   ▼                  │
│                                           /thinking 路由             │
│                                           (检测 blocker.needs)       │
│                                                   │                  │
│                                    ┌──────────────┴──────────────┐   │
│                                    │                             │   │
│                              [RESEARCH]                    [REPLAN]  │
│                                    │                             │   │
│                                    ▼                             ▼   │
│                            /thingking_web               /thingking_web│
│                            (外部研究)                   (重新规划)    │
│                                    │                             │   │
│                                    └──────────────┬──────────────┘   │
│                                                   │                  │
│                                                   ▼                  │
│                                         新 plan.latest.yaml          │
│                                         (plan_source_hash 必须变化)  │
│                                                   │                  │
│                                                   ▼                  │
│                                         清理 latch.lock              │
│                                         → 重试 /reflectloop          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**关键点**：
- Reflectloop 是独立 Skill，不硬绑定任何 command
- 失败后写 blocker + latch，由 `/thinking` 决定下一步
- 每次重试必须更新 `plan_source_hash`，防止无限循环
- 最大重试 2~3 次后 STOP，需人工介入

## 核心定位

Reflectloop 是**模块化 Skill**，不是硬绑定某个 command：
- 可被 `/thinking` 路由体系调用
- 可被 CI/脚本直接调用
- 可被用户手动执行

## 调用方式

### 1. 通过 /thinking 路由

```
/thinking full
    │
    ├─ /thingking → blocker.latest.yaml, trail.latest.yaml
    │
    ├─ /thingking_web → research, delta, plan.latest.yaml
    │
    └─ /reflectloop → 执行 plan
```

### 2. 直接调用

```powershell
python -X utf8 analyzetools/reflectloop_sandbox.py --plan .claude/state/thinking/plan.latest.yaml
```

### 3. 作为 CI 步骤

```yaml
# .github/workflows/validate.yml
- name: Run Reflectloop
  run: python -X utf8 analyzetools/reflectloop_sandbox.py
  continue-on-error: false
```

## 工件驱动集成

Reflectloop 的输入输出完全基于工件文件，不依赖运行时状态：

### 输入工件

| 工件 | 生产者 | 消费者 |
|------|--------|--------|
| `plan.latest.yaml` | /thingking_web | reflectloop |

### 输出工件

| 工件 | 生产者 | 消费者 |
|------|--------|--------|
| `reflectloop.latest.yaml` | reflectloop | 调用方/审计 |
| `blocker.latest.yaml` | reflectloop (失败时) | /thinking 路由 |
| `latch.lock` | reflectloop (失败时) | /thinking 路由, hooks |

## 与 /thinking 路由的集成

### 失败触发路由

Reflectloop 失败时写入 `blocker.latest.yaml`，`/thinking` 路由器检测到后：

```yaml
# blocker.latest.yaml
envelope:
  command: reflectloop
  status: ERROR
  error_code: STEP_FAILED
  next: "/thinking"

blocker_id: B-251228-XXXXXX
needs: [RESEARCH]  # 或 [REPLAN]
```

### 路由决策

| blocker.needs | 路由到 | 说明 |
|---------------|--------|------|
| `[RESEARCH]` | /thingking_web | 依赖/版本问题，需要外部研究 |
| `[REPLAN]` | /thingking_web | 逻辑错误，需要重新规划 |

## 反思闭环流程

```
                    ┌──────────────────────────────────────────┐
                    │                START                     │
                    └──────────────────┬───────────────────────┘
                                       ▼
                    ┌──────────────────────────────────────────┐
                    │  /thingking_web → plan.latest.yaml       │
                    └──────────────────┬───────────────────────┘
                                       ▼
                    ┌──────────────────────────────────────────┐
                    │  /reflectloop                             │
                    └──────────────────┬───────────────────────┘
                                       ▼
                           ┌───────────────────────┐
                           │     SUCCESS?          │
                           └───────────┬───────────┘
                        YES │                   │ NO
                            ▼                   ▼
               ┌─────────────────┐   ┌─────────────────────────┐
               │  生成 patch     │   │  写 blocker + latch     │
               │  + summary      │   └───────────┬─────────────┘
               │  → END          │               ▼
               └─────────────────┘   ┌─────────────────────────┐
                                     │  retries < max?         │
                                     └───────────┬─────────────┘
                                  YES │                   │ NO
                                      ▼                   ▼
                     ┌──────────────────────┐   ┌─────────────────┐
                     │  /thingking_web      │   │  STOP           │
                     │  (基于 blocker.needs)│   │  人工介入       │
                     └──────────┬───────────┘   └─────────────────┘
                                ▼
                     ┌──────────────────────┐
                     │  清理 latch.lock     │
                     │  → 返回 reflectloop  │
                     └──────────────────────┘
```

## 调用方责任

调用 Reflectloop 的代码/命令需要：

1. **确保 plan 存在**：检查 `plan.latest.yaml` 存在且 status=OK
2. **处理 latch**：失败后清理 latch.lock 再重试
3. **控制重试**：跟踪 `plan_source_hash` 变化，防止无限循环
4. **归档 runs**：每次 run 有独立 run_id，日志不覆盖

## 与 Failure Latch 的集成

Reflectloop 遵循 `50-failure-latch.md` 机制：

1. **启动检查**：发现 `latch.lock` 直接 `LATCHED` 退出
2. **失败写入**：步骤失败后写 `latch.lock`
3. **恢复**：用户手动删除 `latch.lock` 后可重试

## 与 Secret-Safe 的集成

Reflectloop 遵循 `70-mcp-cus.md` 脱敏规则：

1. **env_status**：只写 `<SET>` / `<UNSET>`
2. **输出扫描**：检测敏感模式
3. **私密隔离**：`.claude/private/secrets/` 不进沙箱

## 不应做的事

Reflectloop 作为模块化 Skill：

- ❌ 不自动触发下一个命令（由调用方决定）
- ❌ 不自动重试（由调用方控制）
- ❌ 不修改源目录（变更在沙箱，需手动合并）
- ❌ 不安装依赖（由 plan 步骤决定）

## 示例：脚本调用

```python
#!/usr/bin/env python3
"""示例：脚本调用 Reflectloop 并处理反思闭环"""

from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path("d:/dw11")
PLAN_PATH = PROJECT_ROOT / ".claude/state/thinking/plan.latest.yaml"
LATCH_PATH = Path.home() / ".claude" / "latch.lock"
MAX_RETRIES = 3

def run_reflectloop():
    """执行一次 reflectloop"""
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "analyzetools/reflectloop_sandbox.py"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0

def cleanup_latch():
    """清理 latch.lock"""
    if LATCH_PATH.exists():
        LATCH_PATH.unlink()

def main():
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"Attempt {attempt}/{MAX_RETRIES}")

        # 清理旧 latch
        cleanup_latch()

        # 执行
        if run_reflectloop():
            print("SUCCESS")
            return 0

        # 失败：需要生成新 plan（此处简化，实际应调用 /thingking_web）
        print(f"FAILED, would regenerate plan...")
        # subprocess.run([...], ...)  # 调用 /thingking_web

    print("MAX_RETRIES exceeded")
    return 1

if __name__ == "__main__":
    sys.exit(main())
```

## References

- [SKILL.md](SKILL.md) - 唯一事实源
- [.claude/skills/thinking-router/ROUTING.md](../thinking-router/ROUTING.md) - /thinking 路由规则

---

*创建时间: 2025-12-28*
