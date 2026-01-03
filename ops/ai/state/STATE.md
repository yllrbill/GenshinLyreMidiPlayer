# Project State

## Latest Task
- TASK_ID: 20260103-midi-editor-pipeline
- Status: DONE (Phase 1 + 1.5 + 2 + Timeline优化)
- Pointer: ops/ai/tasks/20260103-midi-editor-pipeline

## Previous Task
- TASK_ID: 20260102-2138-main-mixin-refactor
- Status: DONE (包含 Input Diagnostics 实现)
- Pointer: ops/ai/tasks/20260102-2138-main-mixin-refactor

## Current Focus
- MIDI 编辑器 Phase 1 + 1.5 + 2 + Timeline优化 完成
- 本次优化: 拍子生成性能、音符标签条件显示、网格宽度覆盖、resizeEvent
- 待进行 Phase 3：高级编辑 (双击添加音符/批量移调/量化/撤销重做)

## Completed Summary (MIDI Editor Phase 1)
- **Phase 1 钢琴卷帘骨架完成**: 6 个新文件 (~745 行)
- ui/editor/note_item.py: NoteItem (QGraphicsRectItem)
- ui/editor/piano_roll.py: PianoRollWidget (QGraphicsView)
- ui/editor/timeline.py: TimelineWidget
- ui/editor/keyboard.py: KeyboardWidget
- ui/editor/editor_window.py: EditorWindow (含保存/索引)
- Syntax check: OK
- Import check: OK (`from ui.editor import EditorWindow`)

## 行数统计（当前）
- main.py: 1050 行 (原 2206 → 1556 → 1039 → 1050)
- ui/tab_builders.py: 575 行 (新增)
- i18n/translations.py: 173 行 (+5 新翻译键)
- ui/mixins/ 合计 910 行（7 files）
  - config_mixin.py: 337
  - settings_preset_mixin.py: 295
  - playback_mixin.py: 153
  - hotkeys_mixin.py: 68
  - language_mixin.py: 24
  - __init__.py: 18
  - logs_mixin.py: 15

## Known Issues / Technical Debt
1. ~~**Field Drift Risk**: save_settings vs _collect_current_settings 字段结构不同~~ ✅ 已解决
2. ~~LyreAutoPlayer 目录策略性未纳入 git 跟踪~~ ✅ 已纳入 git 跟踪
3. **Path Handling (P2 - Low Risk)**: 版本索引仍依赖 `midi-change/index.json`，但已实现多重回退策略：
   - 路径规范化匹配 (`os.path.normcase`)
   - 文件名 + edit_style + 元数据验证 (file_size + note_count)
   - 文件名前缀 + 有效风格兜底
   - 当 index.json 缺失或元数据变化过大时仍可能匹配失败
   - `_lookup_source_path()` 失败时，`load_midi()` 回退为按原始文件加载

## Pending Tasks
1. (DONE) 20260103-midi-editor-pipeline - MIDI 编辑管线 Phase 1+1.5+2+优化

## Recent Completions
- Input Diagnostics 窗口 + 修复审计 (追加到 20260102-2138)
  - ui/diagnostics_window.py (新增 ~240 行)
  - 支持按键记录、过滤、来源标注
  - 17 个新 i18n 翻译键
  - **2026-01-03 修复**: 线程安全 signal、语言同步、防御性 KeySource、_sync_diagnostics_state() 统一方法

## Evidence
- Regression: LyreAutoPlayer/.claude/state/regression/mixin_refactor_20260102.json (14/14)
- Handoff: ops/ai/tasks/20260102-2142-unify-config-schema-and-persistence/handoff.md

## How to Resume in a New Session
1. Read `ops/ai/state/STATE.md`
2. Read latest task's `request.md` and `handoff.md`
3. Review evidence files if needed
4. Continue from task status

## Search Constraints
- 检索任务文档时仅扫描 `ops/ai/tasks/*/` 一层，避免全仓库遍历

---

## Next Actions
1. Phase 3: 双击创建音符
2. Phase 3: 批量移调/量化
3. Phase 3: 撤销/重做 (QUndoStack)
4. Phase 4: 超音域处理预览

---
*Last Updated: 2026-01-04 (Path Handling Known Issues & Search Constraints 更新)*
