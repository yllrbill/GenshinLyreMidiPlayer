#!/usr/bin/env python
"""
EOP to MIDI Converter - Version 3
Filters out the repeating lookup table pattern before parsing.
"""
import sys
sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

LETTER_TO_MIDI = {
    'q': 60, 'r': 62, 's': 64, 't': 65, 'u': 67, 'v': 69, 'w': 71,  # C4-B4
    'x': 72, 'y': 74, 'z': 76, '{': 77,  # C5-F5
}

MARKERS = {0xBD, 0xD8, 0xDE, 0xE2, 0xE6, 0xF2, 0xF4, 0xF6}

# The repeating lookup table pattern to filter out
LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'

def remove_patterns(data: bytes) -> bytes:
    """Remove all occurrences of the lookup table pattern."""
    result = data
    while LOOKUP_PATTERN in result:
        result = result.replace(LOOKUP_PATTERN, b'')
    return result

def parse_eop_beats(data: bytes) -> list:
    """Parse EOP data into beats, skipping header."""
    # Skip header (first ~13 bytes before notes start)
    # Find first marker or note
    start = 0
    for i in range(min(20, len(data))):
        if data[i] in MARKERS or chr(data[i]) in LETTER_TO_MIDI:
            start = i
            break

    beats = []
    current_notes = []

    for i in range(start, len(data)):
        b = data[i]
        if b in MARKERS:
            if current_notes:
                beats.append(current_notes)
                current_notes = []
        elif chr(b) in LETTER_TO_MIDI:
            current_notes.append(chr(b))

    if current_notes:
        beats.append(current_notes)

    return beats

def convert_eop_to_midi(eop_path: str, midi_path: str, bpm: int = 180):
    """Convert EOP file to MIDI."""
    print(f"Converting: {eop_path}")

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"Original size: {len(data)} bytes")

    # Remove lookup table patterns
    cleaned_data = remove_patterns(data)
    removed = len(data) - len(cleaned_data)
    print(f"After removing lookup patterns: {len(cleaned_data)} bytes (removed {removed})")

    # Parse into beats
    beats = parse_eop_beats(cleaned_data)
    total_notes = sum(len(b) for b in beats)
    print(f"Found {len(beats)} beats, {total_notes} total notes")

    # Create MIDI
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    tempo_us = int(60_000_000 / bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    track.append(MetaMessage('track_name', name='Horse Racing (EOP)', time=0))

    # 1/8 note duration for each beat
    ticks_per_beat = 480 // 2  # 240 ticks = 1/8 note
    note_duration = int(ticks_per_beat * 0.9)

    events = []
    current_time = 0

    for beat_notes in beats:
        if not beat_notes:
            current_time += ticks_per_beat
            continue

        # Slight stagger for chords
        stagger = 3 if len(beat_notes) > 1 else 0

        for idx, note_char in enumerate(beat_notes):
            midi_note = LETTER_TO_MIDI[note_char]
            note_time = current_time + (idx * stagger)

            events.append({'time': note_time, 'type': 'on', 'note': midi_note, 'velocity': 80})
            events.append({'time': note_time + note_duration, 'type': 'off', 'note': midi_note})

        current_time += ticks_per_beat

    # Sort events
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

    mid.save(midi_path)

    duration_s = (current_time / 480) * (60 / bpm)
    print(f"\nSaved: {midi_path}")
    print(f"  Notes: {total_notes}")
    print(f"  Duration: {duration_s:.1f} seconds ({duration_s/60:.1f} minutes)")

    return mid

if __name__ == "__main__":
    eop_path = r"D:\dw11\.claude\state\sample.eop"
    midi_path = r"D:\dw11\piano\LyreAutoPlayer\赛马_converted.mid"
    convert_eop_to_midi(eop_path, midi_path, bpm=180)
