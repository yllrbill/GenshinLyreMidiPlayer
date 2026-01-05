# -*- coding: utf-8 -*-
"""
PlayerThread - Main playback thread.

Handles:
- MIDI playback with quantization
- FluidSynth sound synthesis
- 8-bar style variations
- Error simulation
- Input timing and humanization
"""

import sys
import os
import time
import heapq
import random
from typing import List, Dict, Tuple, Optional

from PyQt6.QtCore import QThread, pyqtSignal

import mido

# Import local modules
from input_manager import create_input_manager, disable_ime_for_window, enable_ime_for_window
from style_manager import INPUT_STYLES

from .config import PlayerConfig
from .midi_parser import NoteEvent
from .scheduler import KeyEvent
from .quantize import build_available_notes, quantize_note, get_octave_shift
from .errors import plan_errors_for_group
from .bar_utils import calculate_bar_and_beat_duration

# Optional: FluidSynth for sound
try:
    import fluidsynth
    _fluidsynth_error = None
except ImportError as e:
    fluidsynth = None
    _fluidsynth_error = str(e)

# GM (General MIDI) instrument programs
GM_PROGRAM = {
    "Piano": 1, "Harpsichord": 7, "Celesta": 9, "Glockenspiel": 10,
    "Music Box": 11, "Vibraphone": 12, "Marimba": 13, "Xylophone": 14,
    "Organ": 20, "Accordion": 22, "Harmonica": 23, "Guitar": 25,
    "Harp": 47, "Strings": 49, "Choir": 53, "Trumpet": 57,
    "Flute": 74, "Pan Flute": 76, "Shakuhachi": 78, "Whistle": 79,
}

# Windows-specific imports
try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None
    win32con = None


def try_focus_window(hwnd: int) -> bool:
    """Try to focus a window by handle."""
    if win32gui is None or hwnd is None:
        return False
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


