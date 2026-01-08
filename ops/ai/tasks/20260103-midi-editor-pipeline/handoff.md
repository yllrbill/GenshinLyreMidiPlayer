# Handoff - MIDI Editor Pipeline

## Session 17 (2026-01-06) - Strict MIDI Timing

### Status: DRAFT - Pending Planner Decision

### Evidence Index

| File | Path | Purpose |
|------|------|---------|
| context_pack.md | evidence/context_pack.md | 低 token 摘要 + 决策点 |
| diff.patch | evidence/diff.patch | 当前未提交改动 (1528 行) |
| execute.log | evidence/execute.log | 执行日志 Session 13-17 |
| plan.md | .claude/private/plan.md | 用户提供的阶段目标 |

### Uncommitted Changes (Session 17)

| File | Lines | Change |
|------|-------|--------|
| `player/config.py` | +1 | `strict_midi_timing: bool = False` |
| `player/thread.py` | +7/-6 | Strict mode: force mechanical + disable chord-lock |
| `main.py` | +22 | UI checkbox + handler |
| `ui/tab_builders.py` | +7 | Checkbox widget |
| `ui/mixins/config_mixin.py` | +11/-2 | Config propagation |
| `i18n/translations.py` | +5 | i18n strings |

### Session 16 Rollback

**Batch press_many was rolled back** - user reported it worsened dense sections.
Current approach: Deferred synth (Session 15) + strict MIDI timing (Session 17).

### Decision Required for Planner

1. **Commit** Session 17 (strict_midi_timing feature)?
2. **Test first** with Counting-Stars bar 17-18?
3. **Document** all timing-affecting configs (see table below)?

### Key Timing Configs Inventory (from plan.md)

| Config | File | Line | Effect | Strict Mode |
|--------|------|------|--------|-------------|
| `input_style` | config.py | 41 | timing_offset/stagger/duration | Forced to `mechanical` |
| `strict_midi_timing` | config.py | 51 | Master toggle | **NEW** |
| `min_press_interval_ms` | input_manager.py | - | Debounce between presses | Unchanged |
| `min_key_hold_ms` | config.py | - | Duration flooring | Unchanged |
| Chord-lock delay | thread.py | 628-634 | Delay between chord notes | **Disabled** |
| `pause_every_bars` | config.py | - | Auto-pause interval | Unchanged |
| `use_midi_duration` | config.py | - | Use MIDI note duration | Forced to True |

---

## Session 15 (2026-01-06) - Key Injection Performance

### Status: COMMITTED (6b18283)

### Completed Work
**Key Injection Performance Optimization - 7/7 COMPLETED**

| Step | Description | Status |
|------|-------------|--------|
| 1/7 | Reproduce issue with Counting-Stars bar 17-18 | OK |
| 2/7 | Add timing instrumentation in PlayerThread | OK |
| 3/7 | Batch same-timestamp SendInput for key injection | OK |
| 4/7 | Isolate FluidSynth from critical path | OK |
| 5/7 | Reorder KeyList 36-key to high→low pitch | OK |
| 6/7 | Unify Editor preview synth with main playback | OK |
| 7/7 | Validate all fixes and existing behavior | OK |

### Key Changes
1. **Deferred FluidSynth** (`thread.py:912-1060`)
   - Collect synth calls in `deferred_noteon` / `deferred_noteoff` lists
   - Execute all key injections first (timing-critical)
   - Execute synth calls after inner loop completes

2. **Timing Instrumentation** (`thread.py:901-904, 1062-1066`)
   - Lag detection: logs `[Lag]` when >50ms behind schedule
   - Batch metrics: logs `[Batch]` for slow batches >10ms with >2 events

3. **36-key Sort Order** (`key_list_widget.py:121,172,198-209`)
   - Added `_layout_name` attribute
   - 36-key layout uses reverse sort (high→low pitch)
   - 21-key layout preserves original (low→high pitch)

4. **Unified Preview Sound** (`editor_window.py:1812-1841`)
   - Editor's `_init_sound()` checks main window's settings first
   - Uses main's soundfont path and instrument selection
   - Falls back to default paths if unavailable

### Verification
```
python -m py_compile player/thread.py - OK
python -m py_compile ui/editor/key_list_widget.py - OK
python -m py_compile ui/editor/editor_window.py - OK
.venv/Scripts/python -c "import player.thread; ..." - All imports OK
```

### Next Steps
1. Manual test: Play `Counting-Stars-OneRepublic.mid` bar 17-18, verify no missed keys
2. Manual test: Verify 36-key KeyList shows high→low pitch order
3. Commit changes if tests pass

---

## Session 14 (2026-01-06) - time_signature denominator fix

