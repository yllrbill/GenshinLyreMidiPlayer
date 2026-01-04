# Execute Log - Session 6-11

---

# Session 11 (2026-01-05) - Bar Duration Adjustment Bug Fixes

## Session Info
- Date: 2026-01-05
- Latest Commit: `bd39a79` autosave: 2026-01-05 05:58:18
- Focus: Bar duration adjustment algorithm fixes (6 bug fixes)
- Status: DONE

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| Fix 1 | Bar numbering: 1-based → 0-based conversion in piano_roll.py | DONE |
| Fix 2 | Continuous interval grouping for non-contiguous bar selection | DONE |
| Fix 3 | Delta calculation (delta_sec * bar_count) + interval overlap detection | DONE |
| Fix 4 | Ctrl drag visuals: no blue rect, only yellow lines | DONE |
| Fix 5 | i18n for "no bars selected" message | DONE |
| Fix 6 | List modified files | DONE |

## Changes Made

### piano_roll.py
- `_update_bar_overlay()`: Fixed bar numbering - changed `bar_num * _bar_duration_sec` to `(bar_num - 1) * _bar_duration_sec`
- `adjust_selected_bars_duration()`: Complete rewrite with:
  - Continuous interval grouping algorithm (e.g., [1,2,5,6] → [[1,2], [5,6]])
  - Delta calculation: `delta_sec_per_bar * bar_count`
  - Interval overlap detection instead of note center point
  - Cumulative shift for notes between/after intervals

### timeline.py
- `paintEvent()`: Added `and not self._ctrl_dragging` condition to prevent blue rect during Ctrl+drag

### translations.py
- Added `no_bars_selected_title` translation key
- Added `no_bars_selected_msg` translation key

### editor_window.py
- Updated "no bars selected" message to use `tr("no_bars_selected_title")` and `tr("no_bars_selected_msg")`

## Files Modified (5)
| File | Change |
|------|--------|
| piano_roll.py | Bar numbering fix + duration adjustment rewrite (+200 lines) |
| timeline.py | Ctrl drag blue rect fix |
| translations.py | +2 translation keys |
| editor_window.py | Use tr() for no bars message |
| undo_commands.py | (linter changes) |

## Git Summary
```
bd39a79 autosave: 2026-01-05 05:58:18
8 files changed, 1108 insertions(+), 35 deletions(-)
```

---

# Session 10 (2026-01-05) - Bug Fixes & New Features

## Session Info
- Date: 2026-01-05
- Latest Commit: `864ba46` autosave: 2026-01-05 03:39:21
- Focus: Bug fixes (imports, timeline snap), new features (duration adjust, auto-jitter)
- Status: DONE

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 4 | Add extend duration feature (QSpinBox + apply button) | DONE |
| 5 | Auto-apply jitter on input style change | DONE |
| 6 | Add translations for duration controls | DONE |
| Fix | `undo_commands.py` - add missing `import weakref` | DONE |
| Fix | `timeline.py` - single click precise (no snap), drag = floor/ceil snap | DONE |
| Fix | `editor_window.py` - add missing `QPushButton` import | DONE |

## Changes Made

### undo_commands.py
- Added `import weakref` to fix NameError in AdjustDurationCommand

### timeline.py
- Replaced `_snap_to_bar()` with `_snap_bar_floor()` and `_snap_bar_ceil()`
- `mousePressEvent`: records precise time (no snap)
- `mouseMoveEvent`: shows raw position during drag (no snap preview)
- `mouseReleaseEvent`: single click = precise seek, drag = floor/ceil snap

### editor_window.py
- Added `QPushButton` to PyQt6.QtWidgets import
- Added duration adjustment controls (QSpinBox 50ms step + apply button)
- Added `_apply_duration_delta()` method
- Added `_on_input_style_changed()` handler for auto-jitter
- Connected `cmb_input_style.currentTextChanged` signal

### translations.py
- Added 4 translation keys: duration_label, duration_tooltip, apply_duration, apply_duration_tooltip

## Files Modified (7)
| File | Change |
|------|--------|
| undo_commands.py | +import weakref |
| timeline.py | snap logic rewrite |
| editor_window.py | +QPushButton, duration controls, auto-jitter |
| translations.py | +4 translation keys |
| key_list_widget.py | (linter changes) |
| piano_roll.py | (linter changes) |
| player/config.py | (linter changes) |

