#!/usr/bin/env python
"""
EOP to MIDI Converter V2 - Fixed Timing Algorithm

Based on reverse engineering findings:
- 0x34 + E2/F2 = one timing unit
- 0x38 + E6/F6 = one timing unit
- Target: 77ms per segment to match 2.9 min reference

Key insight: EOP doesn't store per-note timing. All segments
have fixed playback speed (controlled by SP+/SP- in EOPmidi.exe).

Usage:
  python eop_to_midi_v2.py <input.eop> [output.mid] [--bpm N]
"""
import sys
import os
import argparse

sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

# Note mappings (EveryonePiano 21-key layout)
# q-z,{ = lower octave (C4-F5)
# Q-Z = upper octave (C5-D#6)
NOTES_LOWER = {
    'q': 60, 'r': 62, 's': 64, 't': 65, 'u': 67, 'v': 69, 'w': 71,
    'x': 72, 'y': 74, 'z': 76, '{': 77,
}
NOTES_UPPER = {
    'Q': 72, 'R': 74, 'S': 76, 'T': 77, 'U': 79, 'V': 81, 'W': 83,
    'X': 84, 'Y': 86, 'Z': 88,
}
NOTES = {**NOTES_LOWER, **NOTES_UPPER}

# Markers
MAJOR_MARKERS = {0xE2, 0xE6, 0xF2, 0xF6}
TIMING_BYTES = {0x34, 0x38}

# Lookup table pattern (to filter)
LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'


def parse_eop_v2(data: bytes) -> tuple:
    """
    Parse EOP data into segments with timing markers.

    Returns:
        segments: list of {'notes': [int], 'timing': 0x34|0x38, 'marker': 0xE2|E6|F2|F6}
        header: first 13 bytes
    """
    header = data[:13]

    # Remove lookup patterns from data
    cleaned = data[13:]
    while LOOKUP_PATTERN in cleaned:
        cleaned = cleaned.replace(LOOKUP_PATTERN, b'')

    note_bytes = set(ord(c) for c in NOTES.keys())
    segments = []
    current_notes = []
    current_timing = 0

    i = 0
    while i < len(cleaned):
        b = cleaned[i]

        if b in note_bytes:
            current_notes.append(NOTES[chr(b)])
        elif b in TIMING_BYTES:
            current_timing = b
        elif b in MAJOR_MARKERS:
            if current_notes:  # Only add if there are notes
                segments.append({
                    'notes': current_notes.copy(),
                    'timing': current_timing,
                    'marker': b,
                })
            current_notes = []
            current_timing = 0

        i += 1

    return segments, header


def create_midi_v2(segments: list, target_duration_s: float = 174.0, velocity: int = 80) -> MidiFile:
    """
    Create MIDI file with fixed timing per segment.

    Args:
        segments: parsed segments from parse_eop_v2
        target_duration_s: target duration in seconds (default 2.9 min)
        velocity: note velocity (0-127)

    Returns:
        MidiFile object
    """
    # Calculate ticks per segment to hit target duration
    # Using 480 ticks per beat and 120 BPM
    ticks_per_beat = 480
    bpm = 120

    # ms per beat = 60000 / BPM = 500ms
    ms_per_beat = 60000 / bpm

    # Target: each segment = target_duration_s / len(segments) seconds
    ms_per_segment = (target_duration_s * 1000) / len(segments)
    ticks_per_segment = int(ms_per_segment / ms_per_beat * ticks_per_beat)

    print(f"Timing calculation:")
    print(f"  Segments: {len(segments)}")
    print(f"  Target duration: {target_duration_s}s ({target_duration_s/60:.1f} min)")
    print(f"  ms per segment: {ms_per_segment:.1f}")
    print(f"  ticks per segment: {ticks_per_segment}")

    # Create MIDI file
    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)

    # Set tempo (120 BPM = 500000 microseconds per beat)
    tempo_us = int(60_000_000 / bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    track.append(MetaMessage('track_name', name='EOP Conversion V2', time=0))

    # Build note events
    events = []
    current_time = 0

    for seg in segments:
        notes = seg['notes']

        # Skip empty segments
        if not notes:
            current_time += ticks_per_segment
            continue

        # Take first 2 unique notes from segment
        seen = set()
        note_offset = 0
        for note in notes:
            if note not in seen and len(seen) < 2:
                # Stagger notes slightly within the segment
                note_time = current_time + note_offset * (ticks_per_segment // 4)

                # Note duration = 90% of segment duration
                note_duration = max(10, ticks_per_segment * 9 // 10)

                events.append({
                    'time': note_time,
                    'type': 'on',
                    'note': note,
                    'velocity': velocity,
                })
                events.append({
                    'time': note_time + note_duration,
                    'type': 'off',
                    'note': note,
                })

                seen.add(note)
                note_offset += 1

        current_time += ticks_per_segment

    # Sort events by time (note_off before note_on at same time)
    events = sorted(events, key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))

    # Convert to MIDI messages with delta times
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


def convert_v2(eop_path: str, midi_path: str = None, target_duration: float = 174.0):
    """Convert EOP file to MIDI with improved timing."""
    if not midi_path:
        midi_path = os.path.splitext(eop_path)[0] + '_v2.mid'

    print("=" * 60)
    print("EOP to MIDI Converter V2")
    print("=" * 60)
    print(f"Input: {eop_path}")
    print(f"Output: {midi_path}")
    print(f"Target duration: {target_duration}s ({target_duration/60:.1f} min)")
    print()

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    segments, header = parse_eop_v2(data)
    print(f"Header: {header.hex()}")
    print(f"Segments: {len(segments)}")

    if not segments:
        print("ERROR: No segments extracted!")
        return None

    # Count timing byte distribution
    timing_34 = sum(1 for s in segments if s['timing'] == 0x34)
    timing_38 = sum(1 for s in segments if s['timing'] == 0x38)
    print(f"Timing bytes: 0x34={timing_34}, 0x38={timing_38}")

    mid = create_midi_v2(segments, target_duration)
    mid.save(midi_path)

    duration_s = mid.length
    print()
    print(f"Saved: {midi_path}")
    print(f"Actual duration: {duration_s:.1f}s ({duration_s/60:.1f} min)")
    print("=" * 60)

    return mid


def main():
    parser = argparse.ArgumentParser(description='Convert EOP to MIDI (V2)')
    parser.add_argument('input', help='Input .eop file')
    parser.add_argument('output', nargs='?', help='Output .mid file (optional)')
    parser.add_argument('--duration', type=float, default=174.0,
                        help='Target duration in seconds (default: 174 = 2.9 min)')
    args = parser.parse_args()

    convert_v2(args.input, args.output, args.duration)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default: convert sample.eop
        convert_v2(
            r"D:\dw11\.claude\state\sample.eop",
            r"D:\dw11\piano\LyreAutoPlayer\赛马_v2.mid",
            174.0  # 2.9 minutes target
        )
    else:
        main()
