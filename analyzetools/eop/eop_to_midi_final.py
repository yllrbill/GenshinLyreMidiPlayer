#!/usr/bin/env python
"""
EOP to MIDI Converter - Final Version
Best-effort conversion from EveryonePiano .eop format to MIDI.

Note: EOP is a proprietary format without documentation.
This converter produces a playable approximation but may not be
a perfect reproduction of the original.

For best results, download MIDI directly from MuseScore using:
  npx dl-librescore@latest -i "<musescore_url>" -t midi -o "<output_dir>"

Usage:
  python eop_to_midi_final.py <input.eop> [output.mid] [--bpm N]
"""
import sys
import os
import argparse

sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

# Note mappings (EveryonePiano 21-key layout)
NOTES = {
    'q': 60, 'r': 62, 's': 64, 't': 65, 'u': 67, 'v': 69, 'w': 71,  # C4-B4
    'x': 72, 'y': 74, 'z': 76, '{': 77,  # C5-F5
}

# Section markers
MAJOR_MARKERS = {0xE2, 0xE6, 0xF2, 0xF6}

# Lookup table pattern (to filter)
LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'


def parse_eop(data: bytes) -> list:
    """Parse EOP data into note events."""
    # Remove lookup table patterns
    cleaned = data
    while LOOKUP_PATTERN in cleaned:
        cleaned = cleaned.replace(LOOKUP_PATTERN, b'')

    notes = []
    current_time = 0
    beat_ticks = 60  # 1/8 note at 480 tpb

    section_notes = []
    note_bytes = set(ord(c) for c in NOTES.keys())

    for b in cleaned[13:]:  # Skip header
        if b in MAJOR_MARKERS:
            # Process section
            if section_notes:
                # Take first 2 unique notes from section
                seen = set()
                for note in section_notes:
                    if note not in seen and len(seen) < 2:
                        notes.append({
                            'time': current_time + len(seen) * 8,
                            'note': note,
                            'duration': beat_ticks - 10,
                        })
                        seen.add(note)
                current_time += beat_ticks
            section_notes = []
        elif b in note_bytes:
            section_notes.append(NOTES[chr(b)])

    return notes


def create_midi(notes: list, bpm: int = 180) -> MidiFile:
    """Create MIDI file from note events."""
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    tempo_us = int(60_000_000 / bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    track.append(MetaMessage('track_name', name='EOP Conversion', time=0))

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
    return mid


def convert(eop_path: str, midi_path: str = None, bpm: int = 180):
    """Convert EOP file to MIDI."""
    if not midi_path:
        midi_path = os.path.splitext(eop_path)[0] + '.mid'

    print(f"Converting: {eop_path}")
    print(f"Output: {midi_path}")
    print(f"BPM: {bpm}")

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    notes = parse_eop(data)
    print(f"Extracted: {len(notes)} notes")

    if not notes:
        print("ERROR: No notes extracted!")
        return None

    mid = create_midi(notes, bpm)
    mid.save(midi_path)

    duration_s = mid.length
    print(f"\nSaved: {midi_path}")
    print(f"Duration: {duration_s:.1f} seconds ({duration_s/60:.1f} min)")

    return mid


def main():
    parser = argparse.ArgumentParser(description='Convert EOP to MIDI')
    parser.add_argument('input', help='Input .eop file')
    parser.add_argument('output', nargs='?', help='Output .mid file (optional)')
    parser.add_argument('--bpm', type=int, default=180, help='Tempo (default: 180)')
    args = parser.parse_args()

    convert(args.input, args.output, args.bpm)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default: convert sample.eop
        convert(
            r"D:\dw11\.claude\state\sample.eop",
            r"D:\dw11\piano\LyreAutoPlayer\赛马_converted.mid",
            180
        )
    else:
        main()
