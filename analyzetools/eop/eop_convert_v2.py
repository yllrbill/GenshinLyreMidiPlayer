#!/usr/bin/env python
"""
EOP to MIDI Converter - Version 2
Based on deeper analysis of EOP format structure.

Structure discovered:
- Markers (0xBD, 0xD8, 0xDE, 0xE2, 0xE6, 0xF2, 0xF4, 0xF6) separate timing beats
- Note bytes (0x71-0x7B = q-{) represent piano keys
- Some other bytes (like 0x6E = 'n') might be rests or control
"""
import sys
import os
import struct

sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

# EOP letter to MIDI note mapping
# Based on EveryonePiano standard 21-key layout
LETTER_TO_MIDI = {
    # Row 1 (q-w) - Middle octave C4-B4
    'q': 60,  # C4
    'r': 62,  # D4
    's': 64,  # E4
    't': 65,  # F4
    'u': 67,  # G4
    'v': 69,  # A4
    'w': 71,  # B4

    # Row 2 (x-{) - High octave C5-F5
    'x': 72,  # C5
    'y': 74,  # D5
    'z': 76,  # E5
    '{': 77,  # F5
}

# Marker bytes that indicate timing/section boundaries
MARKERS = {0xBD, 0xD8, 0xDE, 0xE2, 0xE6, 0xF2, 0xF4, 0xF6}

def parse_eop_beats(data: bytes) -> list:
    """
    Parse EOP data into beats/measures.
    Each beat contains a list of notes to play.
    """
    beats = []
    current_notes = []

    # Skip header (first 16 bytes or so)
    start = 0

    for i in range(start, len(data)):
        b = data[i]

        if b in MARKERS:
            # End current beat, start new one
            if current_notes:
                beats.append(current_notes)
                current_notes = []
        elif chr(b) in LETTER_TO_MIDI:
            # This is a note
            current_notes.append(chr(b))

    # Don't forget last beat
    if current_notes:
        beats.append(current_notes)

    return beats

def convert_eop_to_midi(eop_path: str, midi_path: str, bpm: int = 140):
    """Convert EOP file to MIDI with proper timing."""
    print(f"Converting: {eop_path}")

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    # Parse into beats
    beats = parse_eop_beats(data)
    print(f"Found {len(beats)} beats/sections")

    # Calculate expected duration
    # 赛马 is about 2-3 minutes at fast tempo
    # If we have ~2300 beats at 140 BPM, that's about 16 minutes - too slow
    # Let's estimate: 2300 beats / 8 beats per measure = 287 measures
    # At 140 BPM, 287 measures = about 8 minutes - still too long

    # Maybe markers aren't every beat - let's group them
    # Try: each marker = 1/16 note
    beat_duration_ms = (60000 / bpm) / 4  # 16th note at 140 BPM = 107ms

    print(f"Beat duration: {beat_duration_ms:.1f}ms (1/16 note at {bpm} BPM)")

    # Create MIDI file
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    # Set tempo
    tempo_us = int(60_000_000 / bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    track.append(MetaMessage('track_name', name='Horse Racing (EOP)', time=0))

    # Convert time to ticks
    ticks_per_ms = 480 / (60000 / bpm)
    beat_ticks = int(beat_duration_ms * ticks_per_ms)
    note_duration_ticks = int(beat_ticks * 0.8)  # 80% of beat duration

    # Build note events
    events = []
    current_time = 0

    for beat_idx, beat_notes in enumerate(beats):
        if not beat_notes:
            current_time += beat_ticks
            continue

        # Add stagger for chords (notes in same beat)
        stagger_ticks = 5 if len(beat_notes) > 1 else 0

        for note_idx, note_char in enumerate(beat_notes):
            midi_note = LETTER_TO_MIDI[note_char]
            note_time = current_time + (note_idx * stagger_ticks)

            events.append({
                'time': note_time,
                'type': 'on',
                'note': midi_note,
                'velocity': 80
            })
            events.append({
                'time': note_time + note_duration_ticks,
                'type': 'off',
                'note': midi_note
            })

        current_time += beat_ticks

    # Sort by time, with note-off before note-on at same time
    events = sorted(events, key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))

    # Convert to delta times
    last_time = 0
    for ev in events:
        delta = max(0, ev['time'] - last_time)
        last_time = ev['time']

        if ev['type'] == 'on':
            track.append(Message('note_on', note=ev['note'], velocity=ev['velocity'], time=delta))
        else:
            track.append(Message('note_off', note=ev['note'], velocity=0, time=delta))

    track.append(MetaMessage('end_of_track', time=0))

    # Save
    mid.save(midi_path)

    total_notes = sum(len(b) for b in beats)
    duration_s = current_time / (ticks_per_ms * 1000)

    print(f"Saved MIDI to: {midi_path}")
    print(f"  Total notes: {total_notes}")
    print(f"  Beats: {len(beats)}")
    print(f"  Duration: {duration_s:.1f} seconds")

    return mid

if __name__ == "__main__":
    eop_path = r"D:\dw11\.claude\state\sample.eop"
    midi_path = r"D:\dw11\piano\LyreAutoPlayer\赛马_converted.mid"
    convert_eop_to_midi(eop_path, midi_path, bpm=200)  # Fast piece
