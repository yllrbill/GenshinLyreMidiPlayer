#!/usr/bin/env python
"""
EOP to MIDI Converter - Version 5
Take only first 2 notes per segment for cleaner output.
"""
import sys
sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

# Note mappings
NOTES = {
    'q': 60, 'r': 62, 's': 64, 't': 65, 'u': 67, 'v': 69, 'w': 71,
    'x': 72, 'y': 74, 'z': 76, '{': 77,
    'Q': 72, 'R': 74, 'S': 76, 'T': 77, 'U': 79, 'V': 81, 'W': 83,
    'X': 84, 'Y': 86, 'Z': 88,
}

NOTE_BYTES = set(ord(c) for c in NOTES.keys())
LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'

def parse_segments(data: bytes) -> list:
    """Parse into segments by high-byte markers."""
    # Remove lookup pattern
    cleaned = data
    while LOOKUP_PATTERN in cleaned:
        cleaned = cleaned.replace(LOOKUP_PATTERN, b'')

    segments = []
    current = []

    for b in cleaned:
        if b >= 0x80:  # Marker
            if current:
                segments.append(bytes(current))
                current = []
        else:
            current.append(b)

    if current:
        segments.append(bytes(current))

    return segments

def extract_notes_from_segments(segments: list, notes_per_segment: int = 2) -> list:
    """Extract limited notes from each segment."""
    notes = []
    current_time = 0
    beat_duration = 120  # ticks per beat (1/4 note at 480 tpb)

    for seg in segments:
        # Get note bytes from this segment
        seg_notes = [chr(b) for b in seg if b in NOTE_BYTES]

        if not seg_notes:
            current_time += beat_duration
            continue

        # Take first N notes only
        for i, note_char in enumerate(seg_notes[:notes_per_segment]):
            if note_char in NOTES:
                notes.append({
                    'time': current_time + (i * 10),  # Small stagger
                    'note': NOTES[note_char],
                    'duration': beat_duration - 10,
                })

        current_time += beat_duration

    return notes

def convert_eop_to_midi(eop_path: str, midi_path: str, bpm: int = 180, notes_per_seg: int = 2):
    """Convert EOP to MIDI."""
    print(f"Converting: {eop_path}")

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    # Parse segments
    segments = parse_segments(data)
    print(f"Found {len(segments)} segments")

    # Extract notes
    notes = extract_notes_from_segments(segments, notes_per_seg)
    print(f"Extracted {len(notes)} notes ({notes_per_seg} per segment max)")

    if not notes:
        print("ERROR: No notes!")
        return None

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

    events = sorted(events, key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))

    # To delta
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

    max_time = max(ev['time'] for ev in events)
    duration_s = (max_time / 480) * (60 / bpm)

    print(f"\nSaved: {midi_path}")
    print(f"  Notes: {len(notes)}")
    print(f"  Duration: {duration_s:.1f} seconds ({duration_s/60:.1f} min)")

    return mid

if __name__ == "__main__":
    eop_path = r"D:\dw11\.claude\state\sample.eop"
    midi_path = r"D:\dw11\piano\LyreAutoPlayer\赛马_converted.mid"

    # Try with just 1 note per segment for minimal output
    convert_eop_to_midi(eop_path, midi_path, bpm=180, notes_per_seg=1)
