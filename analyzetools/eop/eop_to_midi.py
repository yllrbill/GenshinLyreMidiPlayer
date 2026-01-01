#!/usr/bin/env python
"""
EOP to MIDI Converter
Converts EveryonePiano .eop files to standard MIDI format

Based on reverse-engineering of the EOP format:
- EOP uses keyboard letters to represent piano keys
- File structure appears to encode note events sequentially
"""
import sys
import os

# Add mido path
sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")

from mido import Message, MidiFile, MidiTrack, MetaMessage

# EveryonePiano keyboard to MIDI note mapping
# Based on the standard EOP keyboard layout
EOP_KEY_TO_MIDI = {
    # Lower octave (C3-B3)
    '1': 49,  # C#3
    'q': 48,  # C3
    '2': 51,  # D#3
    'w': 50,  # D3
    '3': 0,   # (no E#)
    'e': 52,  # E3
    'r': 53,  # F3
    '5': 54,  # F#3
    't': 55,  # G3
    '6': 56,  # G#3
    'y': 57,  # A3
    '7': 58,  # A#3
    'u': 59,  # B3

    # Middle octave (C4-B4) - Middle C
    '!': 61,  # C#4 (Shift+1)
    'Q': 60,  # C4
    '@': 63,  # D#4 (Shift+2)
    'W': 62,  # D4
    '#': 0,   # (no E#)
    'E': 64,  # E4
    'R': 65,  # F4
    '%': 66,  # F#4 (Shift+5)
    'T': 67,  # G4
    '^': 68,  # G#4 (Shift+6)
    'Y': 69,  # A4
    '&': 70,  # A#4 (Shift+7)
    'U': 71,  # B4

    # Higher octave (C5-B5)
    'i': 72,  # C5
    '9': 73,  # C#5
    'o': 74,  # D5
    '0': 75,  # D#5
    'p': 76,  # E5
    '[': 77,  # F5
    '=': 78,  # F#5
    ']': 79,  # G5

    # Extended keys (based on EOP)
    'a': 60,  # C4 (alternative)
    's': 62,  # D4
    'd': 64,  # E4
    'f': 65,  # F4
    'g': 67,  # G4
    'h': 69,  # A4
    'j': 71,  # B4
    'k': 72,  # C5

    'z': 48,  # C3 (low)
    'x': 50,  # D3
    'c': 52,  # E3
    'v': 53,  # F3
    'b': 55,  # G3
    'n': 57,  # A3
    'm': 59,  # B3

    # Additional mappings based on analysis
    # These appear frequently in the EOP file
    '{': 79,  # G5
}

# Alternative mapping: EOP might use simple sequential byte values
# Based on analysis, bytes 0x71-0x7B (q-{) are most common
# Map them to a 2-octave range
SIMPLE_BYTE_TO_MIDI = {}
for i, val in enumerate(range(0x71, 0x7C)):  # q to {
    # Map to C4 (60) and up
    SIMPLE_BYTE_TO_MIDI[val] = 60 + i

def parse_eop_header(data: bytes) -> dict:
    """Parse EOP file header."""
    header = {
        'magic': data[0:4],
        'version': data[0],
        'flags': data[1:4],
    }
    return header

def extract_notes_simple(data: bytes) -> list:
    """
    Simple extraction: treat each byte in note range as a note event.
    Skip header bytes.
    """
    notes = []
    time = 0
    tick_ms = 100  # 100ms per note (will be adjusted)

    # Skip header (first ~16 bytes seem to be metadata)
    start_offset = 16

    prev_byte = 0
    for i, b in enumerate(data[start_offset:]):
        # Only process bytes that look like note data
        if 0x71 <= b <= 0x7B:  # q to {
            midi_note = SIMPLE_BYTE_TO_MIDI.get(b)
            if midi_note:
                # Check if this is part of a chord (same or adjacent timing)
                if prev_byte and 0x71 <= prev_byte <= 0x7B:
                    # Possibly chord - use same time
                    chord_delay = 5  # 5ms stagger for chord
                else:
                    time += tick_ms

                notes.append({
                    'time': time,
                    'note': midi_note,
                    'duration': 80,  # 80ms default duration
                    'velocity': 80,
                })
        prev_byte = b

    return notes

