---
description: Web comparison + differ + newplan (C~G full workflow)
argument-hint: [search topic or error message]
---
think harder.

## Envelope Output (REQUIRED FIRST)

**Every output MUST start with envelope:**

```yaml
envelope:
  command: thingking_web
  timestamp: <ISO8601>
  status: OK|ERROR
  error_code: <null|SEARCH_FAILED|MISSING_BLOCKER|NO_RESULTS|NSFW_CONTENT|SECRET_LEAK>
  missing_inputs: []
  artifacts_read:
    - .claude/state/thinking/blocker.latest.yaml
  artifacts_written:
    - .claude/state/thinking/research.latest.yaml
    - .claude/state/thinking/delta.latest.yaml
    - .claude/state/thinking/plan.latest.yaml
  next: "<first verification command from plan>"
```

**If status = ERROR: Output envelope then STOP. No further content.**

---

## Full Workflow: C → D → E → F → G

Execute the complete external research and replanning workflow for: "$ARGUMENTS"

---

## C. Web Research Pack

### Search Strategy

**难度自适应（引用 websearch Skill）**:

搜索参数按 topic 复杂度自动调整（见 `.claude/skills/websearch/SKILL.md` Section D）：

| 难度 | Queries | Results/Query | 并发 |
|------|---------|---------------|------|
| EASY | 3 | 5 | 1 |
| MEDIUM | 4-5 | 7 | 2 |
| HARD | 6 | 10 | 3 |

**HARD 触发条件**: 含 "最新/latest/对比/compare/方案/根因" 等关键词，或约束数>=3，或 topic>100字符

Query 优先级:
1. Official documentation
2. GitHub issues/discussions
3. Stack Overflow (verified answers)
4. Blog posts from maintainers

### MCP Search Execution (via websearch Skill)

**搜索执行委托给 websearch Skill**（见 `.claude/skills/websearch/SKILL.md`）。

websearch 内部使用以下工具（按优先级）：
1. `brave` (Brave Search API)
2. `tavily_remote` (Tavily Remote MCP)
3. `qwen` (Qwen + DashScope)
4. `freebird` (DuckDuckGo, 免费兜底)
5. Built-in `websearch` (fallback)

### Tool Probe (REQUIRED before search)

Before executing searches, probe tool availability and output:

```yaml
tool_probe:
  timestamp: <ISO8601>
  available:
    brave: <true|false>
    tavily_remote: <true|false>
    qwen: <true|false>
    freebird: true  # 无需 API key，始终可用
    websearch: true  # always available
  selected: websearch  # 使用聚合技能
  env_check:
    BRAVE_API_KEY: <SET|UNSET>
    TAVILY_MCP_URL: <SET|UNSET>
    DASHSCOPE_API_KEY: <SET|UNSET>
```

**Tool Probe Hard Rules**:
1. **URL 禁止**: 绝不输出包含 `://` 的环境变量值（尤其 TAVILY_MCP_URL）
2. **只允许状态**: env_check 字段只能输出 `SET` 或 `UNSET`，不输出实际值
3. **脱敏检查**: 如果发现输出中包含 `://`、`api_key=`、`token=`，必须立即 STOP 并报错

### NSFW Gate (via websearch Skill)

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
      next: "/thingking_web \"<topic>\" --allow-nsfw"
    STOP - 不生成 research_pack / D/E/F/G

ELIF websearch 返回 NSFW_FLAGGED AND allow_nsfw = true:
    继续执行，但在 research_pack.constraints 中添加:
      - constraint: "NSFW_ACKNOWLEDGED - 内容已确认，摘要已脱敏"
        source: "user-consent"
