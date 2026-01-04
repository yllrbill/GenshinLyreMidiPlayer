# Context Pack - MIDI Editor Pipeline

## Task
- ID: 20260103-midi-editor-pipeline
- Status: DONE (Session 10 - Bug Fixes & New Features)
- Last Updated: 2026-01-05
- Latest Commit: `864ba46`
- Uncommitted: 7 files

## Session 10 Summary (2026-01-05)
Bug fixes + new features: imports, timeline snap, duration adjust, auto-jitter.

### Tasks Completed
| Task | Description | Status |
|------|-------------|--------|
| 4 | Duration adjustment (QSpinBox 50ms + apply) | DONE |
| 5 | Auto-apply jitter on input style change | DONE |
| 6 | Translations for duration controls | DONE |
| Fix | `undo_commands.py` - add `import weakref` | DONE |
| Fix | `timeline.py` - single click precise, drag = floor/ceil | DONE |
| Fix | `editor_window.py` - add `QPushButton` import | DONE |

### Key Changes
| File | Change |
|------|--------|
| `undo_commands.py` | +import weakref |
| `timeline.py` | snap logic rewrite (floor/ceil) |
| `editor_window.py` | +QPushButton, duration controls, auto-jitter |
| `translations.py` | +4 translation keys |

## Session 9 Summary (2026-01-05)
UI fixes: KeyList width, progress bar highlighting, auto-scroll, audio sync, toolbar layout.

## Session 8 Summary (2026-01-05)
Bug fixes, i18n improvements, keyboard config sync.

## Session 7 Summary (2026-01-04)
Main GUI cleanup + KeyListWidget + i18n updates.

## Session 6 Summary
Unified Playback Engine Phase 1-7 complete.

## Implementation Status

### Unified Playback Engine
| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Config fields | DONE |
| 2 | Auto-pause signals | DONE |
| 3 | Follow mode | DONE |
| 4 | Signal connections | DONE |
| 5 | Strict mode toggle | DONE |
| 6 | Countdown overlay | DONE |
| 7 | Settings persistence | DONE |

### Key Features
- 严格跟谱模式 + 自动小节暂停 + 倒计时覆盖
- 跟随模式 + 输入风格抖动 (undo/redo)
- 键盘配置同步 + KeyListWidget
- 时值调整 (QSpinBox + apply)
- 时间轴选区 (单击精确, 拖动吸附)

## File Index

### New Files
| Path | Lines | Purpose |
|------|-------|---------|
| `ui/editor/countdown_overlay.py` | 66 | 倒计时覆盖 |
| `ui/editor/key_list_widget.py` | 533 | 按键序列进度 |

### Session 10 Modified Files
| Path | Change |
|------|--------|
| `undo_commands.py` | +import weakref, AdjustDurationCommand |
| `timeline.py` | _snap_bar_floor/_snap_bar_ceil |
| `editor_window.py` | +QPushButton, duration controls |
| `translations.py` | +4 keys |

## Next Steps (for Planner)

1. **Commit**: `/repo-push` 提交 Session 10 变更
2. **用户测试**: 时间轴拖拽、时值调整、自动 jitter
3. **Phase 3-4**: 高级编辑 + 超音域处理预览（如需继续）
