# Context Pack - MIDI Editor Pipeline

## Task
- ID: 20260103-midi-editor-pipeline
- Status: DONE (Session 9 - UI Fixes & Auto-scroll)
- Last Updated: 2026-01-05
- Latest Commit: `7713727`

## Session 9 Summary (2026-01-05)
UI fixes: KeyList width, progress bar highlighting, auto-scroll, audio sync, toolbar layout.

### Tasks Completed
| Task | Description | Status |
|------|-------------|--------|
| 1 | KeyLabelWidget width 50→80 (match keyboard) | DONE |
| 2 | Progress bar note highlighting - iterate all bars | DONE |
| 3 | Auto-scroll (80% threshold → 30% position) | DONE |
| 4 | Audio checkbox sync main→editor | DONE |
| 5 | Toolbar split into two rows | DONE |

### Key Changes
| File | Change |
|------|--------|
| `key_list_widget.py` | Width 80, iterate all bars, auto-scroll |
| `piano_roll.py` | Auto-scroll for playhead |
| `editor_window.py` | Toolbar split with addToolBarBreak() |
| `main.py` | _sync_editor_audio() method + signal |

## Session 8 Summary (2026-01-05)
Bug fixes, i18n improvements, keyboard config sync.

## Session 7 Summary (2026-01-04)
Main GUI 清理 + KeyListWidget + i18n 更新。

## Session 6 Summary
统一播放引擎 Phase 1-7 全部实现完成。

## Implementation Status

### Unified Playback Engine (Plan: linked-gathering-glade.md)

| Phase | Description | Key File | Status |
|-------|-------------|----------|--------|
| 1 | Config fields | `player/config.py` | ✅ |
| 2 | Auto-pause signals | `player/thread.py` | ✅ |
| 3 | Follow mode | `ui/editor/editor_window.py` | ✅ |
| 4 | Signal connections | `ui/mixins/playback_mixin.py` | ✅ |
| 5 | Strict mode toggle | `main.py` | ✅ |
| 6 | Countdown overlay | `ui/editor/countdown_overlay.py` | ✅ |
| 7 | Settings persistence | `config_mixin.py`, `settings_preset_mixin.py` | ✅ |

### Key Features Implemented
- **严格跟谱模式**: 开启后禁用 speed/error/8-bar 控件
- **自动小节暂停**: 支持每 1/2/4/8 小节暂停
- **倒计时覆盖**: 编辑器全屏半透明 + 悬浮窗数字显示
- **跟随模式**: 编辑器跟随主窗口 PlayerThread，禁用本地音频
- **输入风格抖动**: Apply Jitter with undo/redo support
- **键盘配置同步**: Main window → Editor real-time sync

## File Index

### New Files
| Path | Lines | Purpose |
|------|-------|---------|
| `ui/editor/countdown_overlay.py` | 66 | 倒计时覆盖组件 |
| `ui/editor/key_list_widget.py` | 533 | 按键序列进度显示 |

### Modified Files (Session 8)
| Path | Delta | Purpose |
|------|-------|---------|
| `undo_commands.py` | +90 | ApplyJitterCommand |
| `editor_window.py` | +20 | set_keyboard_config, i18n |
| `main.py` | +15 | sync_editor_keyboard_config |
| `translations.py` | +5 | format string fix |
| `key_list_widget.py` | +15 | scroll_offset |

## Next Steps (for Planner)

1. **用户测试**: 验证严格模式 + 自动暂停 + 倒计时 + KeyListWidget 功能
2. **Commit**: 变更已就绪，待用户确认后提交
3. **Phase 3-4**: 高级编辑 + 超音域处理预览（如需继续）