---

# Session 9 (2026-01-05) - UI Fixes & Auto-scroll

## Session Info
- Date: 2026-01-05
- Commit: `7713727` autosave: 2026-01-05 01:58:42
- Focus: KeyList width, progress bar highlighting, auto-scroll, audio sync, toolbar layout
- Status: DONE

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 1 | KeyLabelWidget width 50→80 (match keyboard) | DONE |
| 2 | Progress bar note highlighting - iterate all bars | DONE |
| 3 | Auto-scroll logic for playhead (80% threshold → 30% position) | DONE |
| 4 | Audio checkbox sync main→editor | DONE |
| 5 | Toolbar split into two rows | DONE |

## Changes Made

### key_list_widget.py
- `KeyLabelWidget.setFixedWidth(80)` - match keyboard widget width
- `update_playback_time()` - iterate all `_key_bars` to update played/current state
- Auto-scroll: when playhead > 80% viewport, scroll to 30% position

### piano_roll.py
- `set_playhead_position()` - added auto_scroll parameter
- Auto-scroll logic matching key_list_widget

### editor_window.py
- `addToolBarBreak()` after BPM control
- New `toolbar2` for Pause/Resume/Octave/Input/Style/KeyList controls

### main.py
- Added `_sync_editor_audio()` method
- Signal connection: `chk_sound.stateChanged` → `_sync_editor_audio`
- Sync called on editor open

## Files Modified (4)

| File | Change |
|------|--------|
| key_list_widget.py | Width fix, iterate all bars, auto-scroll |
| piano_roll.py | Auto-scroll for playhead |
| editor_window.py | Toolbar split |
| main.py | Audio checkbox sync |

---

# Session 8 (2026-01-05) - Bug Fixes & i18n

## Session Info
- Date: 2026-01-05
- Focus: Bug fixes, i18n, keyboard config sync
- Status: DONE

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 1 | Fix `_apply_input_style_jitter` crash (add ApplyJitterCommand) | DONE |
| 2 | Implement `KeyLabelWidget.set_scroll_offset` | DONE |
| 3 | Add `set_keyboard_config` method for root/layout sync | DONE |
| 4 | Menu i18n for Apply Input Style Jitter | DONE |
| 5 | effective_root calculation with octave offset | DONE |
| 6 | Real-time sync when main window settings change | DONE |
| 7 | Fix `_update_style_params_display` AttributeError | DONE |

## Changes Made

### undo_commands.py (+90 lines)
- Added `ApplyJitterCommand` class for undoable jitter operations
- Pre-generates random offsets for redo consistency
- Supports timing_offset_ms and duration_variation

### key_list_widget.py
- Added `_scroll_offset` instance variable
- Implemented `set_scroll_offset()` method
- Modified `paintEvent` to subtract scroll offset from y coordinates
- Performance optimization: skip invisible rows

### editor_window.py
- Added `ApplyJitterCommand` import
- Added `set_keyboard_config(root_note, layout_name)` method
- Menu action now uses `tr("apply_jitter")` and `tr("apply_jitter_tooltip")`
- Rewrote `_apply_input_style_jitter` to use QUndoCommand

### main.py
- Added signal connections: `cmb_root`, `cmb_octave`, `cmb_preset` → `_sync_editor_keyboard_config`
- Added `_sync_editor_keyboard_config()` method for real-time editor sync
- Fixed `effective_root` calculation: `root_note + (octave_shift * 12)`
- Removed orphaned `_update_style_params_display` call (line 195)

### translations.py
- Fixed format string placeholders: `{min_offset}`, `{max_offset}`, `{duration_pct:.0f}`

## Verification
```bash
cd d:/dw11/piano/LyreAutoPlayer
python main.py
# Result: Starts successfully (AttributeError fixed)
```

## Files Modified (5)
| File | Lines Changed |
|------|---------------|
| undo_commands.py | +90 |
| key_list_widget.py | +15 |
| editor_window.py | +20 |
| main.py | +15 |
| translations.py | +5 |

---

# Session 7 (2026-01-04) - KeyListWidget & Cleanup

