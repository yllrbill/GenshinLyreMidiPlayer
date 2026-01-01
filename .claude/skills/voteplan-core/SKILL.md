---
name: voteplan-core
description: 多源搜索→摘要→候选计划→确定性评分投票→落盘工件（含敏感脱敏/隔离）
allowed-tools: Bash(*), Read(*), Write(*), Edit(*), Glob(*), Grep(*), mcp__*
---

# Voteplan Core Skill

## Purpose

Voteplan 是**多源搜索 + 候选计划评分投票**模块。从多个 MCP 搜索工具获取信息，汇总为摘要，生成候选计划，通过确定性评分算法选出最优计划。

**核心能力**：
- 多源搜索（brave, tavily_remote, freebird, qwen）+ 可用性探测
- 摘要提取 + 敏感信息脱敏
- 候选计划生成（最多 4 个）
- 确定性评分与投票（锁死权重/公式/tie-breaker）
- Envelope-First 输出 + 工件落盘

## Sources of Truth

> **本文件是 Voteplan 的唯一事实源。** 其它文件只能引用此处，不得重复定义契约。

| 文件 | 角色 |
|------|------|
| `.claude/skills/voteplan-core/SKILL.md` | **唯一事实源** |
| `.claude/skills/voteplan-core/patterns.yaml` | **敏感扫描 Patterns 单一事实源** |
| `.claude/skills/websearch/SKILL.md` | **搜索执行委托** (聚合搜索 + NSFW 门禁) |
| `.claude/commands/voteplan.md` | Thin wrapper（调用入口，用户可直接 /voteplan） |
| `.claude/rules/70-mcp-cus.md` | MCP 脱敏规则（继承） |
| `.claude/rules/65-thinking-envelope.md` | Envelope 规范（继承） |

---

## Trigger

Voteplan 被触发的条件：

1. **用户显式调用**：`/voteplan <topic>` 或 `/voteplan`（无参数）
2. **参数**：`$ARGUMENTS` 为搜索主题或问题描述

---

## Inputs

| 输入 | 必需 | 说明 |
|------|------|------|
| `$ARGUMENTS` | No | 搜索主题/问题描述（为空时自动提取） |
| `--allow-nsfw` | No | 显式允许 NSFW 内容的标志 |
| `--allow-secret-isolation` | No | 显式允许敏感信息隔离处理的标志 |
| 上下文文件 | No | 可选引用 @CLAUDE.md 等 |

### allow_nsfw 自动同意判定（确定性规则）

```
allow_nsfw = (args 含 --allow-nsfw)
          OR (topic 文本中包含以下任一 marker，大小写不敏感)
```

**NSFW 自动同意 Markers**：
- `NSFW`, `成人`, `色情`, `porn`, `adult`, `hentai`, `18+`, `R18`, `エロ`

**规则说明**：当 topic 明确包含上述 marker 时，视为用户已明确表达搜索 NSFW 内容的意图，自动同意，无需再次询问。

### allow_secret_isolation 自动同意判定（确定性规则）

```
allow_secret_isolation = (args 含 --allow-secret-isolation)
                      OR (topic 文本中包含以下任一 marker，大小写不敏感)
```

**Secret Isolation 自动同意 Markers**：
- `API key`, `token`, `credential`, `secret`, `密钥`, `凭证`, `认证`, `授权`

**规则说明**：当用户明确在搜索与密钥/凭证相关的主题时，自动允许隔离处理。敏感内容写入私有目录，公开摘要使用脱敏版本。

### 参数自动提取（当 $ARGUMENTS 为空时）

按以下优先级自动提取搜索主题：

1. **blocker.latest.yaml**:
   - 检查 `.claude/state/thinking/blocker.latest.yaml`
   - 提取 `blocker_statement` 或 `summary` 字段

2. **HANDOFF.md Blockers**:
   - 检查 `analydocs/HANDOFF.md`
   - 提取 `## Blockers` 章节第一条

