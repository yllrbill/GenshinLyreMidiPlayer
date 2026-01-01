---
name: reflectloop-core
description: 可复跑沙箱执行闭环 - 在隔离环境中执行 plan.latest.yaml
allowed-tools: Bash(*), Read(*), Write(*), Edit(*), Glob(*), Grep(*)
---

# Reflectloop Core Skill

## Purpose

Reflectloop 是**可复跑执行闭环模块**，在隔离沙箱中按 `plan.latest.yaml` 的步骤执行命令，以 exit code 判定成功/失败，并生成可审计的证据链。

**核心能力**：
- 沙箱隔离执行（git worktree 优先，copy 兜底）
- Fail-fast + latch 锁存
- Secret-safe（敏感值检测 + 脱敏输出）
- 工件驱动的反思闭环（失败 → blocker → /thinking → 新 plan → 重试）

## Sources of Truth

> **本文件是 Reflectloop 的唯一事实源。** 其它文件只能引用此处，不得重复定义契约。

| 文件 | 角色 |
|------|------|
| `.claude/skills/reflectloop-core/SKILL.md` | **唯一事实源** |
| `.claude/skills/reflectloop-core/ROUTING.md` | 集成规则（如何被其它命令调用） |
| `.claude/commands/reflectloop.md` | Thin wrapper（调用入口） |
| `.claude/rules/reflectloop-envelope.md` | 规范附录（引用本文件） |
| `analyzetools/reflectloop_sandbox.py` | 实现（遵循本规范） |

## Trigger

Reflectloop 被触发的条件：

1. **用户显式调用**：`/reflectloop` 或 `python -X utf8 analyzetools/reflectloop_sandbox.py`
2. **/thinking 路由后续**：`plan.latest.yaml` 生成后自动执行
3. **CI/脚本调用**：作为可复跑验收步骤

## Inputs

### 必需

| 工件 | 路径 | 说明 |
|------|------|------|
| Plan | `.claude/state/thinking/plan.latest.yaml` | 来自 /thingking_web 的执行计划 |

### Plan 结构要求

```yaml
envelope:
  command: thingking_web
  status: OK
  timestamp: <ISO8601>
  # ...

new_plan:
  unified_goal: "Goal description"
  run_id: <RUN_ID>

  steps:
    - id: P-1
      action: "Description of what this step does"
      commands:
        - "python -X utf8 script.py"
        - "npm test"
      cwd: "optional/subdirectory"  # 相对于沙箱根目录
      verification:
        - "Expected output or state"
      depends_on: []
```

### 可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--plan` | `.claude/state/thinking/plan.latest.yaml` | Plan 文件路径 |
| `--mode` | `auto` | 沙箱模式: auto, worktree, copy |
| `--max-retries` | `2` | 最大重试次数（由调用方控制） |
| `--sandbox-root` | `%TEMP%/reflectloop` | 沙箱根目录 |
| `--project-root` | `.` | 项目根目录 |

## Outputs (Envelope-First)

> **所有 `.latest.yaml` 必须以 `envelope:` 开头。**

### Envelope 模板

```yaml
envelope:
  command: reflectloop
  timestamp: <ISO8601>
  status: OK|ERROR
  error_code: <null if OK, else error code>
  missing_inputs: []
  artifacts_read:
    - <input artifact paths>
  artifacts_written:
    - <output artifact paths>
  next: <suggested next command, null if OK>
```

### 成功时输出

| 工件 | 路径 | 说明 |
|------|------|------|
| Result | `.claude/state/reflectloop/reflectloop.latest.yaml` | 执行结果 (status=OK) |
| Patch | `.claude/state/reflectloop/runs/<run_id>/changes.patch` | 变更补丁 (git diff) |
| Summary | `.claude/state/reflectloop/runs/<run_id>/summary.md` | 执行摘要 |
| Logs | `.claude/state/reflectloop/runs/<run_id>/logs/*.log` | 步骤日志 |

### 失败时输出

| 工件 | 路径 | 说明 |
|------|------|------|
| Result | `.claude/state/reflectloop/reflectloop.latest.yaml` | 执行结果 (status=ERROR) |
| Blocker | `.claude/state/thinking/blocker.latest.yaml` | 阻塞点卡片 |
| Lock | `$HOME/.claude/latch.lock` | 失败锁存 |
| Logs | `.claude/state/reflectloop/runs/<run_id>/logs/*.log` | 步骤日志 |

