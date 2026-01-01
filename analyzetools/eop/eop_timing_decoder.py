"""
EOP Timing Decoder - Hypothesis Testing

Based on IDA + byte analysis findings:
- Pattern: [notes...][0x34|0x38][0xE2|0xE6|0xF2|0xF6]
- 0x34 ('4') appears before 0xE2/0xF2
- 0x38 ('8') appears before 0xE6/0xF6

Hypothesis 1: 0x34 = quarter note, 0x38 = eighth note
Hypothesis 2: Marker pairs encode timing (E2+E6 vs F2+F6)
Hypothesis 3: Timing is beat-based (120 BPM default)
"""

import sys
from collections import Counter
from dataclasses import dataclass

EOP_FILE = r"D:\dw11\.claude\state\sample.eop"
LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'

# Known byte classes
NOTES_LOWER = set(range(ord('q'), ord('{') + 1))  # q-{
NOTES_UPPER = set(range(ord('Q'), ord('Z') + 1))  # Q-Z
NOTES = NOTES_LOWER | NOTES_UPPER

MARKERS_MAJOR = {0xE2, 0xE6, 0xF2, 0xF6}
MARKERS_MINOR = {0xBD, 0xD8, 0xDE, 0xF4}
ALL_MARKERS = MARKERS_MAJOR | MARKERS_MINOR

TIMING_BYTES = {0x34, 0x38}  # '4' and '8'

@dataclass
class Segment:
    notes: list
    timing_byte: int
    marker_byte: int
    start_pos: int
    end_pos: int

def read_and_filter(path):
    with open(path, 'rb') as f:
        data = f.read()

    # Skip header (13 bytes)
    filtered = data[13:]

    # Remove lookup patterns
    while LOOKUP_PATTERN in filtered:
        filtered = filtered.replace(LOOKUP_PATTERN, b'')

    return data[:13], filtered

def parse_segments(data):
    """Parse EOP data into segments with timing markers"""
    segments = []
    current_notes = []
    current_start = 0
    i = 0

    while i < len(data):
        byte = data[i]

        if byte in NOTES:
            if not current_notes:
                current_start = i
            current_notes.append(chr(byte))

        elif byte in MARKERS_MAJOR:
            # Check for timing byte before marker
            timing_byte = 0
            if i > 0 and data[i-1] in TIMING_BYTES:
                timing_byte = data[i-1]
                # Remove timing byte from notes if it was added
                if current_notes and current_notes[-1] == chr(timing_byte):
                    current_notes.pop()

            segment = Segment(
                notes=current_notes.copy(),
                timing_byte=timing_byte,
                marker_byte=byte,
                start_pos=current_start,
                end_pos=i
            )
            segments.append(segment)
            current_notes = []

        i += 1

    return segments

def analyze_timing_patterns(segments):
    """Analyze timing patterns in segments"""
    print("=" * 60)
    print("TIMING PATTERN ANALYSIS")
    print("=" * 60)

    # Group by timing+marker combination
    combos = Counter()
    for seg in segments:
        key = (seg.timing_byte, seg.marker_byte)
        combos[key] += 1

    print("\nTiming + Marker combinations:")
    for (timing, marker), count in sorted(combos.items()):
        timing_str = f"0x{timing:02X}" if timing else "none"
        print(f"  {timing_str} + 0x{marker:02X}: {count} segments")

    # Analyze segment properties by timing type
    print("\nSegment properties by timing byte:")
    for timing in [0x34, 0x38]:
        segs = [s for s in segments if s.timing_byte == timing]
        if segs:
            avg_notes = sum(len(s.notes) for s in segs) / len(segs)
            note_counts = Counter(len(s.notes) for s in segs)
            print(f"\n  0x{timing:02X} ({len(segs)} segments):")
            print(f"    Avg notes/segment: {avg_notes:.1f}")
            print(f"    Note count distribution: {note_counts.most_common(5)}")

def calculate_duration(segments, bpm, quarter_ticks=1, eighth_ticks=0.5):
    """Calculate total duration with given BPM and tick values"""
    # Each quarter note tick = 60/BPM seconds
    beat_duration = 60 / bpm

    total_ticks = 0
    for seg in segments:
        if seg.timing_byte == 0x34:  # Quarter note marker
            total_ticks += quarter_ticks
        elif seg.timing_byte == 0x38:  # Eighth note marker
            total_ticks += eighth_ticks
        else:
            total_ticks += quarter_ticks  # Default to quarter

    total_seconds = total_ticks * beat_duration
    return total_seconds