3. **对话上下文**:
   - 分析当前对话中的错误/阻塞描述
   - 提取最近的问题陈述

4. **全部失败** → `ERROR(INSUFFICIENT_INPUT)` STOP

---

## Outputs (Envelope-First)

> **所有输出必须以 `envelope:` 开头。**

### Envelope 模板

```yaml
envelope:
  command: voteplan
  vote_id: <VOTE_ID>
  timestamp: <ISO8601>  # 必须为 RFC3339 格式，例如 2025-12-28T15:30:42Z
  status: OK|ERROR
  error_code: <null if OK, else error code>
  warnings: []  # OK 时也可能有 warnings
  missing_inputs: []
  artifacts_read: []
  artifacts_written_dirs:
    - .claude/state/planvote-search/<vote_id>/
  artifacts_written:
    - .claude/state/planvote-search/<vote_id>/query_manifest.yaml
    - .claude/state/planvote-search/<vote_id>/summary.md
    - .claude/state/planvote-search/<vote_id>/candidates/plan_1.yaml
    - .claude/state/planvote-search/<vote_id>/score_log.yaml
    - .claude/state/voteplan.<vote_id>.yaml
  artifacts_written_private:
    - .claude/state/private/planvote/<vote_id>/raw/...  # 仅路径，不泄露内容
  next: <suggested next command>
```

### Timestamp 规范

`envelope.timestamp` 必须遵循 **RFC3339** 格式：
- 4 位年份
- UTC 时区使用 `Z` 后缀
- 允许可选小数秒（如 `.123`）
- 示例：`2025-12-28T15:30:42Z` 或 `2025-12-28T15:30:42.123Z`
- 禁止：2 位年份、无时区、非 UTC 偏移

**验证 Pattern**：见 [patterns.yaml](patterns.yaml) `PATTERN_TIMESTAMP_RFC3339`

---

## Vote ID

### 生成规则

```
格式: YYMMDDHHMMSS-XXXX
示例: 251228153042-a7f3

其中:
- YYMMDDHHMMSS: UTC 时间戳
- XXXX: 4 位随机 hex（或 topic 的 SHA256 前 4 位）
```

### 唯一性要求

- vote_id **必须全局唯一**
- 禁止覆盖历史工件（每次新 vote_id）
- 所有工件路径必须包含 vote_id

---

## Directory Structure

### 公开工件目录

```
.claude/state/planvote-search/<vote_id>/
├── brave/
│   ├── query1_results.md
│   ├── query2_results.md
│   └── query3_results.md
├── tavily_remote/
│   ├── query1_results.md
│   └── ...
├── freebird/
│   └── ...
├── qwen/
│   └── ...
├── summary.md                    # 汇总摘要（已脱敏）
├── query_manifest.yaml          # 查询清单（可复跑）
├── candidates/
│   ├── plan_1.yaml
│   ├── plan_2.yaml
│   ├── plan_3.yaml
│   └── plan_4.yaml
└── score_log.yaml               # 评分日志

.claude/state/
└── voteplan.<vote_id>.yaml      # 主输出（最终计划）
```

### 私有隔离目录

```
.claude/state/private/planvote/<vote_id>/
├── raw/
│   ├── brave/
│   │   └── query1_raw.json      # 未脱敏原始响应
│   ├── tavily_remote/
│   │   └── ...
│   └── ...
└── debug/
    └── tool_probe.yaml          # 完整环境信息（可能含敏感）
```

**私有目录规则**：
- 仅作本地审计留存
- 不在对话输出正文展开内容
- `.gitignore` 应包含 `.claude/state/private/`

---

## Tool Set (Fixed Order)

### 工具优先级（锁死顺序）

