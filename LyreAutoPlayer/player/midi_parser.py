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

    Args:
        mid_path: Path to MIDI file

    Returns:
        List of NoteEvent sorted by time
    """
    mid = mido.MidiFile(mid_path)
    tempo = 500000  # default 120 BPM
    t = 0.0

    # Track active notes: {note: start_time}
    active_notes: Dict[int, float] = {}
    events: List[NoteEvent] = []

    merged = mido.merge_tracks(mid.tracks)
    for msg in merged:
        t += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
        if msg.type == "set_tempo":
            tempo = msg.tempo
        elif msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
            # Note on
            active_notes[msg.note] = t
            events.append(NoteEvent(time=t, note=msg.note, duration=0))
        elif msg.type == "note_off" or (msg.type == "note_on" and getattr(msg, "velocity", 0) == 0):
            # Note off
            note = msg.note
            if note in active_notes:
                start_time = active_notes.pop(note)
                duration = t - start_time
                # Find the event and update duration
                for ev in reversed(events):
                    if ev.note == note and ev.time == start_time:
                        ev.duration = duration
                        break

    events.sort(key=lambda x: x.time)
    return events
