# Handoff - 20260103-midi-editor-pipeline

## Status: IN_PROGRESS (Phase 1.5 DONE)

## Summary
MIDI 编辑管线任务。Phase 1 + Phase 1.5 已完成。

## Goals
实现钢琴卷帘编辑器，支持：
- 可视化 MIDI 音符
- 预览播放
- 基础编辑 (选择/移动/删除/复制粘贴)
- 高级编辑 (添加/批量操作)
- 超音域处理预览
- **[新增]** 打开 MIDI 直接进入编辑器
- **[新增]** 保存/另存为 + 索引管理
- **[新增]** 已编辑版本选择弹窗

## Plan Overview

| Phase | 目标 | 估计行数 | 状态 |
|-------|------|----------|------|
| Phase 1 | 钢琴卷帘可视化 + 播放 | ~500 行 | ✅ DONE |
| Phase 1.5 | main.py 集成 + 版本选择 | ~100 行 | ✅ DONE |
| Phase 2 | 基础编辑 | ~300 行 | PENDING |
| Phase 3 | 高级编辑 | ~400 行 | PENDING |
| Phase 4 | 超音域预览 | ~200 行 | PENDING |

## Files Created (Phase 1)

| File | Lines | Description |
|------|-------|-------------|
| ui/editor/__init__.py | 15 | 模块导出 |
| ui/editor/note_item.py | 75 | NoteItem (QGraphicsRectItem) |
| ui/editor/piano_roll.py | 175 | PianoRollWidget (QGraphicsView) |
| ui/editor/timeline.py | 105 | TimelineWidget |
| ui/editor/keyboard.py | 95 | KeyboardWidget |
| ui/editor/editor_window.py | 280 | EditorWindow (含保存/索引) |
| **Total** | **~745** | |

## Verified Facts
- 语法检查: `py_compile ui/editor/*.py` ✅
- 导入检查: `from ui.editor import EditorWindow` ✅
- EditorWindow 已包含:
  - load_midi() 加载并显示
  - 保存/另存为 (Ctrl+S / Ctrl+Shift+S)
  - 索引写入 `midi/edited/index.json`
  - get_edited_versions() 类方法
  - edit_style ComboBox (5 种风格)

## Audit Fixes Applied (2026-01-03)

### Round 1

| 严重度 | 问题 | 修复 |
|--------|------|------|
| HIGH | 坐标系统 `127-note` 与 NOTE_RANGE 不匹配 | 改为 `note_max - note` |
| HIGH | setRenderHint 枚举用法错误 | 改为 `QPainter.RenderHint.Antialiasing` |
| MED | MIDI tempo 解析不支持变速 | 添加 tempo_map 累计时间计算 |
| MED | 重叠音符 note_on 覆盖丢失 | 改用 `(note, channel) -> list` FIFO |
| LOW | NoteItem.selected 与 QGraphicsItem 不同步 | 添加 `itemChange()` 方法 |
| LOW | EDITS_DIR 依赖 CWD | 改为 `Path(__file__).parent.parent.parent` |
| LOW | edit_style 无 UI | 添加 ComboBox 到工具栏 |

### Round 2

| 严重度 | 问题 | 修复 |
|--------|------|------|
| HIGH | KeyboardWidget 仍用 127 基准 | 改为 `note_max` (keyboard.py) |
| MED | Ctrl+滚轮缩放不同步时间轴/滑条 | 添加 `sig_zoom_changed` 信号 |
| LOW | 版本选择流程未接入 | 添加 `_open_with_version_check()` |

## Dependencies
- mido (已安装)
- PyQt6 (已安装)

## Reference
- openmusic.ai 钢琴卷帘编辑器
- LMMS / FL Studio Piano Roll

## Phase 1.5 Implementation (2026-01-03)

### Files Modified

| File | Changes |
|------|---------|
| ui/__init__.py | 添加 EditorWindow 导出 |
| ui/editor/editor_window.py | 保存目录改为 `midi-change`，版本列表按 last_modified 逆序 |
| main.py | 重构加载流程：先选版本再统一加载 |
| i18n/translations.py | 添加 original_file, select_version, select_version_prompt |

### Implementation Details

1. **保存目录变更**:
   - 原: `LyreAutoPlayer/midi/edited/`
   - 新: `LyreAutoPlayer/midi-change/`
   - 索引文件: `midi-change/index.json`

2. **版本选择优化**:
   - 版本列表按 `last_modified` 逆序排列（最新在前）
   - 默认选中最新版本（第一项）
   - 原始文件放在列表最后一项
   - 取消选择时自动加载最新保存版本

3. **统一加载流程**:
   - `on_load()`: 选择文件 → `_select_version()` → 返回 `selected_path`
   - 用 `selected_path` 执行 `midi_to_events_with_duration()`
   - 设置 `self.mid_path = selected_path`，更新 UI 和日志
   - 编辑器 `load_midi(selected_path)` 使用同一路径

4. **新方法 `_select_version(original_path) -> str`**:
   - 无历史版本 → 返回原始路径
   - 有历史版本 → 弹窗选择
   - 用户取消 → 返回最新保存版本

### Verified Facts
- 语法检查: `py_compile main.py ui/editor/editor_window.py` ✅
- 导入检查: `from ui import EditorWindow` ✅
- 保存目录: `D:\dw11\piano\LyreAutoPlayer\midi-change` ✅
- 版本排序: `get_edited_versions()` 返回按 last_modified 逆序 ✅
- 编辑器 i18n: `_open_with_version_check()` 使用 tr() 函数 ✅

## Next Steps (Phase 2)
1. 实现音符选择 (点击/框选)
2. 实现音符移动 (拖拽)
3. 实现音符删除 (Delete 键)
4. 实现复制粘贴 (Ctrl+C/V)

## Evidence Index
| File | Path | Summary |
|------|------|---------|
| context_pack.md | evidence/ | Planner 最小阅读摘要 |
| execute.log | evidence/ | 执行日志 + 语法检查 |
| diff.patch | evidence/ | git diff (ops/ai 骨架) |

---
*Created: 2026-01-03*
*Updated: 2026-01-03 (Phase 1.5 completed, evidence generated)*