| 优先级 | 工具 ID | MCP Server | 说明 |
|--------|---------|------------|------|
| 1 | `brave` | brave | Brave Search API |
| 2 | `tavily_remote` | tavily-remote | Tavily Remote MCP (HTTP) |
| 3 | `freebird` | freebird | DuckDuckGo (免费兜底) |
| 4 | `qwen` | qwen_fallback | Qwen + DashScope |

### Tool Probe (必需步骤)

运行前必须探测各工具可用性：

```yaml
tool_probe:
  timestamp: <ISO8601>
  available:
    brave: <true|false>
    tavily_remote: <true|false>
    freebird: <true|false>
    qwen: <true|false>
  unavailable_reason:
    brave: <null|"env BRAVE_API_KEY not set"|"connection failed">
    tavily_remote: <null|"env TAVILY_MCP_URL not set">
    freebird: <null|"...">
    qwen: <null|"env DASHSCOPE_API_KEY not set">
  env_status:
    BRAVE_API_KEY: <SET|UNSET>
    TAVILY_MCP_URL: <SET|UNSET>
    DASHSCOPE_API_KEY: <SET|UNSET>
  selected_tools: [<list of available tools>]
  min_tools_required: 1
```

**Tool Probe 规则**：
1. **必须探测全部 4 个工具**（brave, tavily_remote, freebird, qwen），不得跳过任何一个
2. 至少 1 个工具可用才能继续
3. 不可用的工具记录 warning 并降级
4. `env_status` 只允许 `SET|UNSET`（绝不输出实际值）
5. 禁止 `unavailable_reason: "not probed"` - 每个工具必须有实际探测结果

### 难度自适应查询参数

> 引用 `.claude/skills/websearch/SKILL.md` Section D（唯一事实源）

| 难度 | 判定条件 | Queries | Results/Query | 并发 |
|------|----------|---------|---------------|------|
| **EASY** | 单一明确问题，无复杂约束 | 3 | 5 | 1 |
| **MEDIUM** | 有 2-3 个约束或需要对比 | 4-5 | 7 | 2 |
| **HARD** | 含特定关键词或高复杂度 | 6 | 10 | 3 |

**HARD 触发条件（满足任一）**:
- 含关键词: "最新" "latest" "对比" "compare" "方案" "solution" "根因" "root cause"
- 含关键词: "多平台" "cross-platform" "兼容" "compatibility"
- 约束数 >= 3（通过 AND/且/并且 计数）
- topic 长度 > 100 字符
- 含版本号对比（如 "v1 vs v2"）

总查询数 = Queries × 可用工具数（按难度动态调整）

---

## Sensitive Information Rules

### 敏感匹配 Patterns

> **单一事实源**：[patterns.yaml](patterns.yaml)
>
> 以下为简要说明，完整 PCRE2 正则定义见 patterns.yaml。

| Pattern | 用途 |
|---------|------|
| `PATTERN_TOKEN_PCRE2` | API tokens (tvly-, sk-, xai-) |
| `PATTERN_URL_SECRET_PCRE2` | URL 中的敏感参数 |
| `PATTERN_PRAGMA` | allowlist pragma（禁止在公开工件） |
| `PATTERN_TIMESTAMP_RFC3339` | 时间戳格式验证 |

**环境变量名**（出现即视为敏感值载体）：
- `BRAVE_API_KEY`
- `DASHSCOPE_API_KEY`
- `TAVILY_MCP_URL`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### 脱敏规则（公开工件）

| 场景 | 处理 |
|------|------|
| 命中 key/token 值 | 替换为 `<REDACTED>` |
| URL 含 secret 参数 | 保留 `scheme://host/path`，参数值替换为 `<REDACTED>` |
| 环境变量值 | 只输出 `SET` 或 `UNSET`，绝不输出实际值 |

**示例**：
```
# 原始
https://api.tavily.com/search?apiKey=tvly-xxxxx123

# 脱敏后
https://api.tavily.com/search?apiKey=<REDACTED>
```

### 私有隔离规则