## Error Handling

### 错误码定义

| 错误码 | Exit Code | 含义 | 触发条件 | 后续行为 |
|--------|-----------|------|----------|----------|
| `MISSING_PLAN` | 1 | Plan 文件缺失 | plan.latest.yaml 不存在 | **STOP** - 提示先运行 /thingking_web |
| `INVALID_PLAN` | 1 | Plan 格式无效 | 无法解析或无可执行步骤 | **STOP** - 检查 plan 格式 |
| `SANDBOX_CREATE_FAILED` | 1 | 沙箱创建失败 | worktree/copy 都失败 | **STOP** - 检查磁盘空间/权限 |
| `STEP_FAILED` | 1 | 步骤执行失败 | 命令返回非 0 exit code | **STOP** - 写 blocker + latch.lock |
| `SECRET_LEAK` | 99 | 敏感信息泄露 | 检测到 API key 等 | **STOP** - fail-closed |
| `LATCHED` | 1 | 会话已锁定 | latch.lock 存在 | **STOP** - 先解锁再执行 |
| `SANDBOX_ESCAPE` | 98 | cwd 逃逸 | step.cwd 解析到沙箱外 | **STOP** - 修正 plan 中的 cwd |
| `MAX_RETRIES` | - | 超过重试次数 | 由调用方控制 | **STOP** - 需要人工介入 |

### STOP 条件

当 `status: ERROR` 时：
1. 输出完整 envelope
2. **不执行后续步骤**
3. 在 `next` 字段给出修复建议
4. 写入 `latch.lock`（除 LATCHED 自身外）

## Sandbox Strategy

### 默认位置

沙箱默认创建在**项目目录外**（系统临时目录），避免递归复制风险：

```
Windows: %TEMP%\reflectloop\<run_id>\repo
Unix: /tmp/reflectloop/<run_id>/repo
```

### 快路径 (worktree)

```
条件: 项目是 git repo 且 git 可用 且工作区干净
方法: git worktree add --detach
优点: 快速、结构一致、支持 git diff
注意: 若工作区有未提交改动，自动降级到 copy 模式
```

### 兼容路径 (copy)

```
方法: shutil.copytree + ignore 函数
优点: 跨平台、可控排除
```

### 默认排除项

```
.git/
.claude/state/
.claude/sandbox/
.claude/private/secrets/
node_modules/
venv/
venvsfrida_env/
__pycache__/
.pytest_cache/
analyzedata/outputs/
analyzedata/scratch/
*.i64
*.idb
*.dll
*.exe
*.pdb
```

### cwd 逃逸门禁

`step.cwd` 解析后必须在沙箱目录内：

```python
resolved_cwd = (sandbox_repo / step.cwd).resolve()
if not str(resolved_cwd).startswith(str(sandbox_repo.resolve())):
    # SANDBOX_ESCAPE - exit_code=98
```

## Latch Lock

### 启动时检查

Reflectloop 启动前检查 `$HOME/.claude/latch.lock`：
- 存在 → `error_code: LATCHED`，直接退出
- 不存在 → 继续执行

### 失败时写入

```yaml
# $HOME/.claude/latch.lock
pid: <process_id>
created_at: <ISO8601>
reason: STEP_FAILED
```

### 清理

用户手动清理后重试：

```powershell
Remove-Item $env:USERPROFILE\.claude\latch.lock -Force
```

## Secret-Safe Rules

### 1. env_status 只写 SET/UNSET

```yaml
env_status:
  BRAVE_API_KEY: <SET>      # 正确
  TAVILY_MCP_URL: <UNSET>   # 正确
  # DASHSCOPE_API_KEY: sk-xxx  # 禁止！
```

### 2. 敏感模式检测

```regex
# API key 赋值
(TAVILY|BRAVE|DASHSCOPE).*(API_KEY|MCP_URL)\s*[:=]\s*(?!\$\{)(?!<)[^\s"'<]+

# Token 模式
[:=]\s*[^$\s"<]*(tvly-|sk-)[A-Za-z0-9_-]{10,}

# URL 携带 secret
https?://[^\s"]+[?&](api_key|apikey|token|tavilyApiKey)=[^&\s"]+
```

### 3. 检测流程

1. 检查 plan 内容
2. 检查每个命令
3. 检查命令输出 (stdout/stderr)
4. 发现泄露 → `error_code: SECRET_LEAK`，exit_code=99

