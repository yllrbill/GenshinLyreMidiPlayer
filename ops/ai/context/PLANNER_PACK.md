# Planner Pack

> Planner 首次阅读本文件，快速了解项目全貌

## 1. Project Summary

Piano MIDI 项目 - 包含 EOP 转 MIDI 工具和 LyreAutoPlayer 自动演奏器。

主要功能：
- EOP 格式解析与转换 - 将 EveryonePiano (.eop) 文件转换为标准 MIDI
- LyreAutoPlayer - 游戏自动演奏工具 (Python/PyQt6)
- GenshinLyreMidiPlayer - C# WPF MIDI 播放器

## 2. Key Paths (按重要性排序)

1. `CLAUDE.md` - 项目配置入口
2. `ops/ai/state/STATE.md` - 当前状态
3. `ops/ai/context/REPO_MAP.md` - 仓库地图
4. `ops/ai/state/TASKS_INDEX.md` - 任务索引
5. `LyreAutoPlayer/main.py` - Python 播放器入口
6. `GenshinLyreMidiPlayer/` - C# WPF 播放器

## 3. Common Commands

| 操作 | 命令 |
|------|------|
| EOP 转换 | `python -X utf8 analyzetools/eop/eop_to_midi_final.py <input.eop> <output.mid>` |
| LyreAutoPlayer | `cd LyreAutoPlayer && .venv\Scripts\activate && python main.py` |
| C# 构建 | `dotnet build GenshinLyreMidiPlayer.sln` |

## 4. Current Focus

(从 STATE.md 读取 - 待更新)

## 5. Risk Areas / Constraints

- 敏感数据在 `private/` 目录
- EOP 格式为逆向工程结果，可能不完整
- Windows 平台依赖（keyboard 库需要 Win32）

## 6. Active Tasks

(从 TASKS_INDEX.md 读取 - 暂无)

## 7. Dual-Agent Workflow

本项目使用双代理工作流：
- **ChatGPT (Planner)**: 决策层，生成 plan.md
- **Claude Code (Executor)**: 执行层，执行 plan 并生成证据

关键命令：
- `/ai-resume` - 恢复上下文
- `/ai-intake` - 建案
- `/ai-catalog` - 更新索引
- `/ai-end` - 收尾交接

---
*Last Updated: 2026-01-01*
