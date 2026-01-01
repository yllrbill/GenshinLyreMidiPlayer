#!/usr/bin/env python
"""
EOP to MIDI Converter - Final Version
Based on deep analysis of EOP format structure
"""
import sys
import os
import struct

sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

# EOP letter to MIDI note mapping
# Based on EveryonePiano standard keyboard layout
# q-u = C3-B3, s-j = C4-B4 (21-key mode overlapping)
LETTER_TO_MIDI = {
    # Row 1 (q-u) - Octave 4
    'q': 60,  # C4
    'r': 62,  # D4
    's': 64,  # E4
    't': 65,  # F4
    'u': 67,  # G4
    'v': 69,  # A4
    'w': 71,  # B4

    # Row 2 (x-{) - Octave 5
    'x': 72,  # C5
    'y': 74,  # D5
    'z': 76,  # E5
    '{': 77,  # F5
}

def find_song_data_start(data: bytes) -> int:
    """
    Find where the actual song data starts.
    Skip the repeating patterns at the beginning.
    """
    # Look for the first segment marker after header
    # The pattern "qrstrstustuvtuvwuvwxvwxywxyzxyz{" repeats many times
    # Find where the real song data starts

    # Skip first 16 bytes (header)
    i = 16

    # Find the pattern that repeats
    repeat_pattern = bytes([0x71, 0x72, 0x73, 0x74, 0x72, 0x73, 0x74, 0x75,
                           0x73, 0x74, 0x75, 0x76, 0x74, 0x75, 0x76, 0x77,
                           0x75, 0x76, 0x77, 0x78, 0x76, 0x77, 0x78, 0x79,
                           0x77, 0x78, 0x79, 0x7A, 0x78, 0x79, 0x7A, 0x7B])

    # Skip all occurrences of this pattern
    while i < len(data) - len(repeat_pattern):
        if data[i:i+len(repeat_pattern)] == repeat_pattern:
            i += len(repeat_pattern)
        else:
            break

    return i

def parse_eop_segments(data: bytes, start_offset: int = 0) -> list:
    """
    Parse EOP file into segments based on marker bytes.
    Markers: 0xBD, 0xD8, 0xE2, 0xE6, 0xF2, 0xF4, 0xF6, etc.
    """
    markers = {0xBD, 0xD8, 0xE2, 0xE6, 0xF2, 0xF4, 0xF6, 0xDE}
    segments = []
    current_segment = []
    segment_start = start_offset

    for i in range(start_offset, len(data)):
        b = data[i]
        if b in markers:
            if current_segment:
                segments.append({
                    'start': segment_start,
                    'marker': b,
                    'data': bytes(current_segment)
                })
            current_segment = []
            segment_start = i + 1
        else:
            current_segment.append(b)

    # Don't forget last segment
    if current_segment:
        segments.append({
            'start': segment_start,
            'marker': 0,
            'data': bytes(current_segment)
        })

    return segments

def extract_notes_from_segment(segment: dict, time_offset: float) -> list:
    """
    Extract notes from a single segment.
    Returns list of (time, midi_note, duration) tuples.
    """
    notes = []
    data = segment['data']

    # Time increment per note in this segment
    note_count = sum(1 for b in data if chr(b) in LETTER_TO_MIDI)
    if note_count == 0:
        return notes

    # Estimate time for this segment (100ms per beat, adjust as needed)
    segment_duration = 100  # ms per segment
    time_per_note = segment_duration / note_count if note_count > 0 else 0

    current_time = time_offset
    for b in data:
        char = chr(b)
        if char in LETTER_TO_MIDI:
            notes.append({
                'time': current_time,
                'note': LETTER_TO_MIDI[char],
                'duration': 80,
                'velocity': 80,
            })
            current_time += time_per_note

    return notes

def convert_eop_to_midi(eop_path: str, midi_path: str):
    """Convert EOP file to MIDI."""
    print(f"Converting: {eop_path}")

    with open(eop_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    # Find where song data starts
    song_start = find_song_data_start(data)
    print(f"Song data starts at offset: 0x{song_start:04X}")

    # Parse segments
    segments = parse_eop_segments(data, song_start)
    print(f"Found {len(segments)} segments")

    # Extract notes from all segments
    all_notes = []
    time = 0.0
    segment_time = 100.0  # ms per segment (estimated)

    for seg in segments:
        notes = extract_notes_from_segment(seg, time)
        all_notes.extend(notes)
        if notes:
            time = notes[-1]['time'] + 50  # Gap between segments
        else:
            time += segment_time

    print(f"Extracted {len(all_notes)} notes")
    if not all_notes:
        print("ERROR: No notes extracted!")
        return None

    # Create MIDI file
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    # Set tempo (140 BPM for 赛马, a fast piece)
    tempo_bpm = 140
    tempo_us = int(60_000_000 / tempo_bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    track.append(MetaMessage('track_name', name='Horse Racing (EOP)', time=0))

    # Convert time to ticks
    ms_per_tick = (60_000 / tempo_bpm) / 480

    # Build note events
    events = []
    for note in sorted(all_notes, key=lambda x: x['time']):
        time_ticks = int(note['time'] / ms_per_tick)
        dur_ticks = int(note['duration'] / ms_per_tick)

        events.append({'time': time_ticks, 'type': 'on', 'note': note['note'], 'velocity': note['velocity']})
        events.append({'time': time_ticks + dur_ticks, 'type': 'off', 'note': note['note']})

    # Sort by time
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
    duration_s = all_notes[-1]['time'] / 1000 if all_notes else 0
    print(f"Saved MIDI to: {midi_path}")
    print(f"  Notes: {len(all_notes)}")
    print(f"  Duration: {duration_s:.1f} seconds")

    return mid

if __name__ == "__main__":
    eop_path = r"D:\dw11\.claude\state\sample.eop"
    midi_path = r"D:\dw11\piano\LyreAutoPlayer\赛马_converted.mid"
    convert_eop_to_midi(eop_path, midi_path)
