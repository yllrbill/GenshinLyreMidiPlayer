# Thinking Command (Router)

> 智能路由：根据上下文自动选择最合适的 thinking 子命令

## Auto-Trigger (PROACTIVELY 使用)

Thinking 被**自动触发**的条件：

### 触发条件

1. **失败锁存激活** (latch.lock 存在):
   - 检查 `$env:USERPROFILE\.claude\latch.lock` 是否存在
   - 如果存在 → 检查失败计数器状态

2. **失败计数器检查** (Circuit Breaker):
   - 读取 `.claude/state/thinking/failure_count.yaml`
   - 如果 `current >= 3` → **绕行模式激活**，跳过自动触发
   - 如果 `current < 3` → 自动调用 `/thingking` 分析阻塞点

3. **检测到绕行行为** (且 `current < 3`):
   - 工具失败后尝试替代路径（违反 triage-discipline）
   - 猜测性修复不查证根因（违反 Evidence-first）
   - 跳过证据链继续执行（违反 Fail-closed）

### 自动触发行为

```yaml
WHEN: <latch.lock 存在 OR 检测到绕行行为>
AND: <failure_count.current < 3>
AND: <blocker.latest.yaml 不存在或时间戳早于 latch.lock>
THEN:
  - 自动调用 Skill(skill: "thinking-router")
  - Thinking-router 自动路由到 /thingking
  - 输出 blocker.latest.yaml + trail.latest.yaml
  - LOG: "[thinking] 检测到失败锁存，自动分析阻塞点"
  - 等待分析完成后再提供修复方案
```

### 失败管理机制

**失败计数器** (`.claude/state/thinking/failure_count.yaml`):
```yaml
failure_count:
  current: 0              # 当前连续失败次数
  threshold: 3            # 阈值（3次后绕行）
  last_failure_time: <ISO8601>
  bypass_until: <ISO8601>  # 绕行模式持续到此时间
  failures:
    - timestamp: <ISO8601>
      blocker_id: B-251231-xxx
      reason: "循环阻塞"
```

**失败处理流程**:
1. /thinking 执行失败 → `failure_count.current++`
2. 生成失败日志 `.claude/state/thinking/failure_log/<blocker_id>.yaml`
3. 如果 `current < 3` → 携带失败日志再次调用 /thinking
4. 如果 `current >= 3` → 进入绕行模式（30分钟）

**失败日志格式** (`.claude/state/thinking/failure_log/<blocker_id>.yaml`):
```yaml
envelope:
  command: thinking_failure_log
  blocker_id: B-251231-xxx
  timestamp: <ISO8601>
  failure_index: 2

failure_analysis:
  failed_approach: "尝试使用 Bash 命令"
  failure_reason: "权限不足"
  pitfalls:
    - "未检查工具可用性"
    - "未探测权限状态"
  blocked_paths:
    - tool: Bash
      command: "yt-dlp ..."
      error: "Permission denied"
  learned_constraints:
    - "需要 Bash(*) 权限"
    - "需要先配置 settings.local.json"

retry_strategy:
  next_approach: "使用 AskUserQuestion 请求权限"
  avoid: ["直接执行 Bash", "假设权限存在"]
```

**绕行模式** (`current >= 3`):
- LOG: "[thinking] 连续3次阻塞，进入绕行模式（持续30分钟）"
- 允许使用替代工具/路径解决问题
- 提示用户手动介入
- 设置 `bypass_until = now() + 30min`

**成功重置**:
- 任何步骤成功执行后（Bash/Edit/Write 退出码 0）
- 重置 `failure_count.current = 0`
- 清除 latch.lock
- 清除绕行模式

**禁止绕过**: 失败后（绕行模式外）必须调用 thinking 分析，不得尝试替代路径。

---

## 路由规则

### 1. 检查工件状态
读取 `.claude/state/thinking/` 目录下的工件：
- `blocker.latest.yaml` - 阻塞点卡片
- `research.latest.yaml` - 研究结果
- `plan.latest.yaml` - 执行计划

### 2. 路由决策

| 条件 | 路由目标 | 说明 |
|------|----------|------|
| 无工件 + 有明确阻塞点 | `/thingking` | 本地分析阻塞点 |
| 有 blocker + needs=RESEARCH | `/thingking_web` | 外部研究 |
| 有 blocker + needs=REPLAN | `/thingking_web` | 重新规划 |
| 有 plan + 需要执行 | `/reflectloop` | 沙箱执行 |
| 无明确上下文 | `/thingking` | 先本地分析 |

### 3. 用户参数

```
/thinking [topic]           # 自动路由
/thinking local [topic]     # 强制本地分析
/thinking web [topic]       # 强制外部研究
/thinking status            # 显示当前状态
```

## 子命令

### /thingking (本地分析)
```
输入: 上下文 + 阻塞描述
输出: blocker.latest.yaml, trail.latest.yaml
用途: 分析当前阻塞点，生成证据链
```

### /thingking_web (外部研究)
```
输入: blocker.latest.yaml + 搜索关键词
输出: research.latest.yaml, plan.latest.yaml
用途: 外部搜索 + 生成执行计划
```

## 状态检查

```powershell
# 检查 thinking 工件状态
ls .claude/state/thinking/*.latest.yaml

# 读取最新 blocker
Get-Content .claude/state/thinking/blocker.latest.yaml -TotalCount 20
```

## Envelope 要求

所有 thinking 命令必须使用 envelope 格式：

```yaml
envelope:
  command: <thingking|thingking_web>
  timestamp: <ISO8601>
  status: OK|ERROR
  error_code: <null if OK>
  next: <suggested next command>
```

详见: `.claude/rules/65-thinking-envelope.md`

---

*用途: 分析问题、研究解决方案、生成执行计划*