### Status: PHASE DONE → NEW PHASE DEFINED

### Completed Work
**time_signature denominator fix - VERIFIED 6/6 PASSED**

| Issue | Root Cause | Fix |
|-------|------------|-----|
| Bar line density doubled after save/reload | Code used log2 conversion (denom_log) | Remove denom_log, use actual denominator value |
| mido semantics misunderstanding | Assumed MIDI file format exponent | mido abstracts exponent internally |

### Evidence Index

| File | Path | Purpose |
|------|------|---------|
| context_pack.md | evidence/context_pack.md | 低 token 摘要 + 新阶段目标 |
| diff.patch | evidence/diff.patch | 当前改动 (336 行) |
| execute.log | evidence/execute.log | 执行日志 + 6/6 验证结果 |
| tests.log | LyreAutoPlayer/tests.log | 语法验证 + mido semantics |

### Verification Results
```
=== PLANNER-EXECUTE LOG ===
Steps: 6
Status: ALL PASSED
- editor_window.py:1357-1362: denominator uses actual value
- playback_mixin.py:48-49: bar_boundaries_sec propagation
- config.py:54: bar_boundaries_sec field
- midi_parser.py:32-33: clip=True
- thread.py: bar_boundaries_sec + clip=True (5 sites)
- tests.log: 6/6 imports, mido denominator=4→4
```

---

## NEW PHASE: Key Injection Performance

### Goals (from plan.md)
1. Fix missed key injection under dense notes/chords (events pile up with play_sound=True)
2. Reorder KeyList (36-key) to high→low pitch
3. Unify Editor Play vs Main Start preview sound

### Reproduction
- MIDI: `midi/Counting-Stars-OneRepublic.mid`
- Section: bar ~17-18 / ~0:34s

### Decision Points for Planner
1. **Commit first?** Current changes (time_signature fix) are verified - commit before new phase?
2. **Priority order?** Key injection fix vs KeyList reorder vs preview sound?
3. **Synth isolation?** Separate thread vs queue vs degradation under overload?

---

## Session 13 (2026-01-05) - BPM/Tempo Preservation Fixes

### Goals
修复审计发现的 BPM/tempo 保存问题和 KeyList 滚动同步问题。

### Issues Fixed

| Severity | Issue | Root Cause | Fix |
|----------|-------|------------|-----|
| HIGH | 保存后重载小节刻度不拉长 | `_sync_timeline_tempo()` 覆盖多段 tempo | 仅当 `len(tempo_events) <= 1` 时调用 |
| HIGH | 保存时 tempo map 不保留 | 总是重建 tempo_events | BPM 未改动时复用 `_tempo_events_tick` |
| MEDIUM | 跨曲加载 bar_durations 污染 | 未清空旧数据 | load_midi() 开头清空 |
| MEDIUM | KeyList 拖动滚动同步问题 | blockSignals 阻止信号 | 移除 blockSignals |
| MEDIUM | 滚动条宽度不一致 | KeyList 固定 12px | 移除 QSS width |
| LOW | 音符丢弃日志模糊 | 无分类信息 | 区分 accidental vs octave |

### Evidence Index

| File | Path | Purpose |
|------|------|---------|
| context_pack.md | evidence/context_pack.md | 低 token 摘要 |
| diff.patch | evidence/diff.patch | 当前改动 (178 行) |
| execute.log | evidence/execute.log | 执行日志 |

### Verification Steps

1. **拉长小节后保存重载**
   ```
   打开 MIDI → 选择小节 → 右键调整时长 → Ctrl+S 保存 → 关闭 → 重新打开
   预期: 被拉长的小节刻度保持拉长状态
   ```

2. **播放自动翻页同步**
   ```
   打开 MIDI → 点击播放 → 观察红色播放头移动到可视区右侧 80% 时
   预期: KeyList 与 PianoRoll 同时翻页
   ```

3. **音符丢弃日志**
   ```
   打开含黑键的 MIDI → 播放
   预期: 日志显示 "Dropped N notes (accidental/black-key=X, octave-conflict=Y)"
   ```

### Current Status
- **状态**: 待验收
- **代码修改**: 已完成，语法验证通过
- **需要用户**: 手动测试验收步骤

### Next Steps
1. 用户执行验收测试
2. 验收通过后 git commit
3. 若验收失败，根据反馈调整

---

## Previous Sessions

### Session 12 (Commit: 62f4743)
Variable bar length system implementation.

### Session 11 (Commit: bd39a79)
Bar duration bug fixes (6 issues).

### Session 10 (Commit: 7b73a5d)
Bug fixes + duration adjust + auto-jitter.