```

### Research Pack Output

```yaml
research_pack:
  status: OK|SEARCH_FAILED|NSFW_CONTENT
  topic: "$ARGUMENTS"
  tool_probe: <include tool_probe from above>
  queries:
    - query: <search string>
      tool_used: <websearch|brave|tavily_remote|qwen|freebird>  # websearch = 聚合技能
      results_count: <N>  # 聚合去重后的数量
  sources:
    - url: <URL>
      title: <page title>
      credibility: <OFFICIAL|MAINTAINER|COMMUNITY|BLOG>
      key_facts:
        - fact: <extracted fact>
          relevance: <HIGH|MEDIUM|LOW>
  recommended_goal: <what "done" looks like per sources>
  recommended_steps:
    - step: <action>
      source: <which URL supports this>
  constraints:
    - constraint: <limitation or requirement>
      source: <URL>
  pitfalls:
    - pitfall: <common mistake>
      fix: <how to avoid/fix>
      source: <URL>
  local_verification:
    - check: <command or file to verify>
      expected: <what success looks like>
```

**If research_pack.status = SEARCH_FAILED:**
1. Set envelope.status = ERROR
2. Set envelope.error_code = SEARCH_FAILED
3. Output envelope
4. **STOP - Do NOT generate D/E/F/G sections**

**If NSFW_CONTENT detected (websearch returns NSFW_FLAGGED) AND allow_nsfw = false:**
1. Set envelope.status = ERROR
2. Set envelope.error_code = NSFW_CONTENT
3. Set envelope.next = "/thingking_web \"<topic>\" --allow-nsfw"
4. Output envelope
5. **STOP - Do NOT generate research_pack/D/E/F/G sections**

**If SECRET_LEAK detected AND allow_secret_isolation = false:**
1. Set envelope.status = ERROR
2. Set envelope.error_code = SECRET_LEAK
3. Set envelope.next = "/thingking_web \"<topic>\" --allow-secret-isolation"
4. Output envelope
5. **STOP - 等待用户确认**

**If SECRET_LEAK detected AND allow_secret_isolation = true:**
1. 继续执行，但隔离敏感内容
2. 原始响应写入私有目录：`.claude/state/private/thinking/<timestamp>/`
3. 公开 research_pack 使用脱敏版本（secret 替换为 `<REDACTED>`）
4. 在 research_pack.warnings 中添加 `SECRET_ISOLATED`
5. envelope.artifacts_written_private 记录隔离路径

**allow_secret_isolation 判定规则（确定性）**：
```
allow_secret_isolation = (args 含 --allow-secret-isolation)
                      OR (topic 文本中包含以下任一 marker，大小写不敏感):
                         "API key", "token", "credential", "secret", "密钥", "凭证"
```

---

## D. Goal Differ (/goaldiffer)

Compare actual goal vs research-recommended goal.

```yaml
goal_delta:
  actual_goal: <current plan goal>
  research_goal: <recommended goal from sources>
  alignment: <ALIGNED|PARTIAL|DIVERGENT>
  conflicts:
    - conflict: <specific mismatch>
      impact: <HIGH|MEDIUM|LOW>
      resolution: <how to reconcile>
  unified_goal: <merged goal respecting constraints>
```

---

## E. Step Differ (/differ1)

Compare actual steps vs research-recommended steps.

```yaml
step_delta:
  items:
    - delta_type: <MISSING|EXTRA|WRONG_ORDER|WRONG_TOOL>
      description: <what's different>
      actual: <what we did/planned>
      research: <what sources recommend>
      evidence: <source URL or local file>
      impact: <HIGH|MEDIUM|LOW>
      fix: <proposed correction>
```

---

## F. Pitfall Differ (/differ2)

Compare actual pitfalls hit vs research-warned pitfalls.

```yaml
pitfall_delta:
  hit_pitfalls:
    - pitfall: <what we encountered>
      when: <step or timestamp>
      impact: <damage caused>
  warned_pitfalls:
    - pitfall: <what sources warn about>
      source: <URL>
      applies: <YES|NO|MAYBE>
  overlap:
    - pitfall: <matched between hit and warned>
  unique_hits:
    - pitfall: <we hit but sources didn't warn>
  unique_warnings:
    - pitfall: <sources warn but we didn't hit>
  guardrails:
    - guardrail: <preventive measure to add>
      prevents: <which pitfall>