def extract_notes_structured(data: bytes) -> list:
    """
    Structured extraction: Try to parse as 4-byte records.
    """
    notes = []
    time = 0

    # Skip header
    i = 16

    while i < len(data) - 4:
        b0, b1, b2, b3 = data[i:i+4]

        # Check if this looks like a note event
        if 0x71 <= b0 <= 0x7B:
            midi_note = SIMPLE_BYTE_TO_MIDI.get(b0)
            if midi_note:
                # b1, b2, b3 might be timing/duration info
                # For now, use fixed timing
                notes.append({
                    'time': time,
                    'note': midi_note,
                    'duration': 100,
                    'velocity': 80,
                })
                time += 100
            i += 4
        else:
            # Skip non-note bytes
            i += 1

    return notes

def notes_to_midi(notes: list, output_path: str, tempo_bpm: int = 120):
    """Convert note list to MIDI file."""
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    # Set tempo
    tempo_us = int(60_000_000 / tempo_bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))

    # Track name
    track.append(MetaMessage('track_name', name='EOP Converted', time=0))

    # Convert time to ticks
    ms_per_tick = (60_000 / tempo_bpm) / 480

    # Sort notes by time
    notes = sorted(notes, key=lambda x: x['time'])

    # Build note events
    events = []
    for note in notes:
        time_ticks = int(note['time'] / ms_per_tick)
        dur_ticks = int(note['duration'] / ms_per_tick)

        events.append({
            'time': time_ticks,
            'type': 'on',
            'note': note['note'],
            'velocity': note['velocity'],
        })
        events.append({
            'time': time_ticks + dur_ticks,
            'type': 'off',
            'note': note['note'],
        })

    # Sort by time
    events = sorted(events, key=lambda x: x['time'])

    # Convert to delta times
    last_time = 0
    for ev in events:
        delta = ev['time'] - last_time
        last_time = ev['time']

        if ev['type'] == 'on':
            track.append(Message('note_on', note=ev['note'],
                                velocity=ev['velocity'], time=delta))
        else:
            track.append(Message('note_off', note=ev['note'],
                                velocity=0, time=delta))

    # End of track
    track.append(MetaMessage('end_of_track', time=0))

    # Save
    mid.save(output_path)
    print(f"Saved MIDI to: {output_path}")
    print(f"  Notes: {len(notes)}")
    print(f"  Duration: {notes[-1]['time'] / 1000:.1f} seconds")

    return mid

def analyze_and_convert(eop_path: str, midi_path: str = None):
    """Main conversion function."""
    print(f"Converting: {eop_path}")

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    # Extract notes using simple method
    notes = extract_notes_simple(data)
    print(f"Extracted {len(notes)} notes")

    if not notes:
        print("ERROR: No notes extracted!")
        return None

    # Adjust timing based on note density
    # 赛马 (Horse Racing) is a fast piece, estimate tempo from note count
    total_time_ms = notes[-1]['time']
    estimated_duration_s = 180  # Assume 3 minute piece

    if total_time_ms > estimated_duration_s * 1000:
        # Too slow, compress time
        ratio = (estimated_duration_s * 1000) / total_time_ms
        for note in notes:
            note['time'] = int(note['time'] * ratio)
        print(f"Adjusted timing (ratio: {ratio:.2f})")

    # Output path
    if midi_path is None:
        base = os.path.splitext(eop_path)[0]
        midi_path = base + '.mid'

    # Convert to MIDI
    mid = notes_to_midi(notes, midi_path, tempo_bpm=140)

    return mid

if __name__ == "__main__":
    eop_path = r"D:\dw11\.claude\state\sample.eop"
    midi_path = r"D:\dw11\piano\LyreAutoPlayer\赛马_converted.mid"

    analyze_and_convert(eop_path, midi_path)
