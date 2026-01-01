---
description: 扫描仓库生成完整项目摘要，用于定点分析与代码定位
argument-hint: "[--force] 例: /ai-project-sum 或 /ai-project-sum --force"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

你在 Claude Code 执行层工作。目标：**扫描当前仓库，生成结构化项目摘要**，为后续分析与定位提供索引。

## 模式

| 参数 | 说明 |
|------|------|
| (默认) | 生成 PROJECT_SUMMARY.md，若已存在则询问是否覆盖 |
| `--force` | 强制覆盖现有 PROJECT_SUMMARY.md |

## 硬规则

- **Offline-first**：不使用网络搜索
- **Read-only scan**：只读扫描，不修改项目源代码
- **Summary-only**：不输出超大文件全文，只给摘要与路径
- **Deterministic**：所有列表按字母/路径排序
- **Tool preference**：优先使用 `rg --files`、`rg` 搜索，避免 `find`

## 输出位置

```
ops/ai/context/PROJECT_SUMMARY.md
```

若 `ops/ai/context/` 目录不存在，先创建。

---

## 执行流程

### Step 1: 检测项目根目录与基础信息

```
1. 确认当前工作目录（项目根）
2. 检测 Git 信息（若存在）：
   - 分支名
   - 最近 5 条 commit（单行）
3. 统计文件数量（排除 .git, node_modules, .venv, __pycache__ 等）
```

### Step 2: 识别语言/框架特征

扫描文件扩展名和特征文件，判断主要技术栈：

| 特征文件 | 语言/框架 |
|----------|-----------|
| `*.py`, `pyproject.toml`, `requirements.txt`, `setup.py` | Python |
| `*.ts`, `*.tsx`, `package.json` | TypeScript/Node.js |
| `*.js`, `package.json` | JavaScript/Node.js |
| `*.cs`, `*.csproj`, `*.sln` | C# / .NET |
| `*.go`, `go.mod` | Go |
| `*.rs`, `Cargo.toml` | Rust |
| `*.java`, `pom.xml`, `build.gradle` | Java |
| `Makefile`, `CMakeLists.txt` | C/C++ |
| `*.vue`, `vite.config.*` | Vue.js |
| `*.jsx`, `next.config.*` | React/Next.js |

### Step 3: 识别入口文件

按优先级搜索（取前 5 个）：

```bash
# Python
rg --files -g "main.py" -g "app.py" -g "cli.py" -g "__main__.py" -g "manage.py"

# JavaScript/TypeScript
rg --files -g "index.ts" -g "index.js" -g "main.ts" -g "main.js" -g "app.ts" -g "server.ts"

# C#
rg --files -g "Program.cs" -g "Startup.cs"

# 通用
rg --files -g "*main*" -g "*entry*" -g "*bootstrap*" | head -10
```

### Step 4: 扫描目录结构

```bash
# 列出顶层目录（深度 2）
rg --files | sed 's|/[^/]*$||' | sort -u | head -50

# 或使用 tree（如果可用）
tree -L 2 -d --noreport
```

输出格式：
```
项目根/
├── src/           # 源代码
├── tests/         # 测试
├── docs/          # 文档
├── config/        # 配置
└── scripts/       # 脚本
```

### Step 5: 识别核心模块

基于目录名和文件内容识别模块职责：

```bash
# 搜索 class 定义
rg "^class " --type py -l | head -20

# 搜索 export/module 定义
rg "^export " --type ts -l | head -20

# 搜索函数入口
rg "^def main|^async def main|if __name__" --type py -l
```

对每个核心模块提取：
- 路径
- 主要类/函数（前 5 个）
- 一句话职责描述

### Step 6: 依赖分析

```bash
# Python
cat requirements.txt pyproject.toml 2>/dev/null | rg "^\w|dependencies"

# Node.js
cat package.json 2>/dev/null | jq '.dependencies, .devDependencies'

# C#
rg "<PackageReference" *.csproj
```

提取关键依赖（前 15 个），标注用途。

### Step 7: 配置文件扫描

搜索配置文件：

```bash
rg --files -g "*.json" -g "*.yaml" -g "*.yml" -g "*.toml" -g "*.ini" -g "*.cfg" -g ".env*" | head -20
```

对每个配置文件提取：
- 路径
- 用途（从文件名/内容推断）

### Step 8: 构建/运行/测试命令

从以下来源提取：