```

---

## G. New Plan (/newplan)

Generate priority-scored plan from all deltas.

**Note**: The scoring algorithm below is a weighted linear model (not strict WSJF ratio formula).

### Scoring Algorithm

For each candidate task (existing + patches):

```
Score = 5*BlockerImpact + 3*GoalAlignment + 2*EvidenceStrength - 2*Risk - Effort

Where:
- BlockerImpact: 0-3 (3=immediately unblocks)
- GoalAlignment: 0-3 (3=directly advances unified goal)
- EvidenceStrength: 0-3 (3=official docs, 2=credible blog, 1=anecdote, 0=guess)
- Risk: 0-2 (2=high risk/irreversible)
- Effort: 0-2 (2=large effort)
```

### Plan Output

```yaml
new_plan:
  unified_goal: <from goal_delta>
  constraints:
    - <constraint from research>
  guardrails:
    - <guardrail from pitfall_delta>
  steps:
    - id: P-<seq>
      action: <what to do>
      rationale: <which delta this closes>
      score: <calculated score>
      score_breakdown:
        blocker_impact: <0-3>
        goal_alignment: <0-3>
        evidence_strength: <0-3>
        risk: <0-2>
        effort: <0-2>
      commands:
        - <exact command>
      files:
        - <file path>
      verification:
        - <how to verify success>
      rollback:
        - <how to undo if failed>
      depends_on: [<P-id list>]
  step_limit: 10
  total_steps: <N>
```

---

## Artifact Output (REQUIRED)

After generating output, write to state files:

```powershell
# Research Pack → .claude/state/thinking/research.latest.yaml
# Delta Matrix → .claude/state/thinking/delta.latest.yaml
# Plan → .claude/state/thinking/plan.latest.yaml
```

---

## Hard Rules

1. **Envelope first**: Output MUST start with envelope block
2. **Deterministic**: Steps sorted by Score DESC, ties broken by Risk ASC then Effort ASC
3. **Evidence-first**: Every step must cite source (URL or local evidence)
4. **Fail-closed**: If search fails or no results, output explicit SEARCH_FAILED status
5. **STOP on SEARCH_FAILED**: Do NOT generate deltas/plan if research_pack.status = SEARCH_FAILED
6. **STOP on ERROR**: If envelope.status = ERROR, output envelope then stop immediately
7. **Secret-safe (CRITICAL)**:
   - 公开输出绝不含 API key、token 的实际值
   - 绝不输出包含 `://` 的环境变量值（如 TAVILY_MCP_URL 的真实 URL）
   - tool_probe.env_check 只允许 `SET|UNSET`
   - 检测到敏感信息时：
     - allow_secret_isolation=false → ERROR(SECRET_LEAK) STOP，提示 --allow-secret-isolation
     - allow_secret_isolation=true → 继续执行，敏感内容隔离到私有目录，公开内容脱敏
8. **Max 10 steps**: Drop lowest-scored items if exceeds limit
9. **Verification required**: Every step must have verification command
10. **Tool probe required**: Always output tool_probe before search results
11. **Websearch delegation**: 搜索执行委托给 websearch Skill（聚合 brave/tavily/qwen/freebird/内置）
12. **NSFW Gate**:
    - 若 websearch 返回 NSFW_FLAGGED 且 allow_nsfw=false → ERROR(NSFW_CONTENT) STOP
    - allow_nsfw 自动同意: topic 含 NSFW/成人/色情/porn/adult/hentai 等 marker → 无需询问
    - 若 allow_nsfw=true → 继续执行，在 constraints 中标注 NSFW_ACKNOWLEDGED

## Final Summary

```
---
ENVELOPE: <status> | <error_code if any>
RESEARCH: <N> sources | <M> queries | <tool used>
GOAL: <alignment status> | <unified goal summary>
DELTAS: <step delta count> steps | <pitfall delta count> pitfalls
PLAN: <step count> steps | Top: <P-1 action> (score: <N>)
ARTIFACTS: research.latest.yaml, delta.latest.yaml, plan.latest.yaml
VERIFY: <first verification command>
---
```
