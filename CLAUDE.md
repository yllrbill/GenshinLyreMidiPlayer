# Claude Code Operating Contract (Piano Project)

## Priority Rules (优先读取)

> **骨架文档**: 新会话应优先读取以下规则文件

| 优先级 | 文件 | 用途 |
|--------|------|------|
| 1 | `.claude/rules/00-operating-model.md` | 核心工作模型 |
| 2 | `analydocs/HANDOFF.md` | 会话交接 |
| 3 | `piano制作指南.md` | Piano 项目指南 |

## Prime Directive
1) 可复跑：关键结论必须附"输入路径 + 命令 + 输出路径"
2) 最小改动：只做完成目标所需的最小修改，避免大重构
3) 证据闭环：重要输入/产物记录哈希与版本信息
4) 少问人：除非被权限/缺输入阻塞，否则优先从仓库恢复上下文

## Start Here (每次新会话第一步)
- **首选**: 运行 `/ai-resume` 恢复上下文并获取下一步计划
- 运行 /bootstrap
- 需要定位 bug：/triage
- 需要构造最小复现：/repro
- 需要验收与证据：/verify
- 会话结束前必须：/handoff

## Repo Conventions
- 文档入口：analydocs/HANDOFF.md
- EOP 转换工具：analyzetools/eop/
- Piano 播放器：LyreAutoPlayer/
- MIDI 相关：LyreAutoPlayer/.venv/Lib/site-packages/mido/

---

## Project Overview

**Piano MIDI 项目** - 包含 EOP 转 MIDI 工具和 LyreAutoPlayer 自动演奏器。

### 主要功能

1. **EOP 格式解析与转换** - 将 EveryonePiano (.eop) 文件转换为标准 MIDI
2. **LyreAutoPlayer** - 游戏自动演奏工具 (Python/PyQt6)
3. **GenshinLyreMidiPlayer** - C# WPF MIDI 播放器

### EOP 转 MIDI

```powershell
# 使用 EOP 转换工具
python -X utf8 analyzetools/eop/eop_to_midi_final.py <input.eop> <output.mid>
```

### LyreAutoPlayer

```powershell
cd LyreAutoPlayer
.venv\Scripts\activate
python main.py
```

## Key Technical Facts

| Item | Value |
|------|-------|
| EOP Skill | `.claude/skills/eop-midi-core/SKILL.md` |
| LyreAutoPlayer 依赖 | PyQt6, mido, keyboard |
| MIDI 库 | mido (Python) |
| GUI 框架 | PyQt6 (Python) / WPF (C#) |

## Common Commands

```powershell
# EOP 分析
python -X utf8 analyzetools/eop/eop_analyzer.py <file.eop>

# MIDI 测试
python -X utf8 -c "import mido; print(mido.get_output_names())"

# LyreAutoPlayer 环境
cd LyreAutoPlayer && .venv\Scripts\activate
```

---

## 已复制的骨架文档

### Rules (通用规则)
- `00-operating-model.md` - 核心工作模型
- `10-triage-discipline.md` - Triage 规则
- `50-failure-latch.md` - 失败锁存机制
- `65-thinking-envelope.md` - Envelope 规范
- `70-mcp-cus.md` - MCP 搜索规则
- `90-handoff-format.md` - 交接文档格式
- `90-windows-shell-discipline.md` - Windows Shell 规范
- `95-command-skill-naming.md` - 命名规范
- `reflectloop-envelope.md` - Reflectloop 规范

### Commands (用户命令)
- `/bootstrap` - 启动/恢复/盘点
- `/triage` - 错误定位
- `/repro` - 生成最小复现
- `/verify` - 验收与证据
- `/handoff` - 会话交接
- `/voteplan` - 多源搜索投票
- `/thinking` - 智能路由
- `/modelrouter` - 模型路由
- `/reflectloop` - 沙箱执行闭环
- `/mcp-cus` - MCP 配置状态
- `/downloader` - 批量下载

### Skills (Claude 技能)
- `voteplan-core` - 多源搜索+评分投票
- `reflectloop-core` - 沙箱执行闭环
- `thinking-router` - 智能路由
- `websearch` - 聚合搜索
- `modelrouter-core` - 模型路由
- `downloader-core` - 批量下载
- `eop-midi-core` - **EOP 转 MIDI 专用**

### Agents (专才分工)
- `re-recon.md` - 只读侦察/结构扫描
- `debugger.md` - 复现-定位-修复
- `auditor.md` - 证据链/门禁审计
