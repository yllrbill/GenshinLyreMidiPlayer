# Thinking Command Envelope Protocol

## 统一输出结构

所有 `/thingking*` 命令必须使用以下 envelope 格式：

```yaml
envelope:
  command: <thingking|thingking_web>
  timestamp: <ISO8601>
  status: OK|ERROR
  error_code: <null if OK, else: see error codes below>
  missing_inputs: []  # list of required but missing inputs
  artifacts_read:
    - path: <file path>
  artifacts_written:
    - path: <file path>
  next: <suggested next command with args>

# ... command-specific content follows ...
```

## 错误码定义

### /thingking 命令 (本地分析)

| 错误码 | 含义 | 触发条件 | 后续行为 |
|--------|------|----------|----------|
| INSUFFICIENT_CONTEXT | 上下文不足 | 无法确定阻塞点 | **STOP** - 请求更多信息 |
| MISSING_EVIDENCE | 证据缺失 | 无法找到支持性证据 | **STOP** - 提示收集证据 |

### /thingking_web 命令 (外部研究)

| 错误码 | 含义 | 触发条件 | 后续行为 |
|--------|------|----------|----------|
| SEARCH_FAILED | 所有搜索工具失败 | MCP 搜索全部返回错误 | **STOP** - 不生成 delta/plan |
| MISSING_BLOCKER | 缺少 blocker | 无 blocker.latest.yaml | **STOP** - 提示先跑 /thingking |
| NO_RESULTS | 无搜索结果 | 搜索成功但无相关结果 | **STOP** - 建议调整搜索词 |

### 通用错误码

| 错误码 | 含义 | 触发条件 | 后续行为 |
|--------|------|----------|----------|
| MISSING_ARTIFACT | 工件缺失 | 依赖的 .latest.yaml 不存在 | **STOP** - 提示创建 |
| INSUFFICIENT_INPUT | 输入不足 | 必要参数缺失 | **STOP** - 列出缺失项 |

## STOP 条件强制执行

**CRITICAL**: 当 `status: ERROR` 时，命令必须：

1. 输出完整 envelope
2. **不生成后续内容**（如 delta、plan）
3. 在 `next` 字段给出修复建议

错误示例：
```yaml
envelope:
  command: thingking_web
  timestamp: 2025-12-28T10:30:00Z
  status: ERROR
  error_code: SEARCH_FAILED
  missing_inputs: []
  artifacts_read: []
  artifacts_written: []
  next: "/mcp-cus 检查 MCP 配置，然后重试 /thingking_web"

# NO FURTHER CONTENT - STOP HERE
```

## 成功示例

```yaml
envelope:
  command: thingking
  timestamp: 2025-12-28T10:30:00Z
  status: OK
  error_code: null
  missing_inputs: []
  artifacts_read: []
  artifacts_written:
    - .claude/state/thinking/blocker.latest.yaml
    - .claude/state/thinking/trail.latest.yaml
  next: "/thingking_web 'AES ECB decryption'"

blocker_id: B-251228-a1b2c3
# ... rest of blocker content ...
```

## 与 /thinking 路由集成

`/thinking` 路由器读取最新工件的 envelope 来判断状态：

1. 读取 `*.latest.yaml`
2. 检查 `envelope.status`
3. 如果 ERROR → 显示错误，不自动路由
4. 如果 OK → 根据 `envelope.next` 或 `needs` 字段路由

## 工件文件格式

每个 `.claude/state/thinking/*.latest.yaml` 必须：

1. 以 `envelope:` 开头
2. 包含完整 envelope 结构
3. envelope 后跟命令特定内容

---

## 自检命令 (CI/脚本用) — NO-FP

> 目标：只命中"疑似真实泄露"，避免扫到文档自身导致误报。
> 建议在仓库根目录执行（`d:\dw11\`）。优先使用 ripgrep（`rg`）。

### 1) 检查是否有直接路由到 /cc-* 的代码

```bash
# 精确匹配 route 行（只匹配实际路由配置，不匹配说明文本）
rg -n '^\s*route:\s*/cc-' .claude/commands/thinking.md
# 预期输出：无（空）

# 检查 routed_to 字段是否引用了 /cc-*
rg -n 'routed_to:\s*/cc-' .claude/commands/thinking.md
# 预期输出：无（空）
```

### 2) 检查是否有 secret 泄露（NO-FP + Allowlist）

**豁免机制**：行内 `# pragma: allowlist-secret why=<reason>` 可豁免该行。

