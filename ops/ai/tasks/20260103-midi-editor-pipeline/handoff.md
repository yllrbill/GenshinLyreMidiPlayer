# Handoff - 20260103-midi-editor-pipeline

## Status: DONE (Phase 1 + 1.5 + 2 + Timeline优化)

## Summary
MIDI 编辑管线任务。Phase 1 + Phase 1.5 + Phase 2 已完成。

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
| Phase 2 | 基础编辑 | ~300 行 | ✅ DONE |
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

## Phase 1.5 补充修复 (2026-01-03)

### P1.5-FIX-1: EditorWindow FluidSynth 播放

**问题**: 编辑器播放按钮只驱动 timer/playhead，无声音输出

**修复**:
- 添加 `fluidsynth` 可选导入 (`HAS_FLUIDSYNTH` 标志)
- 新增字段: `_fs`, `_sfid`, `_chan`, `_active_notes`
- 新增方法:
  - `_init_sound()`: 懒加载 FluidSynth，尝试多种音频驱动
  - `_release_all_notes()`: 释放所有正在发声的音符
  - `closeEvent()`: 窗口关闭时清理资源
- 修改 `on_play_pause()`: 播放时初始化 FluidSynth
- 修改 `on_stop()`: 停止时释放音符
- 修改 `_update_playback()`: 遍历 `piano_roll.notes`，触发 note on/off

**SoundFont 搜索路径**:
1. `LyreAutoPlayer/assets/FluidR3_GM.sf2`
2. `LyreAutoPlayer/FluidR3_GM.sf2`
3. `C:/soundfonts/FluidR3_GM.sf2`

### P1.5-FIX-2: KeyboardWidget 八度音域段显示

**问题**: 左侧键盘无法直观显示可用音域范围和选中八度

**修复**:
- 新增常量:
  - `OCTAVE_LABEL_WIDTH = 20`: 八度标签列宽度
  - `KEYBOARD_WIDTH = 60`: 键盘区域宽度
  - 范围颜色: `RANGE_AVAILABLE_COLOR` (绿), `RANGE_SELECTED_COLOR` (黄), `RANGE_UNAVAILABLE_COLOR` (灰)
- 新增字段: `available_range`, `selected_octave`
- 新增信号: `sig_octave_selected(int)`
- 新增方法:
  - `set_available_range(low, high)`: 设置可用音域
  - `set_selected_octave(octave)`: 设置选中八度
  - `_draw_octave_labels(painter)`: 绘制八度标签列
  - `mousePressEvent()`: 点击八度标签切换选中
- 修改 `paintEvent()`: 绘制八度音域段覆盖色
- 修改 EditorWindow 左上角占位符宽度: 60 → 80

### Verified Facts (补充修复)
- 语法检查: `py_compile ui/editor/editor_window.py ui/editor/keyboard.py` ✅
- FluidSynth 可选: 无 pyfluidsynth 时编辑器仍可正常使用 (静音模式)
- 键盘宽度: 20 (八度标签) + 60 (键盘) = 80px

## Phase 2 Implementation (2026-01-03)

### Files Modified

| File | Changes |
|------|---------|
| ui/editor/note_item.py | 添加 ItemIsMovable/ItemSendsGeometryChanges 标志、拖拽边界 clamp、缩放参数存储 |
| ui/editor/piano_roll.py | 添加 RubberBandDrag 框选、键盘事件处理、剪贴板、编辑方法 |

### Implementation Details

1. **音符选择**:
   - 单击: QGraphicsItem 内置选中 (ItemIsSelectable)
   - 框选: `setDragMode(RubberBandDrag)` 橡皮筋框选
   - Ctrl+A: `select_all()` 全选

2. **音符移动**:
   - 启用 `ItemIsMovable` 和 `ItemSendsGeometryChanges` 标志
   - `itemChange(ItemPositionChange)` 限制 X >= 0, Y 在 NOTE_RANGE 内
   - `mouseReleaseEvent()` 后调用 `_sync_notes_from_graphics()` 同步数据模型

3. **删除**:
   - Delete/Backspace: `delete_selected()` 从 scene 和 notes 列表移除
   - 自动更新 `total_duration`

4. **复制粘贴**:
   - Ctrl+C: `copy_selected()` 存储相对时间到 `_clipboard`
   - Ctrl+V: `paste_at_playhead()` 在播放头位置粘贴，自动扩展场景

5. **信号**:
   - 新增 `sig_notes_changed` 信号，编辑后发射

### Verified Facts (Phase 2)
- 语法检查: `py_compile ui/editor/*.py main.py` ✅
- NoteItem 拖拽边界: X >= 0, Y 在 (21, 108) 音域内 ✅
- RubberBandDrag: 框选模式正确启用 ✅
- 键盘事件: Ctrl+A/Delete/Ctrl+C/Ctrl+V/Escape 均已实现 ✅

### Phase 2 补充修复 (2026-01-03)

| 问题 | 修复 |
|------|------|
| RubberBandDrag 固定导致拖拽平移回归 | 添加 Space/中键临时切换 ScrollHandDrag |
| 快捷键依赖焦点 | load_midi() 完成后调用 `piano_roll.setFocus()` |

