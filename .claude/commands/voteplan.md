---
description: 多源搜索→摘要→候选计划→确定性评分投票→落盘工件（含敏感脱敏/隔离）
argument-hint: [search topic or problem description] [--allow-nsfw]
allowed-tools: Bash(*), Read(*), Write(*), Edit(*), Glob(*), Grep(*), mcp__*
---
think harder.

## Voteplan: Multi-Source Search + Voting

> **唯一事实源**: [SKILL.md](../skills/voteplan-core/SKILL.md)

---

## Step -1: 参数检测与阻塞点自动提取

**如果 `$ARGUMENTS` 为空**，则自动从上下文提取搜索主题：

1. **优先读取 blocker.latest.yaml**:
   ```
   检查 .claude/state/thinking/blocker.latest.yaml
   如果存在且 envelope.status=OK:
     提取 blocker_statement 或 summary 作为搜索主题
   ```

2. **次选读取 HANDOFF.md Blockers 章节**:
   ```
   检查 analydocs/HANDOFF.md
   提取 ## Blockers 章节第一条作为搜索主题
   ```

3. **兜底：从对话上下文提取**:
   ```
   分析当前对话中的错误/阻塞描述
   提取最近的问题陈述作为搜索主题
   ```

4. **全部失败 → ERROR(INSUFFICIENT_INPUT) STOP**

**如果 `$ARGUMENTS` 非空**，直接使用作为搜索主题。

---

执行多源搜索、生成候选计划、确定性评分投票，为: "$ARGUMENTS"

---

## Step 0: Generate vote_id

```yaml
vote_id: <YYMMDDHHMMSS>-<4hex>
# 例: 251228153042-a7f3
```

创建目录结构:
- `.claude/state/planvote-search/<vote_id>/`
- `.claude/state/private/planvote/<vote_id>/`

---

## Step 1: Tool Probe

探测 MCP 搜索工具可用性（固定顺序: brave, tavily_remote, freebird, qwen）:

```yaml
tool_probe:
  timestamp: <ISO8601>
  available:
    brave: <true|false>
    tavily_remote: <true|false>
    freebird: <true|false>
    qwen: <true|false>
  env_status:
    BRAVE_API_KEY: <SET|UNSET>
    TAVILY_MCP_URL: <SET|UNSET>
    DASHSCOPE_API_KEY: <SET|UNSET>
  selected_tools: [<available tools>]
```

**Hard Rules**:
- **必须探测全部 4 个工具**（brave, tavily_remote, freebird, qwen），不得跳过
- 禁止 `unavailable_reason: "not probed"` - 每个工具必须有实际探测结果
- `env_status` 只允许 `SET|UNSET`，绝不输出实际值
- 至少 1 个工具可用才能继续
- 不可用工具记录 WARNING 并降级

---

## Step 2: Multi-Source Search (via websearch Skill)

**搜索执行委托给 websearch Skill**（见 `.claude/skills/websearch/SKILL.md`）。

websearch 内部按优先级使用：
1. `brave` (Brave Search API)
2. `tavily_remote` (Tavily Remote MCP)
3. `qwen` (Qwen + DashScope)
4. `freebird` (DuckDuckGo, 免费兜底)
5. Built-in `websearch` (fallback)

### 难度自适应（引用 websearch Skill）

搜索参数按 topic 复杂度自动调整（见 `.claude/skills/websearch/SKILL.md` Section D）：

| 难度 | Queries | Results/Query | 并发 |
|------|---------|---------------|------|
| EASY | 3 | 5 | 1 |
| MEDIUM | 4-5 | 7 | 2 |
| HARD | 6 | 10 | 3 |

**HARD 触发条件**: 含 "最新/latest/对比/compare/方案/根因" 等关键词，或约束数>=3，或 topic>100字符

**执行流程**：
- 按难度自适应规则生成搜索查询词
- 调用 websearch Skill 执行聚合搜索（复用难度自适应、分类摘要、去重）
- 按源分目录落盘：`<tool>/queryN_results.md`（未使用的源目录可空或写说明）

**敏感检查**:
- 原始响应若含敏感信息 → 写入私有目录
- 公开文件只保留脱敏版本

### NSFW Gate

**allow_nsfw 判定规则（确定性）**：

```
allow_nsfw = (args 含 --allow-nsfw)
          OR (topic 文本中包含以下任一 marker，大小写不敏感):
             NSFW, 成人, 色情, porn, adult, hentai, 18+, R18, エロ
```

**规则说明**：当 topic 明确包含上述 marker 时，视为用户已明确表达搜索 NSFW 内容的意图，自动同意。

**处理流程**：

```
IF websearch 返回 NSFW_FLAGGED AND allow_nsfw = false:
    输出 envelope:
      status: ERROR
      error_code: NSFW_CONTENT
      next: "/voteplan \"<topic>\" --allow-nsfw"
    STOP - 不生成 summary / candidates / score_log

ELIF websearch 返回 NSFW_FLAGGED AND allow_nsfw = true:
    允许继续，但：
    - public summary.md 添加风险提示 + 标记 NSFW_ACKNOWLEDGED
    - 原始/更敏感片段写入私有目录：.claude/state/private/planvote/<vote_id>/raw/
    - 公开 envelope.artifacts_written_private 仅列路径（不暴露内容）
```

---

## Step 3: Generate Summary

汇总所有搜索结果到 `summary.md`:

```markdown
# Summary: <topic>

## Section 1: <theme>
- Key finding 1 (Source: <URL>)
- Key finding 2 (Source: <URL>)

## Section 2: <theme>
...

## Constraints
- Constraint 1
- Constraint 2

## Pitfalls
- Pitfall 1 (Fix: ...)
```

