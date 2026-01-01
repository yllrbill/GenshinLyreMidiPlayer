# Reflectloop Envelope Protocol

> **唯一事实源**: [.claude/skills/reflectloop-core/SKILL.md](../skills/reflectloop-core/SKILL.md)
>
> 本文件作为规范附录，详细说明 envelope 协议。所有契约、错误码定义请参见 Skill 文档。

## 概述

Reflectloop 是一个可被其他推理命令调用的"执行闭环"模块。它在沙箱中按 plan.latest.yaml 的步骤执行，以 exit code 判定成功/失败。

## Envelope 输出规范

所有 Reflectloop 输出必须以 envelope 开头：

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
  next: <suggested next command>
```

## 错误码定义

| 错误码 | 含义 | 触发条件 | 后续行为 |
|--------|------|----------|----------|
| MISSING_PLAN | Plan 文件缺失 | plan.latest.yaml 不存在 | **STOP** - 提示先运行 /thingking_web |
| INVALID_PLAN | Plan 格式无效 | 无法解析或无可执行步骤 | **STOP** - 检查 plan 格式 |
| SANDBOX_CREATE_FAILED | 沙箱创建失败 | worktree/copy 都失败 | **STOP** - 检查磁盘空间/权限 |
| STEP_FAILED | 步骤执行失败 | 命令返回非 0 exit code | **STOP** - 写 blocker + latch.lock |
| SECRET_LEAK | 敏感信息泄露 | 检测到 API key 等 | **STOP** - fail-closed |
| MAX_RETRIES | 超过重试次数 | 已重试 N 次仍失败 | **STOP** - 需要人工介入 |
| LATCHED | 会话已锁定 | latch.lock 存在 | **STOP** - 先解锁再执行 |
| SANDBOX_ESCAPE | cwd 逃逸 | step.cwd 解析到沙箱外 | **STOP** - 修正 plan 中的 cwd |

## 输入依赖

### 必需

| 工件 | 路径 | 说明 |
|------|------|------|
| Plan | `.claude/state/thinking/plan.latest.yaml` | 来自 /thingking_web 的执行计划 |

### Plan 结构要求

```yaml
envelope:
  command: thingking_web
  status: OK
  # ...

new_plan:
  steps:
    - id: P-1
      action: "Description of what this step does"
      commands:
        - "python -X utf8 script.py"
        - "npm test"
      cwd: "optional/subdirectory"
      verification:
        - "Expected output or state"
      depends_on: []
```

## 输出工件

### 成功时

| 工件 | 路径 | 说明 |
|------|------|------|
| Result | `.claude/state/reflectloop/reflectloop.latest.yaml` | 执行结果 |
| Patch | `.claude/state/reflectloop/runs/<run_id>/changes.patch` | 变更补丁 |
| Summary | `.claude/state/reflectloop/runs/<run_id>/summary.md` | 执行摘要 |
| Logs | `.claude/state/reflectloop/runs/<run_id>/logs/*.log` | 步骤日志 |

### 失败时

| 工件 | 路径 | 说明 |
|------|------|------|
| Result | `.claude/state/reflectloop/reflectloop.latest.yaml` | 执行结果 (status=ERROR) |
| Blocker | `.claude/state/thinking/blocker.latest.yaml` | 阻塞点卡片 |
| Lock | `$HOME/.claude/latch.lock` | 失败锁存 |
| Logs | `.claude/state/reflectloop/runs/<run_id>/logs/*.log` | 步骤日志 |

## 与 /thinking 路由集成

失败后 Reflectloop 写入的 blocker.latest.yaml 会触发 /thinking 路由：

```yaml
# blocker.latest.yaml (由 reflectloop 写入)
envelope:
  command: reflectloop
  status: ERROR
  error_code: STEP_FAILED
  next: "/thinking"

blocker_id: B-251228-XXXXXX
needs: [RESEARCH]  # 或 [REPLAN]
# ...
```

`/thinking` 路由器检测到此 blocker 后：
- `needs: [RESEARCH]` → 路由到 `/thingking_web`
- `needs: [REPLAN]` → 路由到 `/thingking_web` 重新规划

## needs 判定启发式

| 条件 | needs | 说明 |
|------|-------|------|
| "not found", "no module", "import error" | RESEARCH | 依赖问题，需要外部研究 |
| "version", "incompatible" | RESEARCH | 版本冲突 |
| "assert", "expected", "test failed" | REPLAN | 逻辑错误，需要重新规划 |
| 其他/不确定 | RESEARCH | 默认需要研究 |

## Secret-Safe 规则

### 必须遵守

1. **env_status 只写 SET/UNSET**
   ```yaml
   env_status:
     BRAVE_API_KEY: <SET>      # 正确
     TAVILY_MCP_URL: <UNSET>   # 正确
     # DASHSCOPE_API_KEY: sk-xxx  # 禁止！
   ```

2. **日志输出扫描**
   - 执行每个命令后扫描 stdout/stderr
   - 发现敏感模式则 fail-closed
   - 写入 error_code: SECRET_LEAK

3. **敏感模式定义**
   ```regex
   # API key 赋值
   (TAVILY|BRAVE|DASHSCOPE).*(API_KEY|MCP_URL)\s*[:=]\s*[^\s"'<]+

   # Token 模式
   [:=]\s*(tvly-|sk-)[A-Za-z0-9_-]{10,}

   # URL 携带 secret
   https?://.*[?&](api_key|token|apikey)=[^&\s]+
   ```

4. **豁免机制**
   - 行内包含 `pragma: allowlist-secret why=<reason>` 可豁免
   - 合法理由: TEST_VECTOR, DOCS_EXAMPLE, FIXTURE

## 沙箱策略

### 默认位置 (Fix #1)

沙箱默认创建在**项目目录外**（系统临时目录），避免递归复制风险：

```
Windows: %TEMP%\reflectloop\<run_id>\repo
Unix: /tmp/reflectloop/<run_id>/repo
```

### 快路径 (优先)

```
条件: 项目是 git repo 且 git 可用 且工作区干净
方法: git worktree add --detach
优点: 快速、结构一致、支持 git diff
注意: 若工作区有未提交改动，自动降级到 copy 模式 (Fix #3)
```

### 兼容路径 (fallback)

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

## 执行模型

```
1. 解析 plan.latest.yaml
   ↓ 失败 → ERROR (MISSING_PLAN / INVALID_PLAN)
2. 创建沙箱 (worktree → copy fallback)
   ↓ 失败 → ERROR (SANDBOX_CREATE_FAILED)
3. 逐步执行 commands[]
   ↓ 步骤失败 → fail-fast
   ↓ secret 泄露 → fail-closed
4. 成功 → 生成 patch + summary
   失败 → 写 blocker + latch.lock
5. 清理沙箱（保留日志）
```

## 重试策略

Reflectloop 本身不做重试，由调用方控制：

1. 第 1 次失败 → 写工件 → 交给 /thinking
2. /thinking → /thingking_web 产出新 plan
3. 调用方再次调用 reflectloop

默认 max_retries=2，由参数控制。

## 验收命令

```powershell
# 运行 reflectloop
python -X utf8 analyzetools/reflectloop_sandbox.py --plan .claude/state/thinking/plan.latest.yaml

# 检查输出
Test-Path .claude/state/reflectloop/reflectloop.latest.yaml
Get-Content .claude/state/reflectloop/reflectloop.latest.yaml -TotalCount 5
```

---

*优先级: HIGH - Reflectloop 执行必须遵守*
*创建时间: 2025-12-28*