### 4. 豁免机制

行内包含 `pragma: allowlist-secret why=<reason>` 可豁免：
- `TEST_VECTOR`: 解密测试向量
- `DOCS_EXAMPLE`: 文档示例
- `FIXTURE`: 测试固定数据

### 5. 私密目录隔离

`.claude/private/secrets/` **不复制到沙箱**。

### 6. 验收扫描范围

Smoke test 的 Secret-safe 扫描**仅检查 reflectloop 产生的工件**：

| 目标文件 | 检查项 |
|----------|--------|
| `.claude/state/reflectloop/reflectloop.latest.yaml` | env_status 只含 `<SET>/<UNSET>` |
| `.claude/state/reflectloop/runs/<run_id>/*.log` | 无 API key / token 模式 |
| `.claude/state/thinking/blocker.latest.yaml` | envelope.error_code 正确 |

**历史工件豁免**：`.claude/state/thinking/archive/` 和 `research.latest.yaml` 等历史文件中若出现 `SET/UNSET`（非 `<SET>/<UNSET>` 格式）属于格式差异，不算泄露。

## Reflection Loop (外层调用方算法)

Reflectloop 本身不做重试，由调用方控制反思闭环：

```
┌─────────────────────────────────────────────────────────────┐
│  1. /thingking_web → plan.latest.yaml                       │
│                                                              │
│  2. /reflectloop                                             │
│     ├─ SUCCESS → 生成 patch, summary → 结束                 │
│     └─ FAIL → blocker.latest.yaml (needs: RESEARCH|REPLAN)  │
│               + latch.lock                                   │
│                                                              │
│  3. 调用方检测 blocker.needs                                 │
│     ├─ RESEARCH → /thingking_web <query>                    │
│     └─ REPLAN → /thingking_web (重新规划)                   │
│                                                              │
│  4. 新 plan.latest.yaml (plan_source_hash 必须变化)         │
│                                                              │
│  5. 清理 latch.lock → 返回步骤 2                            │
│                                                              │
│  6. 重试次数 >= max_retries → STOP，人工介入                │
└─────────────────────────────────────────────────────────────┘
```

### 重试策略

| 项目 | 值 |
|------|-----|
| 默认最大重试 | 2~3 次 |
| 每轮必须 | `plan_source_hash` 变化 |
| 归档 | 每次 run 保留在 `runs/<run_id>/` |
| 日志 | 失败日志不覆盖（每次新 run_id） |
| 人工干预 | 保留失败状态，解锁后继续 |

### needs 判定启发式

| 条件 | needs | 说明 |
|------|-------|------|
| "not found", "no module", "import error" | RESEARCH | 依赖问题 |
| "version", "incompatible" | RESEARCH | 版本冲突 |
| "assert", "expected", "test failed" | REPLAN | 逻辑错误 |
| 其他/不确定 | RESEARCH | 默认 |

## Usage

### 基本调用

```powershell
# 默认执行
python -X utf8 analyzetools/reflectloop_sandbox.py

# 指定 plan
python -X utf8 analyzetools/reflectloop_sandbox.py --plan custom_plan.yaml

# 强制 copy 模式
python -X utf8 analyzetools/reflectloop_sandbox.py --mode copy
```

### 验收测试

```powershell
python -X utf8 analyzetools/verify/verify_reflectloop.py
```

### 查看结果

```powershell
# 检查 latest 工件
Get-Content .claude/state/reflectloop/reflectloop.latest.yaml -TotalCount 10

# 查看日志
Get-ChildItem .claude/state/reflectloop/runs/*/logs/*.log
```

## Integration

详见 [ROUTING.md](ROUTING.md)。

## References

| 规范 | 用途 |
|------|------|
| `.claude/rules/65-thinking-envelope.md` | envelope 通用规范 |
| `.claude/rules/70-mcp-cus.md` | MCP 脱敏规则 |
| `.claude/rules/50-failure-latch.md` | latch.lock 机制 |

## Files

```
.claude/skills/reflectloop-core/
├── SKILL.md          # 本文件（唯一事实源）
├── ROUTING.md        # 集成规则
└── examples/
    ├── plan.sample.yaml
    ├── blocker.sample.yaml
    └── reflectloop.latest.sample.yaml
```

---

*创建时间: 2025-12-28*
*优先级: HIGH - Reflectloop 执行必须遵守*