| 场景 | 处理 |
|------|------|
| Raw 响应含敏感字段 | 只写入私有目录 `.claude/state/private/planvote/<vote_id>/raw/` |
| 公开摘要中 | 写 "原始响应已存私有目录，摘要已脱敏" |
| Envelope 中 | `artifacts_written_private` 仅列路径，不泄露内容 |

### 豁免机制

行内包含 `# pragma: allowlist-secret why=<reason>` 可豁免，**但仅限以下位置**：
- `.claude/skills/voteplan/templates/**`（文档/模板文件）

**豁免理由（合法）**：
- `DOCS_EXAMPLE`: 文档示例
- `FIXTURE`: 测试固定数据
- `PUBLIC_SAMPLE`: 公开示例 URL

**禁止位置**：
- 公开工件目录（`.claude/state/planvote-search/<vote_id>/`）
- 主输出文件（`.claude/state/voteplan.<vote_id>.yaml`）

敏感自检时，若在公开工件中发现 `pragma: allowlist-secret`，视为 **SECRET_LEAK** 并 STOP。

---

## Scoring Algorithm (Locked)

### 评分量表

所有评分使用 **0-5 整数** 量表：

| 维度 | 范围 | 含义 |
|------|------|------|
| `success` | 0-5 | 成功可能性（5=非常可能成功） |
| `evidence` | 0-5 | 证据强度（5=官方文档/多源佐证） |
| `conciseness` | 0-5 | 简洁性（5=步骤最少且完整） |
| `risk_score` | 0-5 | 安全性（5=风险最低，0=高风险） |

**注意**：`risk_score` 越高表示**越安全/风险越低**（非反向）。

### 权重与公式（锁死）

```
total = 3 * success + 2 * evidence + 1 * conciseness + 2 * risk_score
```

**最高分**：3*5 + 2*5 + 1*5 + 2*5 = 15 + 10 + 5 + 10 = 40

### Tie-Breaker 规则（锁死顺序）

当 `total` 相同时，依次比较：

1. `risk_score` 高者胜（更安全优先）
2. `evidence` 高者胜（证据更强优先）
3. `steps_count` 少者胜（更简洁优先）
4. `plan_index` 小者胜（先生成者优先）

### score_log.yaml 结构

```yaml
envelope:
  command: voteplan
  vote_id: <VOTE_ID>
  timestamp: <ISO8601>
  status: OK

candidates:
  - plan_index: 1
    plan_file: candidates/plan_1.yaml
    scores:
      success: 4
      evidence: 5
      conciseness: 3
      risk_score: 4
    total: 34  # 3*4 + 2*5 + 1*3 + 2*4 = 12+10+3+8
    steps_count: 7
    evidence_refs:
      - summary.md#section-1-line-15
      - summary.md#section-2-line-42
    hashes:
      plan_sha256: <sha256 of plan_1.yaml>

  - plan_index: 2
    plan_file: candidates/plan_2.yaml
    scores:
      success: 5
      evidence: 4
      conciseness: 4
      risk_score: 3
    total: 34  # 3*5 + 2*4 + 1*4 + 2*3 = 15+8+4+6
    steps_count: 5
    evidence_refs:
      - summary.md#section-1-line-20
    hashes:
      plan_sha256: <sha256 of plan_2.yaml>

ranking:
  - plan_index: 1
    total: 34
    tiebreak_reason: "risk_score (4 > 3)"
  - plan_index: 2
    total: 34
    tiebreak_reason: null

winner:
  plan_index: 1
  plan_file: candidates/plan_1.yaml
  total: 34
  tiebreak_applied: true
  tiebreak_field: risk_score
```

---

## query_manifest.yaml 结构（可复跑）

为确保搜索过程可复跑、可审计，必须写入查询清单：

