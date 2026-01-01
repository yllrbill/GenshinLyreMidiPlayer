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
        progress(int, int): Emitted with (current_event, total_events)
        paused(): Emitted when playback is paused
    """
    log = pyqtSignal(str)
    finished = pyqtSignal()
    progress = pyqtSignal(int, int)  # (current_event, total_events)
    paused = pyqtSignal()  # Emitted when actually paused (for UI update)

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
        self._current_bar = -1  # Current bar index

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
        elif self._paused:
            pause_duration = time.perf_counter() - self._pause_start
            self._total_pause_time += pause_duration
            self._paused = False
            self.log.emit(f"Resumed (paused {pause_duration:.1f}s)")

    def is_paused(self) -> bool:
        return self._paused

    def is_pause_pending(self) -> bool:
        return self._pause_pending

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

        # Countdown
        if self.cfg.countdown_sec > 0:
            self.log.emit(f"Countdown: {self.cfg.countdown_sec}s (switch to game now)")
            for i in range(self.cfg.countdown_sec, 0, -1):
                if self._stop:
                    self.log.emit("Stopped during countdown.")
                    self.finished.emit()
                    return
                self.log.emit(f"  ...{i}")
                time.sleep(1)

        # Disable IME for target window
        ime_disabled_hwnd = None
        if self.cfg.target_hwnd is not None:
            if disable_ime_for_window(self.cfg.target_hwnd):
                ime_disabled_hwnd = self.cfg.target_hwnd
                self.log.emit("IME disabled for target window")

        # Build event queue
        event_queue, notes_scheduled, notes_dropped = self._build_event_queue(
            note_to_key, avail_notes
        )

        n_events = len(event_queue)
        self.log.emit(f"Playing {notes_scheduled} notes ({n_events} events)... (speed x{self.cfg.speed}, midi_dur={self.cfg.use_midi_duration})")

        if notes_dropped > 0:
            self.log.emit(f"Dropped {notes_dropped} out-of-range notes")

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
            self.log.emit(f"Stats: played={notes_scheduled}, dropped={notes_dropped} ({100*notes_dropped//total}% dropped)")

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

        # Calculate bar duration
        beat_duration_for_filter = 0.5
        if self.cfg.midi_path and os.path.isfile(self.cfg.midi_path):
            try:
                mid_obj = mido.MidiFile(self.cfg.midi_path)
                bar_duration, beat_duration_for_filter = calculate_bar_and_beat_duration(mid_obj)
                self._bar_duration = bar_duration
            except Exception:
                pass

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
                                continue
                        else:
                            lower = beat_lowest.get(beat_idx)
                            if lower is not None and lower < note:
                                notes_dropped += 1
                                continue

            q = quantize_note(note, avail_notes, self.cfg.accidental_policy, oct_min, oct_max)
            if q is None:
                notes_dropped += 1
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
        if self._bar_duration > 1e-9 and self.events:
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
                heapq.heappush(
                    event_queue,
                    KeyEvent(boundary_time, 0, "pause_marker", "", 0, bar_index=bar_idx)
                )

        return event_queue, notes_scheduled, notes_dropped

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
                mid_obj = mido.MidiFile(self.cfg.midi_path)
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
            dt = target_time - now
            while dt > 0 and not self._stop:
                if self._paused:
                    break
                time.sleep(min(dt, 0.02))
                now = time.perf_counter() - start - self._total_pause_time
                dt = target_time - now

            if self._paused:
                continue

            if self._stop:
                break

            # Process all events at this time
            eps = 0.001
            processed_bar = None
            paused_now = False
            while event_queue and not self._stop:
                next_event = event_queue[0]
                if next_event.time > target_time + eps:
                    break

                heapq.heappop(event_queue)
                processed_bar = next_event.bar_index

                if next_event.event_type == "pause_marker":
                    if self._pause_pending:
                        self.log.emit(
                            f"[Pause] pending at bar {next_event.bar_index} (t={next_event.time:.3f}s)"
                        )
                        self._do_pause()
                        self._release_all_pressed(pressed_keys, fs, chan)
                        paused_now = True
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

                    # Press key
                    if key not in pressed_keys or pressed_keys[key] == 0:
                        self._input_manager.press(key, note)
                        if fs is not None:
                            fs.noteon(chan, note, self.cfg.velocity)
                    pressed_keys[key] = pressed_keys.get(key, 0) + 1

                    # Handle extra note
                    if extra_key is not None:
                        if extra_key not in pressed_keys or pressed_keys[extra_key] == 0:
                            self._input_manager.press(extra_key, extra_note)
                            if fs is not None and extra_note is not None:
                                fs.noteon(chan, extra_note, self.cfg.velocity)
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
                                fs.noteoff(chan, next_event.note)
                            pressed_keys[key] = 0

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