```bash
# 排除本文件避免自命中
EXCLUDE="--glob=!.claude/rules/65-thinking-envelope.md"

# 豁免过滤器：排除含 allowlist 标记的行
ALLOWLIST_FILTER='| rg -v "pragma:\s*allowlist-secret"'

# 2.1 API KEY：只抓"赋值形态"，值不是 ${VAR} 占位符也不是 <SET|UNSET> 模板
rg -n $EXCLUDE -P '(TAVILY|BRAVE|DASHSCOPE).*(_API_KEY|_MCP_URL)\s*[:=]\s*(?!\$\{)(?!<)[^\s"'\''<]+' .claude/ \
  | rg -v 'pragma:\s*allowlist-secret'
# 预期输出：无（空）

# 2.2 常见 token 外观（只在赋值上下文抓 tvly-xxx, sk-xxx）
rg -n $EXCLUDE -P '[:=]\s*[^$\s"<]*(tvly-|sk-)[A-Za-z0-9_-]{10,}' .claude/ \
  | rg -v 'pragma:\s*allowlist-secret'
# 预期输出：无（空）

# 2.3 URL query 携带疑似 secret 参数
rg -n $EXCLUDE -P 'https?://[^\s"]+[?&](api_key|apikey|token|tavilyApiKey)=[^&\s"]+' .claude/ \
  | rg -v 'pragma:\s*allowlist-secret'
# 预期输出：无（空）

# 2.4 env_check 字段不应包含真实 URL
rg -n $EXCLUDE 'env_check:.*https?://' .claude/ \
  | rg -v 'pragma:\s*allowlist-secret'
# 预期输出：无（空）

# 2.5 解密项目专用：AES key / 密文测试向量（允许 analyzetools/ 和 workspace/）
rg -n -P '[0-9a-fA-F]{32,}' .claude/ \
  | rg -v 'pragma:\s*allowlist-secret' \
  | rg -v '^(analyzetools|workspace|analyzedata)/'
# 预期输出：无（空）
# 说明：解密项目的测试向量/密文在 analyzetools/workspace/analyzedata 目录下是预期的
```

#### Allowlist 格式规范

```yaml
# 行内豁免（必须在同一行，且带理由）
key = "0x12345678"  # pragma: allowlist-secret why=TEST_VECTOR
url = "https://example.com?token=abc123"  # pragma: allowlist-secret why=DOCS_EXAMPLE ticket=PROJ-123

# 合法理由 (why=)：
# - TEST_VECTOR: 解密测试向量
# - DOCS_EXAMPLE: 文档示例
# - FIXTURE: 测试固定数据
# - ENCRYPTED: 已加密的密文（非明文 key）

# 可选字段：
# - ticket=XXX: 关联工单
# - expires=YYYY-MM-DD: 过期时间（审计用）
```

#### 路径级豁免（解密项目专用）

以下目录允许出现密文/测试向量，但仍禁止明文 API key：

| 目录 | 允许 | 禁止 |
|------|------|------|
| `analyzetools/` | 密文、AES key 测试向量 | 明文 API key (TAVILY/BRAVE 等) |
| `analyzedata/` | 加密样本、dump | 明文 API key |
| `workspace/` | 解密输出、临时密文 | 明文 API key |
| `.claude/` | 无 | 所有敏感值 |

#### grep 兜底（没有 rg 时用）

```bash
# API KEY 赋值形态（兜底，排除本文件、模板值、豁免行）
grep -rEn --exclude="65-thinking-envelope.md" \
  '(TAVILY|BRAVE|DASHSCOPE).*(API_KEY|MCP_URL)[[:space:]]*[:=][[:space:]]*[^$[:space:]"<]+' .claude/ \
  | grep -vE ':\s*<(SET|UNSET)' \
  | grep -v 'pragma:.*allowlist-secret'
# 预期输出：无（空）
```

### 3) 检查工件目录与头部合规性

```powershell
# 确认 state 目录结构
Test-Path "d:\dw11\.claude\state\thinking"
# 创建目录（如不存在）
New-Item -ItemType Directory -Path "d:\dw11\.claude\state\thinking" -Force

# 检查 *.latest.yaml 第一行必须是 envelope:
Get-ChildItem "d:\dw11\.claude\state\thinking" -Filter "*.latest.yaml" -ErrorAction SilentlyContinue |
  ForEach-Object {
    $first = (Get-Content $_.FullName -TotalCount 1)
    if ($first -ne "envelope:") { Write-Host "[BAD] $($_.Name) first-line=$first" }
  }
# 预期：无 [BAD]
```

### 设计说明

- **Fail-closed by default**: 命中即失败，除非有显式豁免
- **结构化豁免**: 行内 `pragma: allowlist-secret why=<reason>` 可审计
- **路径隔离**: 解密项目的密文/测试向量在专用目录下不触发告警
- **上下文匹配**: 只匹配"赋值形态"，避免命中文档示例
- **对应风险**: CWE-532（日志/文档泄露敏感信息）

### 审计豁免清单

定期运行以下命令审计所有已豁免的行：

```bash
# 列出所有使用 allowlist 的行（审计用）
rg -n 'pragma:\s*allowlist-secret' d:/dw11/
# 检查是否有过期的豁免
rg -n 'pragma:\s*allowlist-secret.*expires=' d:/dw11/ | while read line; do
  # 提取 expires 日期并与今天比较
  echo "$line"
done
```

---

*优先级: HIGH - 所有 thinking 命令必须遵守*