1. `README.md` / `README` - 搜索 ```bash 代码块
2. `package.json` - scripts 字段
3. `Makefile` - target 列表
4. `pyproject.toml` - scripts 字段
5. `.github/workflows/` - CI 命令

输出格式：
```
| 操作 | 命令 | 来源 |
|------|------|------|
| 安装依赖 | pip install -r requirements.txt | README |
| 运行 | python main.py | README |
| 测试 | pytest | pyproject.toml |
```

### Step 9: 数据流概要（启发式）

搜索数据流关键词：

```bash
# 输入
rg "input|read|load|fetch|request|args" --type py -l | head -10

# 输出
rg "output|write|save|send|response|print" --type py -l | head -10

# 状态管理
rg "state|store|cache|session|context" --type py -l | head -10
```

生成简化数据流描述。

### Step 10: 扩展点/插件点

搜索扩展机制：

```bash
# 插件/扩展
rg "plugin|extension|hook|register|subscribe|emit" -l | head -10

# 抽象类/接口
rg "ABC|Protocol|Interface|abstract" --type py -l | head -10
```

### Step 11: 风险点识别

搜索潜在风险：

```bash
# 硬编码敏感信息
rg "password|secret|api_key|token" -l | head -10

# 危险操作
rg "eval|exec|subprocess|shell=True|os\.system" --type py -l | head -10

# TODO/FIXME/HACK
rg "TODO|FIXME|HACK|XXX" -l | head -10
```

---

## 输出模板 (PROJECT_SUMMARY.md)

```markdown
# Project Summary

> 自动生成于 YYYY-MM-DD HH:MM，供后续分析定位使用

## 1. 基础信息

| 项目 | 值 |
|------|-----|
| 项目根目录 | `<path>` |
| Git 分支 | `<branch>` |
| 主要语言 | Python / TypeScript / ... |
| 框架 | PyQt6 / FastAPI / ... |
| 文件总数 | N |
| 代码行数 | ~N (估算) |

## 2. 目录结构

```
<tree output>
```

## 3. 入口文件

| 入口 | 路径 | 说明 |
|------|------|------|
| 主入口 | `main.py` | GUI 应用入口 |
| ... | ... | ... |

## 4. 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| Player | `player/` | MIDI 播放与线程控制 |
| ... | ... | ... |

## 5. 关键依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| PyQt6 | - | GUI 框架 |
| mido | - | MIDI 解析 |
| ... | ... | ... |

## 6. 配置文件

| 文件 | 用途 |
|------|------|
| `settings.json` | 应用配置 |
| `requirements.txt` | Python 依赖 |
| ... | ... |

## 7. 构建/运行/测试

| 操作 | 命令 |
|------|------|
| 安装依赖 | `pip install -r requirements.txt` |
| 运行 | `python main.py` |
| 测试 | (无) |

## 8. 数据流概要

```
[输入] MIDI 文件 → [解析] mido → [处理] PlayerThread → [输出] pydirectinput 键盘模拟
                                                    ↘ [输出] FluidSynth 音频播放
```

## 9. 扩展点

| 扩展点 | 位置 | 说明 |
|--------|------|------|
| 输入样式 | `style_manager.py` | 可注册新键盘布局样式 |
| ... | ... | ... |

## 10. 风险点

| 类型 | 位置 | 说明 |
|------|------|------|
| TODO | `main.py:123` | 待实现功能 |
| ... | ... | ... |

---

*Generated by /ai-project-sum*
```

---

## 终端输出（简短）

执行完成后输出：

```
✅ 项目摘要已生成

输出路径: ops/ai/context/PROJECT_SUMMARY.md

摘要:
- 项目类型: Python GUI 应用 (PyQt6)
- 入口文件: main.py
- 核心模块: 5 个
- 依赖数量: 8 个
- 风险点: 3 处

下一步: 阅读 PROJECT_SUMMARY.md 进行定点分析
```

---

## 错误处理

| 错误 | 处理 |
|------|------|
| 目录不存在 | 自动创建 `ops/ai/context/` |
| 文件已存在 | 询问覆盖（除非 --force） |
| rg 不可用 | 降级到 Glob + Grep 工具 |
| 空项目 | 输出最小摘要，标注"空项目" |

---

## 与其他命令协同

- `/ai-intake` 建案时可引用 PROJECT_SUMMARY.md
- `/ai-resume` 恢复上下文时可读取 PROJECT_SUMMARY.md
- `repo-mapper` subagent 可复用部分扫描逻辑

---

*创建时间: 2026-01-02*
*版本: 1.0*
