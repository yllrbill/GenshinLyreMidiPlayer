# Context Pack - MIDI Editor Pipeline

## Task
- ID: 20260103-midi-editor-pipeline
- Status: DONE (Session 13 - BPM/Tempo Preservation Fixes)
- Last Updated: 2026-01-05
- Previous Commit: `9b7a351`

## Session 13 Summary (2026-01-05)
BPM/tempo preservation and scroll sync fixes based on audit reports.

### Issues Fixed
| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| 1 | HIGH | `_sync_timeline_tempo()` overwrites multi-segment tempo | Conditional call when `len(tempo_events) <= 1` |
| 2 | HIGH | Tempo map not preserved on save | Reuse `_tempo_events_tick` when BPM unchanged |
| 3 | MEDIUM | Cross-song bar duration pollution | Clear bar_durations on load |
| 4 | MEDIUM | KeyList scroll blockSignals issue | Removed blockSignals from set_scroll_offset |
| 5 | MEDIUM | Scrollbar width inconsistency | Removed fixed width from QSS |
| 6 | LOW | Vague note drop logging | Categorized drop reasons (accidental vs octave) |

### Key Changes
| File | Change |
|------|--------|
| `editor_window.py:586-588` | Clear variable bar data on load |
| `editor_window.py:600` | Cache `_tempo_events_tick` |
| `editor_window.py:627-630` | Conditional `_sync_timeline_tempo()` |
| `editor_window.py:1266-1268` | Reuse original tempo on save |
| `key_list_widget.py:151-153` | Remove fixed scrollbar width |
| `key_list_widget.py:163-165` | Simplify scroll sync |
| `thread.py:415-416,503-516,294-301` | Categorized drop logging |

## Previous Sessions (12-6)
- Session 12: Variable bar length system
- Session 11: Bar duration bug fixes (6 issues)
- Session 10: Bug fixes + duration adjust + auto-jitter
- Session 9: UI fixes (KeyList, auto-scroll, toolbar)
- Session 8: Bug fixes, i18n, keyboard config sync
- Session 7: Main GUI cleanup + KeyListWidget
- Session 6: Unified Playback Engine Phase 1-7

## Verification Required
1. **Bar grid stretch after save/reload**:
   - Open MIDI → stretch a bar → save → reload
   - Expected: Bar grid should remain stretched

2. **KeyList scroll sync during playback**:
   - Play MIDI → observe auto-scroll
   - Expected: KeyList and PianoRoll scroll together

3. **Note drop logging**:
   - Play MIDI with black keys
   - Expected: Log shows "accidental/black-key=N" or "octave-conflict=N"

## File Index

### Session 13 Modified Files
| Path | Lines Changed |
|------|---------------|
| `editor_window.py` | +15 |
| `key_list_widget.py` | -5 |
| `thread.py` | +30 |

### Key Files
| Path | Purpose |
|------|---------|
| `ui/editor/editor_window.py` | MIDI 加载/保存/播放协调 |
| `ui/editor/key_list_widget.py` | 按键序列进度显示 |
| `ui/editor/piano_roll.py` | 钢琴卷帘编辑器 |
| `ui/editor/timeline.py` | 时间轴 |
| `player/thread.py` | 播放线程 |

## Next Steps (for Planner)

1. **验收测试**: 拉长小节→保存→重载，确认小节刻度保持
2. **验收测试**: 播放自动翻页时 KeyList 同步
3. **提交**: 审计通过后 git commit
