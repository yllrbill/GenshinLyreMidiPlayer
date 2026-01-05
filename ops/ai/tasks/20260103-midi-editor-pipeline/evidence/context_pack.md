# Context Pack - MIDI Editor Pipeline

## Task
- ID: 20260103-midi-editor-pipeline
- Status: PHASE DONE → PENDING COMMIT
- Last Updated: 2026-01-06
- Latest Commit: `2789fbe` (uncommitted changes in progress)

---

## Session 15 Summary (2026-01-06)
**Key Injection Performance Optimization - 7/7 COMPLETED**

### Key Changes
1. **Deferred FluidSynth** - All key injections execute first, synth calls batched after
2. **Timing instrumentation** - Logs lag >50ms and slow batches >10ms
3. **36-key sort order** - KeyList now shows high→low pitch for 36-key layout
4. **Unified preview sound** - Editor uses main window's soundfont/instrument

### Modified Files
| File | Lines Changed | Description |
|------|---------------|-------------|
| `thread.py` | +25 | Lag detection, deferred synth |
| `key_list_widget.py` | +10 | 36-key reverse sort |
| `editor_window.py` | +15 | Main window sf/instrument sync |

### Verification Status
- All syntax checks PASSED
- All imports verified OK

---

## Session 14 Summary (2026-01-06)
**time_signature denominator fix - VERIFIED 6/6 PASSED**

### Key Fix
- **Problem**: Bar line density doubled after save/reload
- **Root Cause**: Code used log2 conversion (`denom_log`) but mido expects actual values
- **Fix**: Remove denom_log conversion, use `denominator=denominator` directly

### Verification Results
| Step | Component | Status |
|------|-----------|--------|
| 1/6 | editor_window.py:1357-1362 | OK - denominator uses actual value |
| 2/6 | playback_mixin.py:48-49 | OK - bar_boundaries_sec propagation |
| 3/6 | config.py:54 | OK - bar_boundaries_sec field |
| 4/6 | midi_parser.py:32-33 | OK - clip=True |
| 5/6 | thread.py:102,433,445-447,676,678,746 | OK - bar_boundaries_sec + clip=True |
| 6/6 | tests.log | OK - 6/6 imports, mido denominator=4→4 |

---

## NEW PHASE: Key Injection Performance (Defined in plan.md)

### Goals
1. Fix missed key injection under dense notes/chords (events pile up with play_sound=True)
2. Reorder KeyList (36-key) to high→low pitch
3. Unify Editor Play vs Main Start preview sound

### Reproduction
- MIDI: `midi/Counting-Stars-OneRepublic.mid`
- Section: bar ~17-18 / ~0:34s

### Target Files
| File | Change |
|------|--------|
| `player/thread.py` | Lag instrumentation, batch SendInput, decouple synth |
| `input_manager.py` | Optional batch SendInput for chords |
| `ui/editor/key_list_widget.py` | Sort 36-key rows by pitch descending |
| `ui/editor/editor_window.py` | Align preview synth with main playback |

---

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
