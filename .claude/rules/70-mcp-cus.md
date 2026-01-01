# MCP Search Rules

## 可用搜索工具优先级

按以下顺序尝试 MCP 搜索工具，失败则 fallback：

| 优先级 | 工具 | MCP Server | 说明 |
|--------|------|------------|------|
| 1 | `brave_web_search` | brave | Brave Search API (快速、高质量英文源) |
| 2 | `tavily_search` | tavily-remote | Tavily Remote MCP (HTTP) |
| 3 | `qwen_web_search` | qwen_fallback | Qwen + DashScope (中文源好、有摘要) |
| 4 | `freebird_search` | freebird | DuckDuckGo (免费兜底) |
| 5 | `WebSearch` | (内置) | Claude 内置搜索 |

## 调用规则

### 1. 优先使用 MCP 工具
```
尝试顺序: brave → tavily-remote → qwen_fallback → freebird → WebSearch
```

### 2. 失败处理
- 单个工具失败：尝试下一个
- 全部失败：记录 `SEARCH_FAILED` 状态，不猜测

### 3. 结果记录
每次搜索必须记录：
```yaml
search_log:
  query: <搜索词>
  tool_used: <brave|tavily-remote|freebird|qwen|websearch>
  results_count: <N>
  top_sources:
    - url: <URL>
      credibility: <OFFICIAL|MAINTAINER|COMMUNITY|BLOG>
```

## MCP 配置位置

文件: `D:\dw11\.mcp.json`

```json
{
  "mcpServers": {
    "brave": { 
      "command": "cmd", 
      "args": ["/c", "npx", "-y", "brave-search-mcp"], 
      "env": { "BRAVE_API_KEY": "${BRAVE_API_KEY}" } 
    },
    "tavily-remote": { 
      "type": "http", 
      "url": "${TAVILY_MCP_URL}" 
    },
    "qwen_fallback": { 
      "command": "node", 
      "args": ["D:/ai/mcp-server/qwen-websearch-mcp/index.js"], 
      "env": { 
        "DASHSCOPE_API_KEY": "${DASHSCOPE_API_KEY}",
        "DASHSCOPE_BASE_URL": "${DASHSCOPE_BASE_URL:-https://dashscope-intl.aliyuncs.com/compatible-mode/v1}"
      } 
    },
    "freebird": { 
      "command": "npx", 
      "args": ["-y", "@dannyboy2042/freebird-mcp"] 
    }
  }
}
```

## 环境变量

| 变量 | 用途 |
|------|------|
| `BRAVE_API_KEY` | Brave Search API 密钥 |
| `TAVILY_MCP_URL` | Tavily Remote MCP URL (含 API key) |
| `DASHSCOPE_API_KEY` | DashScope API 密钥 (qwen_fallback) |
| `DASHSCOPE_BASE_URL` | DashScope 基础 URL (可选，默认国际版) |

## 禁止行为

- ❌ 在代码/日志中硬编码 API 密钥
- ❌ 搜索失败时猜测结果
- ❌ 不记录搜索来源就引用

## 难度自适应规则

> **唯一事实源**: `.claude/skills/websearch/SKILL.md` Section D

搜索参数按 topic 复杂度自动调整：

| 难度 | Queries | Results/Query | 并发 | 触发条件 |
|------|---------|---------------|------|----------|
| EASY | 3 | 5 | 1 | 单一明确问题 |
| MEDIUM | 4-5 | 7 | 2 | 2-3 个约束或需对比 |
| HARD | 6 | 10 | 3 | 含关键词/高复杂度 |

**HARD 触发关键词**: 最新/latest/对比/compare/方案/solution/根因/root cause