**实现细节**:
- `keyPressEvent`: Space 按下切换到 ScrollHandDrag
- `keyReleaseEvent`: Space 释放恢复 RubberBandDrag
- `mousePressEvent`: 中键模拟左键启动 ScrollHandDrag
- `mouseReleaseEvent`: 中键释放恢复 RubberBandDrag
- `load_midi()`: 最后调用 `self.piano_roll.setFocus()`

**语法检查**: `python -m py_compile LyreAutoPlayer/ui/editor/*.py LyreAutoPlayer/main.py` ✅

### Phase 2 审计修复 #2 (2026-01-03)

| 严重度 | 问题 | 修复 |
|--------|------|------|
| MED | 中键拖拽释放时仍用中键事件，未发送对应的假左键释放 | mouseReleaseEvent 中添加假左键释放事件 |

**问题详情**:
- 中键按下时创建"假左键按下"事件启动 ScrollHandDrag
- 但中键释放时直接传入中键事件，可能导致拖拽状态未正确结束（"卡住拖拽"）

**修复实现** (piano_roll.py:332-347):
```python
if event.button() == Qt.MouseButton.MiddleButton:
    # 模拟左键释放以正确结束拖拽状态
    fake_event = QMouseEvent(
        event.type(),
        event.position(),
        event.globalPosition(),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,  # 释放后无按钮处于按下状态
        event.modifiers()
    )
    super().mouseReleaseEvent(fake_event)
    self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
    return
```

**语法检查日志**:
```
$ cd d:/dw11/piano/LyreAutoPlayer && python -m py_compile ui/editor/piano_roll.py
Exit code: 0
(无错误输出)
```

### Phase 2 审计修复 #3 (2026-01-03)

| 严重度 | 问题 | 修复 |
|--------|------|------|
| HIGH | `_redraw_all()` 调用 `scene.clear()` 导致 NoteItem 被销毁后复用崩溃 | 改用 `_clear_grid()` 只清理网格图元 |

**问题详情**:
- `scene.clear()` 会删除场景中所有 QGraphicsItem
- 但 `self.notes` 列表仍持有已删除的 NoteItem 引用
- 后续对这些对象调用方法会导致未定义行为或崩溃

**修复实现**:
1. 新增 `_grid_items: List` 字段追踪网格图元
2. 新增 `_clear_grid()` 方法只删除网格图元
3. 修改 `_draw_grid()` 将图元添加到 `_grid_items`
4. 修改 `_redraw_all()` 不用 `scene.clear()`，改为:
   - `_clear_grid()` 清理网格
   - `scene.removeItem(playhead)` 清理播放头
   - 保留 NoteItem 在场景中，只更新几何属性
5. 网格图元设置 `setAcceptedMouseButtons(Qt.MouseButton.NoButton)` 避免干扰音符选择
6. `load_midi()` 中 `scene.clear()` 后清空 `_grid_items` 列表

**语法检查日志**:
```
$ cd d:/dw11/piano/LyreAutoPlayer && python -m py_compile ui/editor/piano_roll.py
Exit code: 0
[OK] piano_roll.py syntax check passed
```

### Phase 2 审计修复 #4 (2026-01-03)

| 严重度 | 问题 | 修复 |
|--------|------|------|
| HIGH | savecustom 旧索引条目 source_path 未规范化，导致匹配失败 | 添加反向匹配 + 自动迁移逻辑 |
| LOW | 工具栏 "Y:" 标签不够明确 | 改为 "Zoom Y:" |

**问题详情**:
- 旧的 `index.json` 条目中 `source_path` 可能使用不同大小写/斜杠格式
- 新添加的 `os.path.normcase()` 不能修复已有的旧条目
- 导致 `get_edited_versions(original_path)` 返回空列表

**修复实现** (editor_window.py):
1. 在 `get_edited_versions()` 中，如果正向匹配为空：
   - 尝试通过 `saved_path` 文件名反向匹配
   - `saved_path` 格式为 `{source_stem}_{style}.mid`
   - 检查 `saved_stem.startswith(source_stem + "_")`
2. 找到匹配后自动迁移：
   - 更新 `e["source_path"]` 为规范化路径
   - 写回 `index.json`
3. 工具栏标签从 "Y:" 改为 "Zoom Y:"

**语法检查日志**:
```
$ cd d:/dw11/piano/LyreAutoPlayer && python -m py_compile ui/editor/editor_window.py ui/editor/piano_roll.py
Exit code: 0
[OK] Syntax check passed
```

### Phase 2 审计修复 #5 - 保存重建 + 网格增强 (2026-01-03)

| 严重度 | 问题 | 修复 |
|--------|------|------|
| HIGH | `_save_midi()` 直接保存 `self.midi_file`，编辑无效 | 新增 `_rebuild_midi_from_notes()` 从 `piano_roll.notes` 重建 MIDI |
| MED | E-F 和 B-C 边界不明显 | 增强网格颜色 + 加粗边界线 |