## Session Info
- Date: 2026-01-04
- Focus: KeyListWidget + Main GUI Cleanup + i18n
- Status: DONE

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 5 | Main GUI Cleanup (removed 8-bar/input style/error widgets) | DONE |
| 6 | KeyListWidget (new key sequence progress display) | DONE |
| 7 | i18n translations update | DONE |

## Changes Made

### config_mixin.py
- `collect_cfg()` returns default disabled `ErrorConfig`
- `_collect_eight_bar_style()` returns default disabled `EightBarStyle`
- `load_settings()` skips widget updates for removed features

### settings_preset_mixin.py
- `on_apply_settings_preset()` only stores internal state
- `on_reset_defaults()` removed widget references
- `_collect_current_settings()` returns defaults
- `_apply_settings_dict()` skips widget updates

### key_list_widget.py (NEW ~307 lines)
- `NoteLabel` - note display with index, name, time, duration
- `KeyListWidget` - scrollable list with auto-scroll, highlighting

### editor_window.py
- Added `KeyListWidget` as right sidebar with QSplitter
- Added `chk_key_list` toggle checkbox
- Updated playback methods to update key list

### translations.py
- +6 translation keys for Key List and Editor controls

## Verification
```bash
python -m py_compile ui/editor/key_list_widget.py ui/editor/editor_window.py
python -m py_compile ui/mixins/config_mixin.py ui/mixins/settings_preset_mixin.py
python -m py_compile i18n/translations.py main.py
# All passed
```

---

# Session 6 (Unified Playback Engine)

## Session Info
- Date: 2026-01-04
- Focus: 统一播放引擎 Phase 1-7 实现
- Status: DONE

## Plan Reference
- Plan File: `C:\Users\yllrb\.claude\plans\linked-gathering-glade.md`
- Goal: 主界面与编辑器共用 PlayerThread、严格跟谱模式、自动小节暂停、倒计时覆盖

## Git Status
```
Latest commit: d44912b fix(editor): sync timeline tempo on load
Changes: 12 files modified, 1 new file (countdown_overlay.py)
```

## Phase Implementation Summary

| Phase | File | Changes | Status |
|-------|------|---------|--------|
| 1 | `player/config.py` | +5 fields: strict_mode, pause_every_bars, auto_resume_countdown, bar_duration_override, editor_bpm | DONE |
| 2 | `player/thread.py` | +2 signals: countdown_tick, auto_pause_at_bar; auto-pause logic | DONE |
| 3 | `ui/editor/editor_window.py` | set_follow_mode(), export_events(), on_external_progress(), update_countdown() | DONE |
| 4 | `ui/mixins/playback_mixin.py` | _on_countdown_tick(), editor signal connections | DONE |
| 5 | `main.py` | _on_strict_mode_changed() UI disable logic | DONE |
| 6 | `ui/editor/countdown_overlay.py` | CountdownOverlay widget (NEW FILE ~66 lines) | DONE |
| 7 | `ui/mixins/settings_preset_mixin.py`, `config_mixin.py` | Settings persistence + i18n fix | DONE |

## Key Commands Executed

```powershell
# Syntax verification (external environment)
cd d:\dw11\piano\LyreAutoPlayer; python -m py_compile ui\editor\editor_window.py
# Exit code: 0

# Git diff generation
git diff HEAD -- LyreAutoPlayer/ > evidence/diff.patch
# Size: 29030 bytes
```

## Technical Notes

1. **i18n**: `update_countdown()` uses `getattr(self.parent(), "lang", LANG_ZH)` - only works when parent() is MainWindow with lang attribute
2. **velocity/channel**: `export_events()` exports but NoteEvent constructor ignores
3. **Playback architecture**: Main window → editor follows PlayerThread; editor standalone → local QTimer

## Files Modified (12 + 1 new)

| File | Lines Changed |
|------|---------------|
| player/config.py | +7 |
| player/thread.py | +40 |
| ui/editor/editor_window.py | +124 |
| ui/editor/__init__.py | +2 |
| ui/editor/countdown_overlay.py | +66 (NEW) |
| ui/floating.py | +24 |
| ui/mixins/playback_mixin.py | +45 |
| ui/mixins/config_mixin.py | +50 |
| ui/mixins/settings_preset_mixin.py | +5 |
| ui/tab_builders.py | +37 |
| main.py | +32 |
| i18n/translations.py | +10 |