```yaml
envelope:
  command: voteplan
  vote_id: <VOTE_ID>
  timestamp: <ISO8601>

tools:
  - tool_id: brave
    available: true
  - tool_id: tavily_remote
    available: true
  - tool_id: freebird
    available: true
  - tool_id: qwen
    available: false
    unavailable_reason: "env DASHSCOPE_API_KEY not set"

queries:
  - tool_id: brave
    query_index: 1
    query_text: "AES-128-ECB decryption Python"
    results_count: 8
    result_file: brave/query1_results.md

  - tool_id: brave
    query_index: 2
    query_text: "set_ccz_decrypt_key Cocos2dx"
    results_count: 3
    result_file: brave/query2_results.md

  - tool_id: tavily_remote
    query_index: 1
    query_text: "neox.xml decryption"
    results_count: 5
    result_file: tavily_remote/query1_results.md
  # ... 更多查询

total_queries: 9
total_results: 27
```

---

## Plan Format (Aligned with plan.latest.yaml)

候选计划文件必须与 `plan.latest.yaml` 结构对齐：

```yaml
envelope:
  command: voteplan
  vote_id: <VOTE_ID>
  candidate_index: 1
  timestamp: <ISO8601>

new_plan:
  unified_goal: "<goal description>"
  constraints:
    - <constraint 1>
    - <constraint 2>
  guardrails:
    - <guardrail from research>

  steps:
    - id: P-1
      action: "Description of what this step does"
      rationale: "Why this step, evidence source"
      commands:
        - "python -X utf8 script.py"
      files:
        - path/to/file.py
      cwd: "optional/subdirectory"
      verification:
        - "Expected output or state"
      rollback:
        - "How to undo"
      depends_on: []

    - id: P-2
      action: "Next step"
      # ...

  step_limit: 10
  total_steps: <N>
```

---

## Error Codes

| 错误码 | 级别 | 含义 | 触发条件 | 后续行为 |
|--------|------|------|----------|----------|
| `TOOL_UNAVAILABLE` | WARNING | 工具不可用 | 单个 MCP 工具不可用 | 降级继续（记录 warnings） |
| `NO_TOOLS_AVAILABLE` | ERROR | 无可用工具 | 所有工具都不可用 | **STOP** |
| `SEARCH_FAILED` | ERROR | 搜索失败 | 所有查询返回错误 | **STOP** |
| `NO_RESULTS` | ERROR | 无搜索结果 | 搜索成功但无相关结果 | **STOP** |
| `PARTIAL_RESULTS` | WARNING | 部分结果 | 部分工具成功/部分失败 | OK + warnings |
| `WRITE_FAILED` | ERROR | 写入失败 | 工件写入失败 | **STOP** |
| `SECRET_LEAK` | ERROR | 敏感信息 | 检测到敏感信息且 allow_secret_isolation=false | **STOP** (提示重跑 --allow-secret-isolation) |
| `SECRET_ISOLATED` | WARNING | 敏感已隔离 | 检测到敏感信息且 allow_secret_isolation=true | OK + warning（敏感内容隔离到私有目录） |
| `NSFW_CONTENT` | ERROR | NSFW 内容 | websearch 返回 NSFW_FLAGGED 且 allow_nsfw=false | **STOP** (提示重跑 --allow-nsfw) |
| `INSUFFICIENT_INPUT` | ERROR | 输入不足 | `$ARGUMENTS` 为空且无法自动提取 | **STOP** |

### Envelope 带 warnings 示例

```yaml
envelope:
  command: voteplan
  vote_id: 251228153042-a7f3
  timestamp: 2025-12-28T15:30:42Z
  status: OK
  error_code: null
  warnings:
    - code: TOOL_UNAVAILABLE
      tool: qwen
      reason: "env DASHSCOPE_API_KEY not set"
    - code: PARTIAL_RESULTS
      detail: "brave returned 0 results for query 2"
  # ...
```

### STOP 条件

当 `status: ERROR` 时：
1. 输出完整 envelope
2. **不生成后续内容**（candidates, score_log 等）
3. 在 `next` 字段给出修复建议