class PlayerThread(QThread):
    """
    Main playback thread.

    Signals:
        log(str): Emitted for log messages
        finished(): Emitted when playback completes
        progress(float, float): Emitted with (current_time, total_duration)
        paused(): Emitted when playback is paused
    """
    log = pyqtSignal(str)
    finished = pyqtSignal()
    progress = pyqtSignal(float, float)  # (current_time, total_duration)
    paused = pyqtSignal()  # Emitted when actually paused (for UI update)
    resumed = pyqtSignal()  # Emitted when playback resumes (for UI update)
    countdown_tick = pyqtSignal(int)  # remaining seconds (0=countdown finished)
    auto_pause_at_bar = pyqtSignal(int)  # bar_index where auto-paused

    def __init__(self, events: List[NoteEvent], cfg: PlayerConfig):
        super().__init__()
        self.events = events
        self.cfg = cfg
        self._stop = False
        self._paused = False
        self._pause_pending = False  # Pause at end of current bar
        self._pause_start = 0.0
        self._total_pause_time = 0.0
        self._bar_duration = 2.0  # Default bar duration (120BPM 4/4)
        self._bar_boundaries_sec: list = []  # 可变小节边界时间列表 (秒)
        self._current_bar = -1  # Current bar index
        self._total_duration = 0.0  # Total playback duration (for progress)
        self._last_progress_emit = 0.0  # Last time progress was emitted

        # Initialize InputManager v2 for reliable key handling in DirectX games
        self._input_manager = create_input_manager(
            enable_diagnostics=cfg.enable_diagnostics,
            backend="sendinput",  # Use SendInput API + scan codes
            target_hwnd=cfg.target_hwnd,  # Target window handle for focus monitoring
            enable_focus_monitor=True  # Auto-release keys when window loses focus
        )

    def stop(self):
        """Stop playback immediately."""
        self._stop = True
        # Release all keys immediately when stopping
        released = self._input_manager.release_all()
        if released > 0:
            self.log.emit(f"Stopped: released {released} keys")

    def pause(self):
        """Request pause at end of current bar."""
        if not self._paused and not self._pause_pending:
            self._pause_pending = True
            self.log.emit(f"Pause pending (at bar end)")

    def _do_pause(self):
        """Execute pause (internal call)."""
        if not self._paused:
            self._paused = True
            self._pause_pending = False
            self._pause_start = time.perf_counter()
            self.log.emit("Paused")
            self.paused.emit()  # Notify UI

    def _release_all_pressed(self, pressed_keys: Dict[str, int], fs, chan: int):
        """Release all pressed keys on pause/stop."""
        released = self._input_manager.release_all()
        if fs is not None:
            if hasattr(fs, "cc"):
                try:
                    fs.cc(chan, 123, 0)  # All notes off
                except Exception:
                    pass
            elif hasattr(fs, "all_notes_off"):
                try:
                    fs.all_notes_off(chan)
                except Exception:
                    pass
        if released > 0:
            self.log.emit(f"Pause: released {released} keys")
        pressed_keys.clear()

    def resume(self):
        """Resume playback."""
        if self._pause_pending:
            # Cancel pending pause
            self._pause_pending = False
            self.log.emit("Pause cancelled")
            self.resumed.emit()  # Notify UI
        elif self._paused:
            pause_duration = time.perf_counter() - self._pause_start
            self._total_pause_time += pause_duration
            self._paused = False
            self.log.emit(f"Resumed (paused {pause_duration:.1f}s)")
            self.resumed.emit()  # Notify UI

    def is_paused(self) -> bool:
        return self._paused

    def is_pause_pending(self) -> bool:
        return self._pause_pending

    def get_bar_duration(self) -> float:
        """Get current bar duration in seconds."""
        return self._bar_duration

    def get_current_bar(self) -> int:
        """Get current bar index."""
        return self._current_bar

    def get_previous_bar_start_time(self) -> float:
        """Calculate start time of previous bar (for resume from previous bar).

        Returns:
            Start time of previous bar in seconds, or 0.0 if at first bar.
        """
        if self._current_bar <= 1 or self._bar_duration <= 0:
            return 0.0
        return (self._current_bar - 1) * self._bar_duration

    def run(self):
        """Main playback loop."""
        if not self.events:
            self.log.emit("No events.")
            self.finished.emit()
            return

        # Prepare mapping (21-key or 36-key)
        effective_root = self.cfg.root_mid_do + (self.cfg.octave_shift * 12)
        avail_pairs = build_available_notes(effective_root, self.cfg.keyboard_preset)
        note_to_key: Dict[int, str] = {n: k for n, k in avail_pairs}
        avail_notes = list(note_to_key.keys())

        mode_str = self.cfg.keyboard_preset
        octave_str = f", octave {self.cfg.octave_shift:+d}" if self.cfg.octave_shift != 0 else ""
        self.log.emit(f"Mode: {mode_str} ({len(avail_notes)} notes{octave_str})")

        # Debug: show available note range
        sorted_notes = sorted(avail_notes)
        self.log.emit(f"Available MIDI range: {sorted_notes[0]}-{sorted_notes[-1]} (root={effective_root})")

        # Debug: analyze MIDI file note range
        midi_notes = [e.note for e in self.events]
        if midi_notes:
            midi_min, midi_max = min(midi_notes), max(midi_notes)
            in_range = sum(1 for n in midi_notes if n in avail_notes)
            self.log.emit(f"MIDI note range: {midi_min}-{midi_max}, in-range: {in_range}/{len(midi_notes)} ({100*in_range//len(midi_notes)}%)")

        # Initialize FluidSynth for local sound
        fs = self._init_fluidsynth()
        sfid = None
        chan = 0

        if fs is not None:
            sfid = fs.sfload(self.cfg.soundfont_path)
            if sfid == -1:
                self.log.emit(f"Sound: failed to load SoundFont")
                fs.delete()
                fs = None
            else:
                prog = GM_PROGRAM.get(self.cfg.instrument, 1) - 1
                fs.program_select(chan, sfid, 0, prog)
                self.log.emit(f"Sound: ON ({self.cfg.instrument}, vel={self.cfg.velocity})")

        # Focus window
        if self.cfg.target_hwnd is not None:
            ok = try_focus_window(self.cfg.target_hwnd)
            self.log.emit(f"Focus window: {'OK' if ok else 'FAILED (Alt-Tab manually)'}")
            if ok:
                time.sleep(0.2)

        # Countdown (skip if skip_countdown is True, e.g., resume from previous bar)
        if self.cfg.countdown_sec > 0 and not self.cfg.skip_countdown:
            self.log.emit(f"Countdown: {self.cfg.countdown_sec}s (switch to game now)")
            for i in range(self.cfg.countdown_sec, 0, -1):
                if self._stop:
                    self.countdown_tick.emit(0)  # Clear countdown UI
                    self.log.emit("Stopped during countdown.")
                    self.finished.emit()
                    return
                self.countdown_tick.emit(i)  # Notify UI of countdown
                self.log.emit(f"  ...{i}")
                time.sleep(1)
            self.countdown_tick.emit(0)  # Countdown finished
        elif self.cfg.skip_countdown:
            self.log.emit("Skipping countdown (resume from previous bar)")

        # Disable IME for target window
        ime_disabled_hwnd = None
        if self.cfg.target_hwnd is not None:
            if disable_ime_for_window(self.cfg.target_hwnd):
                ime_disabled_hwnd = self.cfg.target_hwnd
                self.log.emit("IME disabled for target window")

        # Build event queue
        event_queue, notes_scheduled, notes_dropped, notes_dropped_accidental, notes_dropped_octave_conflict = self._build_event_queue(
            note_to_key, avail_notes
        )

        # Skip events before start_at_time (for resume from previous bar)
        skipped_events = 0
        if self.cfg.start_at_time > 0:
            new_queue = []
            for ev in event_queue:
                if ev.time >= self.cfg.start_at_time:
                    new_queue.append(ev)
                else:
                    skipped_events += 1
            event_queue = new_queue
            heapq.heapify(event_queue)
            self.log.emit(f"Starting at {self.cfg.start_at_time:.2f}s, skipped {skipped_events} events")

        n_events = len(event_queue)
        self.log.emit(f"Playing {notes_scheduled} notes ({n_events} events)... (speed x{self.cfg.speed}, midi_dur={self.cfg.use_midi_duration})")

        # Calculate total duration for progress tracking
        if event_queue:
            self._total_duration = max(ev.time for ev in event_queue)
        else:
            self._total_duration = 0.0

        if notes_dropped > 0:
            detail_parts = []
            if notes_dropped_accidental > 0:
                detail_parts.append(f"accidental/black-key={notes_dropped_accidental}")
            if notes_dropped_octave_conflict > 0:
                detail_parts.append(f"octave-conflict={notes_dropped_octave_conflict}")
            detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
            self.log.emit(f"Dropped {notes_dropped} notes{detail}. Try 36-key or accidental_policy=lower/upper")

        # Main playback loop
        pressed_keys: Dict[str, int] = {}
        errors_applied = self._run_playback_loop(
            event_queue, pressed_keys, note_to_key, fs, chan
        )

        # Release any stuck keys
        released = self._input_manager.release_all()
        if released > 0:
            self.log.emit(f"Cleanup: released {released} stuck keys")

        # Cleanup FluidSynth
        if fs is not None:
            try:
                fs.delete()
            except Exception:
                pass

        # Final statistics
        total = notes_scheduled + notes_dropped
        if total > 0:
            drop_pct = 100 * notes_dropped // total
            if notes_dropped > 0:
                self.log.emit(f"Stats: played={notes_scheduled}, dropped={notes_dropped} ({drop_pct}%) [accidental={notes_dropped_accidental}, octave-conflict={notes_dropped_octave_conflict}]")
            else:
                self.log.emit(f"Stats: played={notes_scheduled}, dropped=0")

        if errors_applied > 0:
            self.log.emit(f"Errors simulated: {errors_applied}")

        # Output diagnostics
        if self.cfg.enable_diagnostics:
            self._output_diagnostics()

        # Re-enable IME
        if ime_disabled_hwnd is not None:
            if enable_ime_for_window(ime_disabled_hwnd):
                self.log.emit("IME re-enabled for target window")

        self.log.emit("Stopped." if self._stop else "Done.")
        self.finished.emit()

    def _init_fluidsynth(self):
        """Initialize FluidSynth synthesizer."""
        if not self.cfg.play_sound:
            return None

        if fluidsynth is None:
            err_msg = _fluidsynth_error if _fluidsynth_error else 'unknown error'
            self.log.emit(f"Sound: pyfluidsynth not available ({err_msg})")
            return None

        if not self.cfg.soundfont_path:
            self.log.emit("Sound: no SoundFont (.sf2) selected.")
            return None

        if not os.path.isfile(self.cfg.soundfont_path):
            self.log.emit(f"Sound: SoundFont file not found: {self.cfg.soundfont_path}")
            return None

        try:
            synth_kwargs = {'gain': 0.8, 'samplerate': 44100}
            if sys.platform != 'win32':
                synth_kwargs['midi.driver'] = 'none'

            fs = fluidsynth.Synth(**synth_kwargs)
            self.log.emit(f"Sound: FluidSynth created")

            # Audio settings for stability
            fs.setting('audio.period-size', 1024)
            fs.setting('audio.periods', 4)
            fs.setting('synth.polyphony', 64)

            if sys.platform == 'win32':
                fs.setting('midi.autoconnect', 0)
            else:
                fs.setting('midi.driver', 'none')

            # Try audio drivers
            drivers = ['dsound', 'wasapi', 'portaudio'] if sys.platform == 'win32' else ['pulseaudio', 'alsa', 'coreaudio']
            started = False
            for driver in drivers:
                try:
                    self.log.emit(f"Sound: trying driver '{driver}'...")
                    fs.start(driver=driver)
                    self.log.emit(f"Sound: driver '{driver}' started OK")
                    started = True
                    break
                except Exception as drv_err:
                    self.log.emit(f"Sound: driver '{driver}' failed: {drv_err}")

            if not started:
                self.log.emit("Sound: all audio drivers failed")
                fs.delete()
                return None

            return fs

        except Exception as e:
            self.log.emit(f"Sound init failed: {e}")
            import traceback
            self.log.emit(traceback.format_exc())
            return None

    def _build_event_queue(self, note_to_key: Dict[int, str], avail_notes: List[int]) -> Tuple[List[KeyEvent], int, int]:
        """Build the event queue with all press/release events."""
        event_queue: List[KeyEvent] = []
        default_press_s = max(0.001, self.cfg.press_ms / 1000.0)
        speed = max(1e-9, self.cfg.speed)

        # Timeline normalization
        next_free_time: Dict[str, float] = {}
        min_hold_ms = max(30.0, self._input_manager.config.min_key_hold_ms * 3)
        min_hold_s = min_hold_ms / 1000.0
        post_release_s = 0.010  # 10ms

        # Get input style
        style = INPUT_STYLES.get(self.cfg.input_style, INPUT_STYLES["mechanical"])
        self.log.emit(f"Input style: {self.cfg.input_style}")

        notes_scheduled = 0
        notes_dropped = 0
        notes_dropped_accidental = 0  # 黑键/无法映射到布局
        notes_dropped_octave_conflict = 0  # 八度冲突

        # Calculate bar duration
        beat_duration_for_filter = 0.5
        if self.cfg.midi_path and os.path.isfile(self.cfg.midi_path):
            try:
                mid_obj = mido.MidiFile(self.cfg.midi_path, clip=True)
                bar_duration, beat_duration_for_filter = calculate_bar_and_beat_duration(mid_obj)
                self._bar_duration = bar_duration
            except Exception:
                pass

        # Override bar duration from editor BPM (Pitfall #2: must be before event queue build)
        if self.cfg.bar_duration_override > 0:
            self._bar_duration = self.cfg.bar_duration_override
            self.log.emit(f"Using editor bar duration: {self._bar_duration:.3f}s")

        # Use variable bar boundaries if provided (for stretched bars)
        if self.cfg.bar_boundaries_sec:
            self._bar_boundaries_sec = list(self.cfg.bar_boundaries_sec)
            self.log.emit(f"Using {len(self._bar_boundaries_sec)} variable bar boundaries")

        # 8-bar style setup
        eight_bar = self.cfg.eight_bar_style
        eight_bar_segments, segment_duration, beat_duration, warp_start = self._setup_eight_bar(eight_bar, speed)
        use_warp = eight_bar.enabled and eight_bar.mode == "warp"
        use_beat_lock = eight_bar.enabled and eight_bar.mode == "beat_lock"

        # Precompute chord info for octave policy
        chord_tolerance = 0.005
        is_chord_note = [False] * len(self.events)
        i = 0
        while i < len(self.events):
            chord_start = self.events[i].time
            j = i + 1
            while j < len(self.events) and abs(self.events[j].time - chord_start) < chord_tolerance:
                j += 1
            if j - i > 1:
                for idx in range(i, j):
                    is_chord_note[idx] = True
            i = j

        # Build beat pitch info for octave policy
        beat_pitch_best: Dict[Tuple[int, int], Tuple[float, int]] = {}
        beat_highest: Dict[int, int] = {}
        beat_lowest: Dict[int, int] = {}

        if beat_duration_for_filter > 1e-9:
            for idx, ev in enumerate(self.events):
                if is_chord_note[idx]:
                    continue
                pitch = ev.note + self.cfg.transpose
                beat_idx = int(ev.time / beat_duration_for_filter)
                key = (beat_idx, pitch)
                best = beat_pitch_best.get(key)
                if best is None or ev.duration > best[0]:
                    beat_pitch_best[key] = (ev.duration, idx)

            for (beat_idx, pitch), (duration, idx) in beat_pitch_best.items():
                if beat_idx not in beat_highest or pitch > beat_highest[beat_idx]:
                    beat_highest[beat_idx] = pitch
                if beat_idx not in beat_lowest or pitch < beat_lowest[beat_idx]:
                    beat_lowest[beat_idx] = pitch

        # First pass: collect notes with quantization
        processed_notes = []
        avail_set = set(avail_notes)
        if self.cfg.octave_range_auto and avail_notes:
            oct_min = min(avail_notes)
            oct_max = max(avail_notes)
        else:
            oct_min = self.cfg.octave_min_note
            oct_max = self.cfg.octave_max_note
        if oct_min > oct_max:
            oct_min, oct_max = oct_max, oct_min

        for idx, ev in enumerate(self.events):
            note = ev.note + self.cfg.transpose
            shifted = False
            if self.cfg.accidental_policy == "octave":
                beat_idx = None
                if beat_duration_for_filter > 1e-9 and not is_chord_note[idx]:
                    beat_idx = int(ev.time / beat_duration_for_filter)
                shift = get_octave_shift(note, oct_min, oct_max)
                if shift is not None:
                    shifted = True
                    if beat_idx is None and beat_duration_for_filter > 1e-9 and not is_chord_note[idx]:
                        beat_idx = int(ev.time / beat_duration_for_filter)
                    if beat_idx is not None:
                        if shift < 0:
                            higher = beat_highest.get(beat_idx)
                            if higher is not None and higher > note:
                                notes_dropped += 1
                                notes_dropped_octave_conflict += 1
                                continue
                        else:
                            lower = beat_lowest.get(beat_idx)
                            if lower is not None and lower < note:
                                notes_dropped += 1
                                notes_dropped_octave_conflict += 1
                                continue

            q = quantize_note(note, avail_notes, self.cfg.accidental_policy, oct_min, oct_max)
            if q is None:
                notes_dropped += 1
                notes_dropped_accidental += 1
                continue

            key = note_to_key[q]
            if self.cfg.accidental_policy == "octave":
                shifted = (q != note)
            processed_notes.append((ev.time, ev.duration, key, q, shifted))

        # Second pass: apply humanization and schedule events
        i = 0
        while i < len(processed_notes):
            chord_start = processed_notes[i][0]
            chord_notes = []

            while i < len(processed_notes) and abs(processed_notes[i][0] - chord_start) < chord_tolerance:
                chord_notes.append(processed_notes[i])
                i += 1

            chord_start_scaled = chord_start / speed

            # Get 8-bar multipliers for this chord (use scaled timeline)
            speed_mult, timing_mult, duration_8bar_mult, section_selected = self._get_section_multipliers(
                chord_start_scaled, eight_bar_segments, segment_duration
            )

            bar_index = int(chord_start / self._bar_duration) if self._bar_duration > 0 else 0
            seg_start = int(chord_start_scaled / segment_duration) * segment_duration if segment_duration > 1e-9 else 0.0

            # Process each note in chord
            chord_processed = []
            for note_idx, (orig_time, orig_duration, key, q, shifted) in enumerate(chord_notes):
                base_time = orig_time

                # Apply timing offset (humanization)
                offset_s = 0.0
                if style.timing_offset_ms != (0, 0):
                    offset_ms = random.uniform(style.timing_offset_ms[0], style.timing_offset_ms[1])
                    offset_s += offset_ms / 1000.0

                # Apply stagger for chords
                if style.stagger_ms > 0 and len(chord_notes) > 1:
                    stagger_offset = note_idx * (style.stagger_ms / 1000.0)
                    offset_s += stagger_offset

                base_time += offset_s
                base_time /= speed

                if eight_bar.enabled:
                    base_time = seg_start + (base_time - seg_start) * timing_mult
                    if use_warp:
                        base_time, _ = self._map_time_warp(
                            base_time, 1.0, eight_bar_segments, segment_duration, warp_start
                        )
                    elif use_beat_lock:
                        base_time, _ = self._map_time_beat_lock(
                            base_time, 1.0, eight_bar_segments, segment_duration, beat_duration
                        )

                desired_time = max(0, base_time)

                # Determine note duration
                if self.cfg.use_midi_duration and orig_duration > 0:
                    duration = orig_duration
                else:
                    duration = default_press_s

                # Apply duration variation
                if style.duration_variation != 0:
                    if style.duration_variation > 0:
                        variation = random.uniform(-style.duration_variation, style.duration_variation)
                    else:
                        variation = random.uniform(style.duration_variation, 0)
                    duration *= (1 + variation)
                    duration = max(0.01, duration)

                duration = max(duration, min_hold_s)
                duration /= speed
                if eight_bar.enabled:
                    duration *= duration_8bar_mult

                key_lower = key.lower()
                nf = next_free_time.get(key_lower, 0.0)

                chord_processed.append({
                    'key': key,
                    'key_lower': key_lower,
                    'q': q,
                    'desired_time': desired_time,
                    'next_free': nf,
                    'duration': duration,
                    'order': note_idx,
                    'shifted': shifted,
                })

            # Calculate unified delay (Chord-Lock Normalization)
            chord_delay = 0.0
            for note_info in chord_processed:
                delay_needed = note_info['next_free'] - note_info['desired_time']
                if delay_needed > chord_delay:
                    chord_delay = delay_needed
            if chord_delay < 0:
                chord_delay = 0.0

            # Schedule events (serialize same-key notes within the same chord)
            key_groups: Dict[str, List[dict]] = {}
            for note_info in chord_processed:
                key_groups.setdefault(note_info['key_lower'], []).append(note_info)

            for key_lower, notes in key_groups.items():
                has_unshifted = any(not item['shifted'] for item in notes)
                if has_unshifted:
                    notes = [item for item in notes if not item['shifted']]
                elif len(notes) > 1:
                    best = max(notes, key=lambda item: (item['duration'], -item['order']))
                    notes = [best]
                notes.sort(key=lambda item: (item['duration'], item['order']))
                if len(notes) > 1:
                    total_short = sum(item['duration'] for item in notes[:-1])
                    total_short += post_release_s * (len(notes) - 1)
                    long_note = notes[-1]
                    long_note['duration'] = max(min_hold_s, long_note['duration'] - total_short)

                prev_release = None
                for note_info in notes:
                    key = note_info['key']
                    q = note_info['q']
                    duration = note_info['duration']

                    start_time = note_info['desired_time'] + chord_delay
                    if prev_release is not None:
                        start_time = max(start_time, prev_release + post_release_s)
                    if note_info['next_free'] > start_time:
                        start_time = note_info['next_free']

                    release_time = start_time + duration
                    next_free_time[key_lower] = release_time + post_release_s

                    heapq.heappush(event_queue, KeyEvent(start_time, 2, "press", key, q, bar_index=bar_index))
                    heapq.heappush(event_queue, KeyEvent(release_time, 1, "release", key, q, bar_index=bar_index))
                    notes_scheduled += 1
                    prev_release = release_time

        # Insert pause markers at bar boundaries (for pause-at-bar)
        # 优先使用可变小节边界列表 (支持拉长/压缩的小节)
        if self._bar_boundaries_sec and self.events:
            # 使用预计算的小节边界时间
            for bar_idx, boundary_orig in enumerate(self._bar_boundaries_sec, start=1):
                if boundary_orig <= 0:
                    continue  # 跳过 0 时刻 (第 1 小节起点不需要暂停标记)
                boundary_time = boundary_orig / speed
                if eight_bar.enabled:
                    _, timing_mult, _, _ = self._get_section_multipliers(
                        boundary_time, eight_bar_segments, segment_duration
                    )
                    seg_start = int(boundary_time / segment_duration) * segment_duration if segment_duration > 1e-9 else 0.0
                    mapped_time = seg_start + (boundary_time - seg_start) * timing_mult
                    if use_warp:
                        mapped_time, _ = self._map_time_warp(
                            mapped_time, 1.0, eight_bar_segments, segment_duration, warp_start
                        )
                    elif use_beat_lock:
                        mapped_time, _ = self._map_time_beat_lock(
                            mapped_time, 1.0, eight_bar_segments, segment_duration, beat_duration
                        )
                    boundary_time = mapped_time
                pause_marker_time = max(0.0, boundary_time - 0.001)
                heapq.heappush(
                    event_queue,
                    KeyEvent(pause_marker_time, 0, "pause_marker", "", 0, bar_index=bar_idx)
                )
        elif self._bar_duration > 1e-9 and self.events:
            # 兜底: 使用固定小节时长计算边界
            total_time = max(e.time + e.duration for e in self.events)
            num_bars = int(total_time / self._bar_duration) + 1
            for bar_idx in range(1, num_bars + 1):
                boundary_orig = bar_idx * self._bar_duration
                boundary_time = boundary_orig / speed
                if eight_bar.enabled:
                    _, timing_mult, _, _ = self._get_section_multipliers(
                        boundary_time, eight_bar_segments, segment_duration
                    )
                    seg_start = int(boundary_time / segment_duration) * segment_duration if segment_duration > 1e-9 else 0.0
                    mapped_time = seg_start + (boundary_time - seg_start) * timing_mult
                    if use_warp:
                        mapped_time, _ = self._map_time_warp(
                            mapped_time, 1.0, eight_bar_segments, segment_duration, warp_start
                        )
                    elif use_beat_lock:
                        mapped_time, _ = self._map_time_beat_lock(
                            mapped_time, 1.0, eight_bar_segments, segment_duration, beat_duration
                        )
                    boundary_time = mapped_time
                pause_marker_time = max(0.0, boundary_time - 0.001)
                heapq.heappush(
                    event_queue,
                    KeyEvent(pause_marker_time, 0, "pause_marker", "", 0, bar_index=bar_idx)
                )

        return event_queue, notes_scheduled, notes_dropped, notes_dropped_accidental, notes_dropped_octave_conflict

    def _setup_eight_bar(self, eight_bar, speed: float):
        """Setup 8-bar style variation parameters."""
        eight_bar_segments: Dict[int, Tuple[float, float, float, bool]] = {}
        segment_duration = 16.0
        beat_duration = 0.5
        warp_start: List[float] = []

        if not eight_bar.enabled or not self.events:
            return eight_bar_segments, segment_duration, beat_duration, warp_start

        # Calculate real bar and beat duration from MIDI
        bar_duration = 2.0
        if self.cfg.midi_path and os.path.isfile(self.cfg.midi_path):
            try:
                mid_obj = mido.MidiFile(self.cfg.midi_path, clip=True)
                bar_duration, beat_duration = calculate_bar_and_beat_duration(mid_obj)
                self.log.emit(f"8-Bar: bar_duration={bar_duration:.3f}s, beat_duration={beat_duration:.3f}s")
            except Exception as e:
                self.log.emit(f"8-Bar: using defaults (error: {e})")

        if speed > 1e-9:
            bar_duration /= speed
            beat_duration /= speed

        segment_duration = bar_duration * 8
        total_duration = max(e.time + e.duration for e in self.events)
        num_segments = max(1, int(total_duration / segment_duration) + 1)

        # Determine selection pattern
        pattern = eight_bar.selection_pattern
        if pattern == "continuous":
            period, pick_mod = 1, 0
        elif pattern == "skip3_pick1":
            period, pick_mod = 4, 3
        elif pattern == "skip2_pick1":
            period, pick_mod = 3, 2
        else:  # skip1_pick1
            period, pick_mod = 2, 1

        # Pre-generate multipliers
        for seg_idx in range(num_segments):
            selected = (seg_idx % period == pick_mod)
            if selected:
                speed_mult = random.uniform(eight_bar.speed_mult_min, eight_bar.speed_mult_max)
                timing_mult = random.uniform(eight_bar.timing_mult_min, eight_bar.timing_mult_max)
                duration_mult = random.uniform(eight_bar.duration_mult_min, eight_bar.duration_mult_max)
                if eight_bar.clamp_enabled:
                    clamp_min = min(eight_bar.clamp_min, eight_bar.clamp_max)
                    clamp_max = max(eight_bar.clamp_min, eight_bar.clamp_max)
                    speed_mult = max(clamp_min, min(speed_mult, clamp_max))
                    timing_mult = max(clamp_min, min(timing_mult, clamp_max))
                    duration_mult = max(clamp_min, min(duration_mult, clamp_max))
            else:
                speed_mult, timing_mult, duration_mult = 1.0, 1.0, 1.0
            eight_bar_segments[seg_idx] = (speed_mult, timing_mult, duration_mult, selected)

        # Build warp_start array
        warp_start = [0.0]
        for seg_idx in range(num_segments):
            speed_mult_i = eight_bar_segments.get(seg_idx, (1.0, 1.0, 1.0, False))[0]
            actual_seg_duration = segment_duration / max(1e-9, speed_mult_i)
            warp_start.append(warp_start[-1] + actual_seg_duration)

        selected_count = sum(1 for v in eight_bar_segments.values() if v[3])
        mode_str = "Tempo Warp" if eight_bar.mode == "warp" else "Beat-Lock"
        self.log.emit(f"8-Bar {mode_str}: {selected_count}/{num_segments} segments selected ({pattern})")

        return eight_bar_segments, segment_duration, beat_duration, warp_start

    def _get_section_multipliers(self, orig_time: float, eight_bar_segments: Dict, segment_duration: float) -> Tuple[float, float, float, bool]:
        """Get multipliers for the segment at orig_time."""
        if not eight_bar_segments:
            return (1.0, 1.0, 1.0, False)
        seg_idx = int(orig_time / segment_duration) if segment_duration > 1e-9 else 0
        return eight_bar_segments.get(seg_idx, (1.0, 1.0, 1.0, False))

    def _map_time_warp(self, orig_time: float, base_speed: float, eight_bar_segments: Dict, segment_duration: float, warp_start: List[float]) -> Tuple[float, float]:
        """Tempo Warp time mapping."""
        if not eight_bar_segments or not warp_start:
            return (orig_time / max(1e-9, base_speed), base_speed)

        seg_idx = int(orig_time / segment_duration) if segment_duration > 1e-9 else 0
        seg_idx = min(seg_idx, len(warp_start) - 2)

        speed_mult = eight_bar_segments.get(seg_idx, (1.0, 1.0, 1.0, False))[0]
        effective_speed = base_speed * speed_mult

        seg_start_orig = seg_idx * segment_duration
        offset_in_seg = orig_time - seg_start_orig
        mapped_offset = offset_in_seg / max(1e-9, speed_mult)
        mapped_time = (warp_start[seg_idx] + mapped_offset) / max(1e-9, base_speed)

        return (mapped_time, effective_speed)

    def _map_time_beat_lock(self, orig_time: float, base_speed: float, eight_bar_segments: Dict, segment_duration: float, beat_duration: float) -> Tuple[float, float]:
        """Beat-Lock time mapping."""
        if not eight_bar_segments or beat_duration <= 1e-9:
            return (orig_time / max(1e-9, base_speed), base_speed)

        seg_idx = int(orig_time / segment_duration) if segment_duration > 1e-9 else 0

        speed_mult, timing_mult, _, _ = eight_bar_segments.get(seg_idx, (1.0, 1.0, 1.0, False))
        effective_speed = base_speed * speed_mult

        seg_start_orig = seg_idx * segment_duration
        offset_in_seg = orig_time - seg_start_orig

        beat_index = int(offset_in_seg / beat_duration)
        frac_in_beat = offset_in_seg - (beat_index * beat_duration)
        scaled_frac = frac_in_beat * timing_mult

        mapped_offset = (beat_index * beat_duration) + scaled_frac
        mapped_time = (seg_start_orig + mapped_offset) / max(1e-9, base_speed * speed_mult)

        return (mapped_time, effective_speed)

    def _run_playback_loop(self, event_queue: List[KeyEvent], pressed_keys: Dict[str, int], note_to_key: Dict[int, str], fs, chan: int) -> int:
        """Run the main playback loop."""
        error_cfg = self.cfg.error_config
        bar_duration = 2.0
        group_duration = bar_duration * 8
        current_bar_group = -1
        errors_for_group: List[Tuple[str, float]] = []
        error_index = 0
        errors_applied = 0
        speed = max(1e-9, self.cfg.speed)

        if error_cfg.enabled:
            self.log.emit(f"Error simulation: ON ({error_cfg.errors_per_8bars}/8bars)")

        start = time.perf_counter()

        while event_queue and not self._stop:
            # Handle pause state
            while self._paused and not self._stop:
                time.sleep(0.05)

            if self._stop:
                break

            next_event = event_queue[0]
            target_time = next_event.time

            # Wait until event time
            now = time.perf_counter() - start - self._total_pause_time

            # Emit progress (throttled to ~10 times/sec)
            if now - self._last_progress_emit >= 0.1:
                self.progress.emit(now, self._total_duration)
                self._last_progress_emit = now

            dt = target_time - now
            while dt > 0 and not self._stop:
                if self._paused:
                    break
                time.sleep(min(dt, 0.02))
                now = time.perf_counter() - start - self._total_pause_time
                # Emit progress at ~10Hz for smooth playhead updates
                if now - self._last_progress_emit >= 0.1:
                    self.progress.emit(now, self._total_duration)
                    self._last_progress_emit = now
                dt = target_time - now

            if self._paused:
                continue

            if self._stop:
                break

            # Timing instrumentation: detect lag (when we're behind schedule)
            lag_ms = -dt * 1000  # positive when behind schedule
            if lag_ms > 50:  # Log if >50ms behind
                self.log.emit(f"[Lag] {lag_ms:.1f}ms behind @ t={target_time:.3f}s, queue={len(event_queue)}")

            # Process all events at this time
            eps = 0.001
            processed_bar = None
            paused_now = False
            batch_start = time.perf_counter()
            batch_count = 0
            # Deferred synth calls - prioritize key injection over audio
            deferred_noteon = []   # [(note, velocity), ...]
            deferred_noteoff = []  # [note, ...]
            while event_queue and not self._stop:
                next_event = event_queue[0]
                if next_event.time > target_time + eps:
                    break

                heapq.heappop(event_queue)
                processed_bar = next_event.bar_index
                batch_count += 1

                if next_event.event_type == "pause_marker":
                    # Check if auto-pause should trigger at this bar
                    should_auto_pause = (
                        self.cfg.pause_every_bars > 0 and
                        next_event.bar_index > 0 and
                        next_event.bar_index % self.cfg.pause_every_bars == 0
                    )

                    if self._pause_pending or should_auto_pause:
                        self.log.emit(
                            f"[Pause] {'auto-' if should_auto_pause else 'pending '}at bar {next_event.bar_index} (t={next_event.time:.3f}s)"
                        )
                        self._release_all_pressed(pressed_keys, fs, chan)
                        self._do_pause()
                        self.auto_pause_at_bar.emit(next_event.bar_index)
                        paused_now = True

                        if should_auto_pause:
                            # Auto-pause countdown (倒计时结束自动继续，F5可提前跳过)
                            countdown_interrupted = False
                            for remaining in range(self.cfg.auto_resume_countdown, 0, -1):
                                if self._stop:
                                    break
                                if not self._paused:  # User pressed F5 to skip
                                    self.countdown_tick.emit(0)  # Clear countdown UI
                                    countdown_interrupted = True
                                    break
                                self.countdown_tick.emit(remaining)
                                time.sleep(1.0)

                            # Auto-resume after countdown (if still paused and not interrupted)
                            if self._paused and not self._stop and not countdown_interrupted:
                                self.countdown_tick.emit(0)
                                self.resume()  # 自动继续

                        break
                    continue

                if next_event.event_type == "press":
                    key = next_event.key
                    note = next_event.note
                    skip_note = False
                    extra_key = None
                    extra_note = None
                    wrong_note_applied = False

                    # Error simulation
                    if error_cfg.enabled:
                        event_time = next_event.time
                        new_bar_group = int(event_time / group_duration)

                        if new_bar_group != current_bar_group:
                            current_bar_group = new_bar_group
                            errors_for_group = plan_errors_for_group(error_cfg)
                            error_index = 0

                        if error_index < len(errors_for_group):
                            group_start = current_bar_group * group_duration
                            event_pos_in_group = (event_time - group_start) / group_duration

                            error_type, error_pos = errors_for_group[error_index]
                            if event_pos_in_group >= error_pos:
                                error_index += 1
                                errors_applied += 1

                                if error_type == "wrong_note":
                                    offset = random.choice([-1, 1])
                                    new_note = note + offset
                                    if new_note in note_to_key:
                                        key = note_to_key[new_note]
                                        note = new_note
                                        wrong_note_applied = True
                                    self.log.emit(f"[Error] Wrong note @ {event_time:.2f}s")

                                elif error_type == "miss_note":
                                    skip_note = True
                                    self.log.emit(f"[Error] Missed note @ {event_time:.2f}s")

                                elif error_type == "extra_note":
                                    offset = random.choice([-1, 1])
                                    extra_note_val = note + offset
                                    if extra_note_val in note_to_key:
                                        extra_key = note_to_key[extra_note_val]
                                        extra_note = extra_note_val
                                    self.log.emit(f"[Error] Extra note @ {event_time:.2f}s")

                                elif error_type == "pause":
                                    pause_ms = random.randint(error_cfg.pause_min_ms, error_cfg.pause_max_ms)
                                    time.sleep(pause_ms / 1000.0)
                                    self.log.emit(f"[Error] Pause {pause_ms}ms @ {event_time:.2f}s")

                    if skip_note:
                        continue

                    # Press key - prioritize key injection, defer synth
                    if key not in pressed_keys or pressed_keys[key] == 0:
                        self._input_manager.press(key, note)
                        if fs is not None:
                            deferred_noteon.append((note, self.cfg.velocity))
                    pressed_keys[key] = pressed_keys.get(key, 0) + 1

                    # Handle extra note
                    if extra_key is not None:
                        if extra_key not in pressed_keys or pressed_keys[extra_key] == 0:
                            self._input_manager.press(extra_key, extra_note)
                            if fs is not None and extra_note is not None:
                                deferred_noteon.append((extra_note, self.cfg.velocity))
                        pressed_keys[extra_key] = pressed_keys.get(extra_key, 0) + 1
                        heapq.heappush(event_queue, KeyEvent(
                            next_event.time + 0.05, 1, "release", extra_key, extra_note or 0,
                            bar_index=next_event.bar_index
                        ))

                    # Handle wrong note release
                    if wrong_note_applied:
                        heapq.heappush(event_queue, KeyEvent(
                            next_event.time + 0.08, 1, "release", key, note,
                            bar_index=next_event.bar_index
                        ))

                elif next_event.event_type == "release":
                    key = next_event.key
                    if key in pressed_keys:
                        pressed_keys[key] -= 1
                        if pressed_keys[key] <= 0:
                            self._input_manager.release(key, next_event.note)
                            if fs is not None:
                                deferred_noteoff.append(next_event.note)
                            pressed_keys[key] = 0

            # Execute deferred synth calls after all key injections are done
            # This prioritizes key injection (timing-critical) over audio (can tolerate latency)
            if fs is not None:
                for note, velocity in deferred_noteon:
                    fs.noteon(chan, note, velocity)
                for note in deferred_noteoff:
                    fs.noteoff(chan, note)

            # Batch processing time instrumentation
            if batch_count > 0:
                batch_elapsed_ms = (time.perf_counter() - batch_start) * 1000
                if batch_elapsed_ms > 10 and batch_count > 2:  # Log slow batches with multiple events
                    self.log.emit(f"[Batch] {batch_count} events in {batch_elapsed_ms:.1f}ms @ t={target_time:.3f}s")

            if paused_now:
                continue

            if processed_bar is not None:
                self._current_bar = processed_bar

        return errors_applied

    def _output_diagnostics(self):
        """Output InputManager diagnostics."""
        diag = self._input_manager.get_diagnostics()
        stats = diag['stats']
        backend = diag.get('backend', 'unknown')

        self.log.emit(f"[Input] Backend: {backend}")
        self.log.emit(f"[Input] Press: {stats['total_press']}, Release: {stats['total_release']}, "
                     f"Failed: {stats['failed_press']}/{stats['failed_release']}")
        self.log.emit(f"[Input] Latency: avg={stats['avg_latency_ms']:.1f}ms, max={stats['max_latency_ms']:.1f}ms")

        if stats.get('focus_lost_releases', 0) > 0:
            self.log.emit(f"[Input] Focus lost releases: {stats['focus_lost_releases']}")
        if stats.get('stuck_recoveries', 0) > 0:
            self.log.emit(f"[Input] Stuck key recoveries: {stats['stuck_recoveries']}")

        lat_dist = stats.get('latency_distribution', {})
        if lat_dist:
            dist_str = ", ".join(f"{k}:{v}" for k, v in lat_dist.items() if v > 0)
            if dist_str:
                self.log.emit(f"[Input] Latency distribution: {dist_str}")