---

## Step 4: Generate Candidate Plans

生成 2-4 个候选计划 (`candidates/plan_N.yaml`):

```yaml
envelope:
  command: voteplan
  vote_id: <VOTE_ID>
  candidate_index: <N>

new_plan:
  unified_goal: "<goal>"
  constraints: [...]
  guardrails: [...]
  steps:
    - id: P-1
      action: "<action>"
      rationale: "<why>"
      commands: [...]
      verification: [...]
      depends_on: []
```

---

## Step 5: Score and Vote

### 评分公式（锁死）

```
total = 3 * success + 2 * evidence + 1 * conciseness + 2 * risk_score
```

| 维度 | 范围 | 含义 |
|------|------|------|
| success | 0-5 | 成功可能性 |
| evidence | 0-5 | 证据强度 |
| conciseness | 0-5 | 简洁性 |
| risk_score | 0-5 | 安全性（越高越安全） |

### Tie-Breaker（锁死顺序）

1. `risk_score` 高者胜
2. `evidence` 高者胜
3. `steps_count` 少者胜
4. `plan_index` 小者胜

写入 `score_log.yaml`:
- 每个候选的分数明细
- evidence_refs（指向 summary.md）
- hashes（sha256）
- ranking + winner

---

## Step 6: Write Final Output

将 winner 复制到 `voteplan.<vote_id>.yaml`:
- 完整 envelope
- search_meta
- scoring_summary
- new_plan（从 winner 复制）

---

## Step 7: Sensitive Self-Check

> Patterns 引用自 [patterns.yaml](../skills/voteplan-core/patterns.yaml)

```powershell
$pub_dir = ".claude/state/planvote-search/<vote_id>"

# === Patterns from patterns.yaml ===
$PATTERN_TOKEN = '(tvly-|sk-|xai-)[A-Za-z0-9_-]{10,}'
$PATTERN_URL_SECRET = 'https?://[^\s"]+[?&](api_key|apikey|token|access_token|tavilyApiKey)=[^&\s"]+'
$PATTERN_PRAGMA = 'pragma:\s*allowlist-secret'

# === rg exit codes: 0=matches (FAIL), 1=no matches (OK), 2=error (ERROR) ===

rg -P $PATTERN_TOKEN $pub_dir       # 预期: exit 1
rg -P $PATTERN_URL_SECRET $pub_dir  # 预期: exit 1
rg $PATTERN_PRAGMA $pub_dir         # 预期: exit 1
```

Exit code 0 → ERROR (SECRET_LEAK) → STOP

---

## Output: Envelope-First

```yaml
envelope:
  command: voteplan
  vote_id: <VOTE_ID>
  timestamp: <ISO8601>
  status: OK|ERROR
  error_code: <null|TOOL_UNAVAILABLE|SEARCH_FAILED|NO_RESULTS|SECRET_LEAK|NSFW_CONTENT>
  warnings: [...]
  artifacts_written:
    - .claude/state/planvote-search/<vote_id>/summary.md
    - .claude/state/planvote-search/<vote_id>/score_log.yaml
    - .claude/state/voteplan.<vote_id>.yaml
  artifacts_written_private:
    - .claude/state/private/planvote/<vote_id>/...
  next: "<verification command>"
```

**If status = ERROR: Output envelope then STOP.**

---

## Final Summary

```
---
ENVELOPE: <status> | <error_code> | warnings: <N>
VOTE_ID: <vote_id>
TOOLS: <N> available | brave(<Y/N>), tavily_remote(<Y/N>), freebird(<Y/N>), qwen(<Y/N>)
QUERIES: <total> | results: <N>
CANDIDATES: <N> plans
WINNER: plan_<N> (total: <score>, tiebreak: <field or "none">)
ARTIFACTS: summary.md, score_log.yaml, voteplan.<vote_id>.yaml
NEXT: <command>
---
```

---

## Error Codes

| 错误码 | 级别 | 说明 |
|--------|------|------|
| TOOL_UNAVAILABLE | WARNING | 单个工具不可用（降级） |
| NO_TOOLS_AVAILABLE | ERROR | 所有工具不可用（STOP） |
| SEARCH_FAILED | ERROR | 所有查询失败（STOP） |
| NO_RESULTS | ERROR | 无相关结果（STOP） |
| PARTIAL_RESULTS | WARNING | 部分成功（OK+warnings） |
| WRITE_FAILED | ERROR | 写入失败（STOP） |
| SECRET_LEAK | ERROR | 检测到敏感信息（需用户确认后重跑 --allow-secret-isolation；若 topic 含密钥相关 marker 则自动同意隔离） |
| SECRET_ISOLATED | WARNING | 敏感内容已隔离到私有目录，公开内容已脱敏（OK + warning） |
| NSFW_CONTENT | ERROR | 检测到 NSFW 内容（需用户确认后重跑；若 topic 明确含 NSFW marker 则自动同意） |

---

## References

- [SKILL.md](../skills/voteplan-core/SKILL.md) - **唯一事实源**
- [patterns.yaml](../skills/voteplan-core/patterns.yaml) - **敏感扫描 Patterns 单一事实源**
- [CHECKLIST.md](../skills/voteplan-core/CHECKLIST.md) - 验收清单
- [verify_voteplan.ps1](../skills/voteplan-core/verify_voteplan.ps1) - 验证脚本
- [70-mcp-cus.md](../rules/70-mcp-cus.md) - MCP 工具 + 脱敏
- [65-thinking-envelope.md](../rules/65-thinking-envelope.md) - Envelope 规范