---

## Workflow

### 完整流程

```
1. 解析 $ARGUMENTS
   ↓ 空 → ERROR (INSUFFICIENT_INPUT)
   ↓ 判定 allow_nsfw (args 含 --allow-nsfw 或 topic 含 NSFW marker)
   ↓ 判定 allow_secret_isolation (args 含 --allow-secret-isolation 或 topic 含密钥 marker)

2. 生成 vote_id (YYMMDDHHMMSS-XXXX)
   ↓ 创建目录结构

3. Tool Probe
   ↓ 所有工具不可用 → ERROR (NO_TOOLS_AVAILABLE)
   ↓ 部分不可用 → WARNING (TOOL_UNAVAILABLE) + 继续

4. 多源搜索 (委托 websearch Skill)
   ↓ websearch 返回 SECRET_LEAK 且 allow_secret_isolation=false → ERROR (SECRET_LEAK) STOP
   ↓ websearch 返回 SECRET_LEAK 且 allow_secret_isolation=true → 继续 (标记 SECRET_ISOLATED)
   ↓ websearch 返回 NSFW_FLAGGED 且 allow_nsfw=false → ERROR (NSFW_CONTENT) STOP
   ↓ websearch 返回 NSFW_FLAGGED 且 allow_nsfw=true → 继续 (标记 NSFW_ACKNOWLEDGED)
   ↓ 全部失败 → ERROR (SEARCH_FAILED)
   ↓ 无结果 → ERROR (NO_RESULTS)
   ↓ 部分成功 → WARNING (PARTIAL_RESULTS) + 继续

5. 写入 query_results.md（按工具分目录）
   ↓ 敏感检查 → 原始写私有目录，公开写脱敏版
   ↓ SECRET_ISOLATED → 原始写私有目录，公开写 <REDACTED> 版本
   ↓ NSFW 内容 → 标记 NSFW_ACKNOWLEDGED

5b. 写入 query_manifest.yaml（可复跑清单）

6. 生成 summary.md（汇总 + 脱敏）
   ↓ 若 SECRET_ISOLATED → 敏感值替换为 <REDACTED>
   ↓ 若 NSFW_ACKNOWLEDGED → 标记已确认

7. 生成候选计划（plan_1.yaml ~ plan_4.yaml）
   ↓ 对齐 new_plan + steps 格式

8. 评分投票
   ↓ 计算 total = 3*success + 2*evidence + 1*conciseness + 2*risk_score
   ↓ Tie-break: risk_score → evidence → steps_count → plan_index

9. 写入 score_log.yaml

10. 写入 voteplan.<vote_id>.yaml（winner 复制 + envelope）

11. 敏感自检（rg 扫描公开目录）
    ↓ 命中且 allow_secret_isolation=false → ERROR (SECRET_LEAK)
    ↓ 命中且 allow_secret_isolation=true → WARNING (SECRET_ISOLATED)

12. 输出 Envelope + Final Summary
```

### NSFW 门禁详细处理

**If websearch returns NSFW_FLAGGED AND allow_nsfw = false:**
1. Set envelope.status = ERROR
2. Set envelope.error_code = NSFW_CONTENT
3. Set envelope.next = "/voteplan \"<topic>\" --allow-nsfw"
4. Output envelope
5. **STOP - Do NOT generate summary/candidates/score_log**

**If websearch returns NSFW_FLAGGED AND allow_nsfw = true:**
1. 允许继续执行
2. 标记 NSFW_ACKNOWLEDGED
3. 无内容限制
4. 原始/敏感片段写入私有隔离目录: `.claude/state/private/planvote/<vote_id>/nsfw/`

### websearch Skill 委托

搜索执行委托给 `.claude/skills/websearch/SKILL.md`，复用：
- 难度自适应（EASY/MEDIUM/HARD）
- NSFW 检测与处理
- Secret-safe 保护
- 分类摘要生成

