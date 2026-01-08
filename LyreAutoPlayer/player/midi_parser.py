# -*- coding: utf-8 -*-
"""
MIDI parsing with duration tracking.
"""

from dataclasses import dataclass
from typing import List, Dict

import mido


@dataclass
class NoteEvent:
    """Represents a MIDI note event with duration."""
    time: float       # start time in seconds
    note: int         # MIDI note number
    duration: float   # duration in seconds (0 if unknown)


def midi_to_events_with_duration(mid_path: str) -> List[NoteEvent]:
    """
    Parse MIDI into NoteEvent with duration.
    Tracks note_on/note_off pairs to calculate duration.
    Supports CC64 sustain pedal (延音踏板).

    Args:
        mid_path: Path to MIDI file

    Returns:
        List of NoteEvent sorted by time
    """
    # clip=True: 容错模式，裁剪超范围数据字节到 0..127
    mid = mido.MidiFile(mid_path, clip=True)
    tempo = 500000  # default 120 BPM
    t = 0.0

    # Track active notes: {(note, channel): [(start_time, velocity, bar_duration), ...]}
    active_notes: Dict[tuple, list] = {}
    # Sustained notes (held by pedal): {(note, channel): [(start_time, velocity, bar_duration), ...]}
    sustained_notes: Dict[tuple, list] = {}
    # Sustain pedal state per channel
    sustain_on: Dict[int, bool] = {}
    numerator = 4
    denominator = 4
    events: List[NoteEvent] = []

    def append_note(note: int, start_time: float, end_time: float):
        """Add a note event with duration."""
        duration = max(0, end_time - start_time)
        events.append(NoteEvent(time=start_time, note=note, duration=duration))

    def current_bar_duration() -> float:
        if denominator <= 0:
            return 0.0
        beat_duration = tempo / 1_000_000.0
        beat_duration *= 4 / denominator
        return beat_duration * numerator

    merged = mido.merge_tracks(mid.tracks)
    for msg in merged:
        t += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)

        if msg.type == "set_tempo":
            tempo = msg.tempo
            continue
        if msg.type == "time_signature":
            numerator = msg.numerator
            denominator = msg.denominator
            continue

        # Handle sustain pedal (CC64)
        if msg.type == "control_change" and msg.control == 64:
            channel = getattr(msg, 'channel', 0)
            is_on = msg.value >= 64
            prev_on = sustain_on.get(channel, False)
            sustain_on[channel] = is_on

            # Pedal released: end all sustained notes
            if prev_on and not is_on:
                for key in list(sustained_notes.keys()):
                    if key[1] != channel:
                        continue
                    for start_time, _, _ in sustained_notes[key]:
                        append_note(key[0], start_time, t)
                    del sustained_notes[key]
            continue

        if not hasattr(msg, 'note'):
            continue

        channel = getattr(msg, 'channel', 0)
        key = (msg.note, channel)

        if msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
            # Note on
            if key not in active_notes:
                active_notes[key] = []
            active_notes[key].append((t, msg.velocity, current_bar_duration()))

        elif msg.type == "note_off" or (msg.type == "note_on" and getattr(msg, "velocity", 0) == 0):
            # Note off
            if key in active_notes and active_notes[key]:
                start_time, velocity, bar_duration = active_notes[key].pop(0)  # FIFO
                if sustain_on.get(channel, False):
                    # Pedal is down: delay note end
                    sustained_notes.setdefault(key, []).append((start_time, velocity, bar_duration))
                else:
                    # Normal note end
                    append_note(msg.note, start_time, t)

    # Handle remaining active notes (no note_off received)
    gap_sec = 0.1
    max_bars = 4
    remaining_notes: Dict[tuple, list] = {}
    for key, items in active_notes.items():
        remaining_notes.setdefault(key, []).extend(items)
    for key, items in sustained_notes.items():
        remaining_notes.setdefault(key, []).extend(items)

    for key, items in remaining_notes.items():
        items.sort(key=lambda x: x[0])
        for idx, (start_time, velocity, bar_duration) in enumerate(items):
            next_start_time = items[idx + 1][0] if idx + 1 < len(items) else None
            end_time = t
            if next_start_time is not None:
                end_time = min(end_time, max(0.0, next_start_time - gap_sec))
            if bar_duration > 0:
                end_time = min(end_time, start_time + bar_duration * max_bars)
            if end_time <= start_time:
                end_time = start_time + 0.001
            append_note(key[0], start_time, end_time)

    events.sort(key=lambda x: x.time)
    return events
