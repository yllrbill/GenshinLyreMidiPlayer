# Project State

## Latest Task
- TASK_ID: 20260103-midi-editor-pipeline
- Status: DONE (Session 11 - Bar Duration Bug Fixes)
- Pointer: ops/ai/tasks/20260103-midi-editor-pipeline
- Latest Commit: `bd39a79`

## Previous Task
- TASK_ID: 20260102-2138-main-mixin-refactor
- Status: DONE (包含 Input Diagnostics 实现)
- Pointer: ops/ai/tasks/20260102-2138-main-mixin-refactor

## Current Focus
- Session 11: Bar duration adjustment bug fixes (6 issues)
- Session 10: Bug fixes (imports, timeline snap) + new features (duration adjust, auto-jitter)
- Session 9: UI fixes (KeyList width, progress bar, auto-scroll, audio sync, toolbar)

## Completed Summary (MIDI Editor)
- **Phase 1 钢琴卷帘骨架完成**: 6 个新文件 (~745 行)
- **Phase 1.5 main.py 集成**: 版本选择弹窗
- **Phase 2 基础编辑**: 选择/移动/删除/复制粘贴
- **Timeline Sync**: 加载时同步 BPM，确保对齐
- **Unified Playback Engine**: Phase 1-7 全部完成

## Session 9 Changes (UI Fixes & Auto-scroll)
| Task | File | Changes |
|------|------|---------|
| 1 | `key_list_widget.py` | Width 50→80 (match keyboard) |
| 2 | `key_list_widget.py` | iterate all _key_bars for highlighting |
| 3 | `key_list_widget.py`, `piano_roll.py` | Auto-scroll 80%→30% |
| 4 | `main.py` | _sync_editor_audio() + signal |
| 5 | `editor_window.py` | toolbar split with addToolBarBreak() |

## Session 8 Changes (Bug Fixes & i18n)
- ApplyJitterCommand, scroll sync, keyboard config sync, menu i18n, effective_root, real-time sync, AttributeError fix

## Session 6-7 Summary
| Phase | File | Changes |
|-------|------|---------|
| 1 | `player/config.py` | +5 fields |
| 2 | `player/thread.py` | +2 signals, auto-pause |
| 3 | `ui/editor/editor_window.py` | follow mode, export |
| 4 | `ui/mixins/playback_mixin.py` | signal connections |
| 5 | `main.py` | strict mode UI disable |
| 6 | `ui/editor/countdown_overlay.py` | NEW (+66 lines) |
| 7 | `config_mixin.py`, `settings_preset_mixin.py` | persistence |

## 行数统计（当前）
- main.py: 1050 行
- ui/tab_builders.py: 575 行
- i18n/translations.py: 179 行 (+6)
- ui/mixins/ 合计 910 行（7 files）
- ui/editor/ 合计 ~1900 行（7 files, +key_list_widget.py 307 行）

## Known Issues / Technical Debt
1. **BPM Scaling 效果待验证**: Session 4 用户反馈改 BPM 后音符时长不变
2. **保存后 BPM 待验证**: 保存的 MIDI 是否按新 BPM 播放
3. **Path Handling (P2 - Low Risk)**: 版本索引依赖 `midi-change/index.json`

## Pending Tasks
1. **用户测试**: 时间轴拖拽、时值调整、自动 jitter 功能
2. Phase 3-4: 高级编辑 + 超音域处理预览（如需继续）

## Recent Completions
- Bar Duration Bug Fixes (Session 11, 2026-01-05) - **Committed: bd39a79**
- Bug Fixes & New Features (Session 10, 2026-01-05) - Committed: 7b73a5d
- UI Fixes & Auto-scroll (Session 9, 2026-01-05) - Committed: 7713727
- Bug Fixes & i18n (Session 8, 2026-01-05)
- KeyListWidget + Main GUI Cleanup (Session 7, 2026-01-04)
- Unified Playback Engine Phase 1-7 (Session 6, 2026-01-04)

## Evidence
- Handoff: ops/ai/tasks/20260103-midi-editor-pipeline/handoff.md
- Context Pack: ops/ai/tasks/20260103-midi-editor-pipeline/evidence/context_pack.md
- Execute Log: ops/ai/tasks/20260103-midi-editor-pipeline/evidence/execute.md

## How to Resume in a New Session
1. Read `ops/ai/state/STATE.md`
2. Read latest task's `request.md` and `handoff.md`
3. Review evidence files if needed
4. Continue from task status

## Search Constraints
- 检索任务文档时仅扫描 `ops/ai/tasks/*/` 一层，避免全仓库遍历

---

## Next Actions
1. **用户测试**: 小节时长调整 (Ctrl+拖拽选择多个小节, 拉伸/压缩)
2. **验证**: 非连续小节 (1,2,5,6) 独立拉伸 + 累计平移
3. Phase 3-4: 高级编辑 + 超音域处理预览（如需继续）

---
*Last Updated: 2026-01-05 (Session 11 - Bar Duration Bug Fixes, DONE, Commit: bd39a79)*