仍需按源分目录落盘（brave/, tavily_remote/, freebird/, qwen/），未使用的源目录可写说明文件。

### 敏感自检命令

> Patterns 引用自 [patterns.yaml](patterns.yaml)

```powershell
# 扫描公开工件目录（排除私有目录）
$vote_id = "<VOTE_ID>"
$pub_dir = ".claude/state/planvote-search/$vote_id"

# === Patterns from patterns.yaml ===
$PATTERN_TOKEN = '(tvly-|sk-|xai-)[A-Za-z0-9_-]{10,}'
$PATTERN_URL_SECRET = 'https?://[^\s"]+[?&](api_key|apikey|token|access_token|tavilyApiKey)=[^&\s"]+'
$PATTERN_PRAGMA = 'pragma:\s*allowlist-secret'

# === rg exit codes: 0=matches, 1=no matches (OK), 2=error (FAIL) ===

# Token 模式
rg -P $PATTERN_TOKEN $pub_dir
# 预期: exit code 1 (no matches)

# URL 携带 secret
rg -P $PATTERN_URL_SECRET $pub_dir
# 预期: exit code 1 (no matches)

# pragma 出现在公开工件（禁止）
rg $PATTERN_PRAGMA $pub_dir
# 预期: exit code 1 (no matches)
```

**Exit Code 解释**:
| Exit Code | 含义 | 敏感扫描结果 |
|-----------|------|-------------|
| 0 | 有匹配 | **FAIL** - 发现敏感信息 |
| 1 | 无匹配 | **OK** - 安全 |
| 2 | 错误 | **ERROR** - 路径/权限问题 |

---

## Usage

### 基本调用

```
/voteplan "how to decrypt AES-128-ECB with unknown key"
```

### 带上下文调用

```
/voteplan "fix ModuleNotFoundError for frida" @analydocs/RUNBOOK.md
```

### 查看输出

```powershell
# 查看最新 voteplan 结果
Get-ChildItem .claude/state/voteplan.*.yaml | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content

# 查看 score_log
Get-Content .claude/state/planvote-search/<vote_id>/score_log.yaml

# 查看候选计划
Get-ChildItem .claude/state/planvote-search/<vote_id>/candidates/
```

---

## Final Summary Template

```
---
ENVELOPE: <status> | <error_code if any> | warnings: <N>
VOTE_ID: <vote_id>
TOOLS: <N> available | probed: brave(<Y/N>), tavily_remote(<Y/N>), freebird(<Y/N>), qwen(<Y/N>)
QUERIES: <total queries> | <total results>
CANDIDATES: <N> plans generated
WINNER: plan_<N> (total: <score>, tiebreak: <field or "none">)
ARTIFACTS:
  - .claude/state/planvote-search/<vote_id>/summary.md
  - .claude/state/planvote-search/<vote_id>/score_log.yaml
  - .claude/state/voteplan.<vote_id>.yaml
NEXT: <suggested verification command>
---
```

---

## References

| 规范 | 用途 |
|------|------|
| `.claude/rules/65-thinking-envelope.md` | Envelope 通用规范 |
| `.claude/rules/70-mcp-cus.md` | MCP 工具优先级 + 脱敏规则 |
| `.claude/skills/reflectloop-core/SKILL.md` | 执行闭环（voteplan 输出可作为输入） |

---

## Files

```
.claude/skills/voteplan/
├── SKILL.md              # 本文件（唯一事实源）
├── patterns.yaml         # 敏感扫描 Patterns 单一事实源
├── CHECKLIST.md          # 验收清单
├── verify_voteplan.ps1   # 验证脚本
└── templates/
    ├── score_log.sample.yaml
    └── voteplan.sample.yaml
```

---

*创建时间: 2025-12-28*
*优先级: HIGH - Voteplan 执行必须遵守*
