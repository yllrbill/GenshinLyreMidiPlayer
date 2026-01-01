---
description: 显示 MCP 服务器配置状态
---

## MCP 服务器状态

读取并显示当前 MCP 配置。

### 操作

1. 读取 `.mcp.json` 配置文件
2. 检查各服务器配置
3. 显示环境变量状态（不显示实际值）

### 输出格式

```yaml
mcp_status:
  config_file: .mcp.json
  servers:
    - name: brave
      type: stdio
      status: <CONFIGURED|MISSING_ENV|ERROR>
      env_vars:
        - BRAVE_API_KEY: <SET|UNSET>
    - name: tavily-remote
      type: http
      status: <CONFIGURED|MISSING_ENV|ERROR>
      env_vars:
        - TAVILY_MCP_URL: <SET|UNSET>
    - name: freebird
      type: stdio
      status: <CONFIGURED|MISSING_ENV|ERROR>
      env_vars: (无需环境变量)
    - name: qwen_fallback
      type: stdio
      status: <CONFIGURED|MISSING_ENV|ERROR>
      env_vars:
        - DASHSCOPE_API_KEY: <SET|UNSET>
        - DASHSCOPE_BASE_URL: <SET|UNSET> (可选)
```

### 搜索工具优先级

```
brave → tavily-remote → freebird → qwen_fallback → WebSearch (内置)
```

### 环境变量检查命令（推荐）

**重要**: 在 Bash 中调用 PowerShell 检查环境变量时，必须使用单引号包裹 -Command 参数，避免 Bash 展开 `$env:` 或 `$_`。

```bash
# 正确写法：使用单引号 + [Environment]::GetEnvironmentVariable()
powershell -NoProfile -Command 'if ([Environment]::GetEnvironmentVariable("BRAVE_API_KEY")) { "SET" } else { "UNSET" }'
powershell -NoProfile -Command 'if ([Environment]::GetEnvironmentVariable("TAVILY_MCP_URL")) { "SET" } else { "UNSET" }'
powershell -NoProfile -Command 'if ([Environment]::GetEnvironmentVariable("DASHSCOPE_API_KEY")) { "SET" } else { "UNSET" }'
```

### 测试命令

测试各 MCP 搜索工具：
```
使用 brave_web_search 工具搜索 "test query"
使用 tavily_search 工具搜索 "test query"
使用 freebird_search 工具搜索 "test query"
使用 qwen_web_search 工具搜索 "test query"
```

### 服务器路径

| 服务器 | 路径/命令 |
|--------|-----------|
| brave | `npx -y brave-search-mcp` |
| tavily-remote | HTTP: `${TAVILY_MCP_URL}` |
| freebird | `npx -y @dannyboy2042/freebird-mcp` |
| qwen_fallback | `D:/ai/mcp-server/qwen-websearch-mcp/index.js` |

### 重新加载

MCP 配置更改后需要重启 Claude Code：
1. 退出当前会话
2. 重新启动 `claude`
3. 运行 `/mcp` 验证

### Hard Rules (脱敏)

1. **绝不输出真实 URL**: TAVILY_MCP_URL 等包含 `://` 的值只能显示 `SET|UNSET` 或 `${VAR}` 占位符
2. **绝不输出 API key**: 任何 `*_API_KEY` 环境变量只能显示 `SET|UNSET`
3. **日志/工件同样适用**: 写入 `.latest.yaml` 或屏幕输出时同样遵守脱敏规则