**修复 1: MIDI 重建** (editor_window.py):
- 新增 `_rebuild_midi_from_notes()` 方法
- 创建单轨 MIDI，保留原始 `ticks_per_beat`
- 考虑 NoteItem 的 `pos()` 偏移（拖拽后的位置变化）
- 计算最终 pitch = note + offset_note, start = start_time + offset_time
- 生成 note_on/note_off 事件，按时间排序，note_off 优先
- 转换为 delta time，添加 end_of_track

**修复 2: 网格增强** (piano_roll.py):
- 新增颜色常量:
  - `GRID_COLOR_E`: 略带红 (E-F 边界下)
  - `GRID_COLOR_B`: 略带绿 (B-C 边界下)
- 增强边界线颜色:
  - `GRID_LINE_C`: `QColor(100, 130, 100)` 绿色加粗
  - `GRID_LINE_EF`: `QColor(130, 90, 90)` 红色加粗
- 边界线宽度从 1.0/1.5 增加到 2.0
- E/B 音行使用特殊背景色突出边界

**语法检查**:
```
$ cd d:/dw11/piano/LyreAutoPlayer && python -m py_compile ui/editor/editor_window.py ui/editor/piano_roll.py
Exit code: 0
Syntax check passed
```

### Phase 2 审计修复 #6 - 保存同步 + 复制粘贴通道 + 网格简化 (2026-01-03)

| 严重度 | 问题 | 修复 |
|--------|------|------|
| HIGH | 拖拽后保存时位置未同步，音符回到原位 | `_save_midi()` 开头调用 `_sync_notes_from_graphics()` |
| MED | 复制粘贴丢失 channel 属性 | `copy_selected()` 保存 channel，`paste_at_playhead()` 传递 channel |
| LOW | 网格颜色过于复杂，E/B/C 边界辨识度低 | 简化为 gray/black/green 三色方案 |

**修复 1: 保存同步** (editor_window.py):
- 在 `_save_midi()` 方法开头添加 `self.piano_roll._sync_notes_from_graphics()` 调用
- 确保拖拽后的 start_time/note 已写回数据模型
- 修复"拖拽后保存，重新打开音符回到原位"问题

**修复 2: 复制粘贴通道** (piano_roll.py):
- `copy_selected()` 中添加 `"channel": getattr(item, 'channel', 0)` 到剪贴板
- `paste_at_playhead()` 中添加 `channel=nd.get("channel", 0)` 传递给 NoteItem
- 保留原始 MIDI 通道信息

**修复 3: 网格简化** (piano_roll.py):
- 移除复杂的 E/B 边界色，简化为三色:
  - `GRID_COLOR_GRAY = QColor(70, 70, 70)` - 灰色行 (更明显)
  - `GRID_COLOR_BLACK = QColor(32, 32, 32)` - 黑色行 (更暗)
  - `GRID_COLOR_C = QColor(80, 140, 80)` - C 音行绿色 (八度起点)
- 灰色行: D, E, G, A, B (note_in_octave in [2, 4, 6, 8, 10])
- 黑色行: C#, D#, F, F#, G#, A# (其余)
- C 音行: 八度起点，绿色突出

**语法检查**:
```
$ cd d:/dw11/piano/LyreAutoPlayer && python -m py_compile ui/editor/editor_window.py ui/editor/piano_roll.py
Exit code: 0
Syntax check passed
```

## Phase 1.5 Timeline 优化修复 (2026-01-03)

| 问题 | 修复 |
|------|------|
| `_generate_beat_ticks()` 从 tick 0 迭代性能差 | 直接跳到可视 tick 范围，不从 0 遍历 |
| "音符" 标签在选中/超域状态也显示 | 仅蓝色普通状态绘制 (selected/out_of_range 时跳过) |
| 网格右侧滚动后出现空白 | scene 宽度 = max(content, scroll_offset + viewport) |
| 窗口大小变化网格不更新 | 添加 `resizeEvent()` 触发 `_redraw_all()` |

**关键方法**:
- `timeline.py: _second_to_tick()` - 秒转 tick (逆向查 tempo_map)
- `timeline.py: _generate_beat_ticks()` - 只生成可视范围内的拍子
- `note_item.py: paint()` - 条件绘制 "音符" 标签
- `piano_roll.py: _calc_scene_width()` - 滚动偏移 + 视口宽度
- `piano_roll.py: resizeEvent()` - 窗口大小变化时重绘

**语法检查**:
```
$ python -m py_compile LyreAutoPlayer/ui/editor/*.py
Exit code: 0
[OK] Syntax check passed
```

## Next Steps (Phase 3)
1. 实现音符添加 (双击创建)
2. 实现批量操作 (移调、量化)
3. 实现撤销/重做

## Evidence Index
| File | Path | Summary |
|------|------|---------|
| context_pack.md | evidence/ | Planner 最小阅读摘要 |
| execute.log | evidence/ | 执行日志 + 语法检查 |
| diff.patch | evidence/ | git diff (ops/ai 骨架) |

---
*Created: 2026-01-03*
*Updated: 2026-01-03 (Phase 1.5 Timeline 优化修复 completed)*
