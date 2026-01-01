#!/usr/bin/env python
"""
EOP to MIDI Converter - Version 6
New approach: The scale pattern IS the data.
High bytes between notes encode timing/velocity/control.
"""
import sys
sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

# Note mappings
NOTES = {'q': 60, 'r': 62, 's': 64, 't': 65, 'u': 67, 'v': 69, 'w': 71,
         'x': 72, 'y': 74, 'z': 76, '{': 77}

# Major beat markers (section separators)
MAJOR_MARKERS = {0xE2, 0xE6, 0xF2, 0xF6}

def parse_eop_v6(data: bytes):
    """
    Parse EOP with focus on extracting musical timing.
    Strategy: Use major markers as beat boundaries,
    and take a sampling of notes from each section.
    """
    # Skip header (first ~13 bytes)
    i = 13

    notes = []
    current_time = 0
    beat_duration = 80  # ticks per beat

    section_notes = []

    while i < len(data):
        b = data[i]
        c = chr(b)

        if b in MAJOR_MARKERS:
            # End of section - emit notes
            if section_notes:
                # Sample notes from section (take every 3rd to reduce density)
                sampled = section_notes[::3]
                for j, note in enumerate(sampled[:4]):  # Max 4 notes per beat
                    notes.append({
                        'time': current_time + j * 10,
                        'note': note,
                        'duration': beat_duration - 20,
                    })
                current_time += beat_duration
            section_notes = []

        elif c in NOTES:
            section_notes.append(NOTES[c])

        i += 1

    # Last section
    if section_notes:
        sampled = section_notes[::3]
        for j, note in enumerate(sampled[:4]):
            notes.append({
                'time': current_time + j * 10,
                'note': note,
                'duration': beat_duration - 20,
            })

    return notes

def convert_eop_to_midi(eop_path: str, midi_path: str, bpm: int = 180):
    """Convert EOP to MIDI."""
    print(f"Converting: {eop_path}")

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    notes = parse_eop_v6(data)
    print(f"Extracted {len(notes)} notes")

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

    events = []
    for n in notes:
        events.append({'time': n['time'], 'type': 'on', 'note': n['note'], 'velocity': 80})
        events.append({'time': n['time'] + n['duration'], 'type': 'off', 'note': n['note']})

    events = sorted(events, key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))

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

    max_time = max(ev['time'] for ev in events) if events else 0
    duration_s = (max_time / 480) * (60 / bpm)

    print(f"\nSaved: {midi_path}")
    print(f"  Notes: {len(notes)}")
    print(f"  Duration: {duration_s:.1f} seconds ({duration_s/60:.1f} min)")

    # Show note distribution
    from collections import Counter
    note_dist = Counter(n['note'] for n in notes)
    print("\nNote distribution:")
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    for midi_note in sorted(note_dist.keys()):
        name = note_names[midi_note % 12] + str(midi_note // 12 - 1)
        print(f"  {name}: {note_dist[midi_note]}")

    return mid

if __name__ == "__main__":
    eop_path = r"D:\dw11\.claude\state\sample.eop"
    midi_path = r"D:\dw11\piano\LyreAutoPlayer\赛马_converted.mid"
    convert_eop_to_midi(eop_path, midi_path, bpm=180)
