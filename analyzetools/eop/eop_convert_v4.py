#!/usr/bin/env python
"""
EOP to MIDI Converter - Version 4
Better understanding of format:
- q-{ (lowercase): notes in octave 4 (C4-F5)
- Q-{ (uppercase): notes in octave 5 (C5-F6)
- '4', '8': timing indicators (quarter, eighth notes)
- High bytes (>=0x80): section/beat markers
"""
import sys
sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

# Note mappings - two octaves
LOWER_NOTES = {  # Lowercase = octave 4
    'q': 60, 'r': 62, 's': 64, 't': 65, 'u': 67, 'v': 69, 'w': 71,  # C4-B4
    'x': 72, 'y': 74, 'z': 76, '{': 77,  # C5-F5
}

UPPER_NOTES = {  # Uppercase = octave 5
    'Q': 72, 'R': 74, 'S': 76, 'T': 77, 'U': 79, 'V': 81, 'W': 83,  # C5-B5
    'X': 84, 'Y': 86, 'Z': 88, # C6-E6
}

ALL_NOTES = {**LOWER_NOTES, **UPPER_NOTES}

# Lookup pattern to filter
LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'

def parse_eop_notes(data: bytes):
    """Parse EOP into time-sequenced notes."""
    # Remove lookup patterns
    cleaned = data
    while LOOKUP_PATTERN in cleaned:
        cleaned = cleaned.replace(LOOKUP_PATTERN, b'')

    notes = []
    current_time = 0
    current_duration = 240  # Default: quarter note (480 ticks/beat / 2)

    i = 0
    while i < len(cleaned):
        b = cleaned[i]
        c = chr(b)

        # High byte = advance time (beat marker)
        if b >= 0x80:
            # Different markers might mean different time advances
            if b in (0xF2, 0xE6):  # Most common
                current_time += 60  # 1/8 note
            elif b in (0xF6, 0xE2):
                current_time += 120  # 1/4 note
            else:
                current_time += 30  # 1/16 note

        # Timing indicators
        elif c == '4':
            current_duration = 480  # Quarter note
        elif c == '8':
            current_duration = 240  # Eighth note

        # Note
        elif c in ALL_NOTES:
            notes.append({
                'time': current_time,
                'note': ALL_NOTES[c],
                'duration': current_duration,
            })
            current_time += 15  # Small advance for arpeggios

        i += 1

    return notes

def convert_eop_to_midi(eop_path: str, midi_path: str, bpm: int = 160):
    """Convert EOP to MIDI."""
    print(f"Converting: {eop_path}")

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    # Parse notes
    notes = parse_eop_notes(data)
    print(f"Extracted {len(notes)} notes")

    if not notes:
        print("ERROR: No notes extracted!")
        return None

    # Deduplicate notes at exact same time and pitch
    seen = set()
    unique_notes = []
    for n in notes:
        key = (n['time'], n['note'])
        if key not in seen:
            seen.add(key)
            unique_notes.append(n)

    print(f"After dedup: {len(unique_notes)} notes")
    notes = unique_notes

    # Create MIDI
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    tempo_us = int(60_000_000 / bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    track.append(MetaMessage('track_name', name='Horse Racing (EOP)', time=0))

    # Build events
    events = []
    for n in notes:
        events.append({'time': n['time'], 'type': 'on', 'note': n['note'], 'velocity': 80})
        events.append({'time': n['time'] + n['duration'], 'type': 'off', 'note': n['note']})

    # Sort
    events = sorted(events, key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))

    # Convert to delta
    last_time = 0
    for ev in events:
        delta = max(0, ev['time'] - last_time)
        last_time = ev['time']

        if ev['type'] == 'on':
            track.append(Message('note_on', note=ev['note'], velocity=ev['velocity'], time=delta))
        else:
            track.append(Message('note_off', note=ev['note'], velocity=0, time=delta))

    track.append(MetaMessage('end_of_track', time=0))

    mid.save(midi_path)

    # Calculate duration
    max_time = max(ev['time'] for ev in events)
    duration_s = (max_time / 480) * (60 / bpm)

    print(f"\nSaved: {midi_path}")
    print(f"  Notes: {len(notes)}")
    print(f"  Duration: {duration_s:.1f} seconds ({duration_s/60:.1f} minutes)")

    return mid

if __name__ == "__main__":
    eop_path = r"D:\dw11\.claude\state\sample.eop"
    midi_path = r"D:\dw11\piano\LyreAutoPlayer\赛马_converted.mid"
    convert_eop_to_midi(eop_path, midi_path, bpm=160)