def test_hypotheses(segments):
    """Test different timing hypotheses"""
    print("\n" + "=" * 60)
    print("HYPOTHESIS TESTING")
    print("=" * 60)

    reference_duration = 2.9 * 60  # 2.9 minutes in seconds

    # Count segments by timing byte
    timing_34 = len([s for s in segments if s.timing_byte == 0x34])
    timing_38 = len([s for s in segments if s.timing_byte == 0x38])
    timing_none = len([s for s in segments if s.timing_byte == 0])

    print(f"\nSegment counts:")
    print(f"  0x34 (quarter?): {timing_34}")
    print(f"  0x38 (eighth?): {timing_38}")
    print(f"  No timing: {timing_none}")

    print(f"\nTarget duration: {reference_duration:.0f}s ({reference_duration/60:.1f} min)")

    # Hypothesis 1: 0x34 = 1 beat, 0x38 = 0.5 beat
    print("\n--- Hypothesis 1: 0x34=1beat, 0x38=0.5beat ---")
    for bpm in [60, 90, 120, 140, 160, 180, 200]:
        duration = calculate_duration(segments, bpm, quarter_ticks=1, eighth_ticks=0.5)
        match = "<<< MATCH" if abs(duration - reference_duration) < 30 else ""
        print(f"  {bpm:3d} BPM: {duration:6.1f}s ({duration/60:.1f} min) {match}")

    # Hypothesis 2: Inverse - 0x38 = 1 beat, 0x34 = 0.5 beat
    print("\n--- Hypothesis 2: 0x34=0.5beat, 0x38=1beat ---")
    for bpm in [60, 90, 120, 140, 160, 180, 200]:
        duration = calculate_duration(segments, bpm, quarter_ticks=0.5, eighth_ticks=1)
        match = "<<< MATCH" if abs(duration - reference_duration) < 30 else ""
        print(f"  {bpm:3d} BPM: {duration:6.1f}s ({duration/60:.1f} min) {match}")

    # Hypothesis 3: All markers are equal beats
    print("\n--- Hypothesis 3: All markers = 1 beat ---")
    total_markers = len(segments)
    for bpm in [60, 90, 120, 140, 160, 180, 200, 300, 400, 500]:
        duration = total_markers * (60 / bpm)
        match = "<<< MATCH" if abs(duration - reference_duration) < 30 else ""
        print(f"  {bpm:3d} BPM: {duration:6.1f}s ({duration/60:.1f} min) {match}")

    # Find optimal BPM for hypothesis 3
    optimal_bpm = total_markers * 60 / reference_duration
    print(f"\n  Optimal BPM for 2.9 min: {optimal_bpm:.0f}")

    # Hypothesis 4: Marker byte itself encodes timing multiplier
    print("\n--- Hypothesis 4: Marker-specific timing ---")
    marker_values = {
        0xE2: 0.25,  # Quarter beat
        0xE6: 0.5,   # Half beat
        0xF2: 0.25,  # Quarter beat
        0xF6: 0.5,   # Half beat
    }
    print(f"  E2/F2 = 0.25 beat, E6/F6 = 0.5 beat")
    for bpm in [60, 90, 120, 140, 160]:
        total_beats = sum(marker_values.get(s.marker_byte, 0.25) for s in segments)
        duration = total_beats * (60 / bpm)
        match = "<<< MATCH" if abs(duration - reference_duration) < 30 else ""
        print(f"  {bpm:3d} BPM: {duration:6.1f}s ({duration/60:.1f} min) [beats={total_beats:.0f}] {match}")

def dump_first_segments(segments, count=30):
    """Dump first N segments for inspection"""
    print("\n" + "=" * 60)
    print(f"FIRST {count} SEGMENTS")
    print("=" * 60)

    for i, seg in enumerate(segments[:count]):
        notes_str = ''.join(seg.notes[:8])
        if len(seg.notes) > 8:
            notes_str += '...'

        timing_str = f"0x{seg.timing_byte:02X}" if seg.timing_byte else "----"
        marker_str = f"0x{seg.marker_byte:02X}"

        print(f"  {i:3d}: [{timing_str}]{marker_str} notes={len(seg.notes):2d} \"{notes_str}\"")

def main():
    print("EOP Timing Decoder")
    print("=" * 60)

    header, data = read_and_filter(EOP_FILE)
    print(f"Header: {len(header)} bytes")
    print(f"Data (filtered): {len(data)} bytes")

    print(f"\nHeader hex: {header.hex()}")

    segments = parse_segments(data)
    print(f"\nParsed {len(segments)} segments")

    analyze_timing_patterns(segments)
    test_hypotheses(segments)
    dump_first_segments(segments)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
