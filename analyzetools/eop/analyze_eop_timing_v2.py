"""
EOP Timing Analysis V2 - Note Duration Hypothesis

Hypothesis: 0x34 = quarter note (4), 0x38 = eighth note (8)
Markers with 0x34 prefix = quarter note timing
Markers with 0x38 prefix = eighth note timing
"""

import sys
from collections import Counter, defaultdict

EOP_FILE = r"D:\dw11\.claude\state\sample.eop"

NOTES = set(range(0x71, 0x7C)) | set(range(0x51, 0x5B))  # q-{ and Q-Z
MAJOR_MARKERS = {0xE2, 0xE6, 0xF2, 0xF6}
MINOR_MARKERS = {0xBD, 0xD8, 0xDE, 0xF4}
LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'

def read_and_filter(path):
    with open(path, 'rb') as f:
        data = f.read()
    # Filter lookup pattern
    filtered = data[13:]
    while LOOKUP_PATTERN in filtered:
        filtered = filtered.replace(LOOKUP_PATTERN, b'')
    return filtered

def analyze_marker_prefix(data):
    """Analyze bytes before markers"""
    print("=== Marker Prefix Analysis ===")

    prefix_stats = defaultdict(lambda: defaultdict(int))

    for i, b in enumerate(data):
        if b in MAJOR_MARKERS:
            if i >= 2:
                prefix = data[i-2:i]
                prefix_hex = prefix.hex()
                prefix_stats[b][prefix_hex] += 1

    for marker in sorted(MAJOR_MARKERS):
        print(f"\n0x{marker:02X} marker - prefixes:")
        prefixes = prefix_stats[marker]
        for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1])[:10]:
            print(f"  [{prefix}] → 0x{marker:02X}: {count} times")

def analyze_note_timing_structure(data):
    """Analyze structure: note sequences between markers"""
    print("\n=== Note + Timing Structure Analysis ===")

    segments = []
    current_segment = []
    current_timing = None

    for i, b in enumerate(data):
        if b in NOTES:
            current_segment.append(chr(b))
        elif b in MAJOR_MARKERS:
            # Check prefix for timing
            if i >= 1:
                prefix = data[i-1]
                if prefix in [0x34, 0x38, 0x3C, 0x40]:  # 4, 8, <, @
                    current_timing = prefix

            if current_segment:
                segments.append({
                    'notes': current_segment.copy(),
                    'marker': b,
                    'timing': current_timing
                })
                current_segment = []
                current_timing = None

    # Analyze segments
    print(f"\nTotal segments: {len(segments)}")

    timing_34 = [s for s in segments if s['timing'] == 0x34]
    timing_38 = [s for s in segments if s['timing'] == 0x38]

    print(f"Segments with 0x34 prefix: {len(timing_34)}")
    print(f"Segments with 0x38 prefix: {len(timing_38)}")

    # Average notes per segment by timing
    if timing_34:
        avg_34 = sum(len(s['notes']) for s in timing_34) / len(timing_34)
        print(f"  Avg notes/segment (0x34): {avg_34:.1f}")
    if timing_38:
        avg_38 = sum(len(s['notes']) for s in timing_38) / len(timing_38)
        print(f"  Avg notes/segment (0x38): {avg_38:.1f}")

    # Show first 10 segments
    print("\nFirst 20 segments:")
    for i, seg in enumerate(segments[:20]):
        notes = ''.join(seg['notes'][:10])
        if len(seg['notes']) > 10:
            notes += '...'
        timing = f"0x{seg['timing']:02X}" if seg['timing'] else "none"
        marker = f"0x{seg['marker']:02X}"
        print(f"  {i:3d}: [{timing}]{marker} notes={len(seg['notes']):2d} \"{notes}\"")

def analyze_byte_pairs(data):
    """Analyze byte pairs to find timing patterns"""
    print("\n=== Byte Pair Analysis ===")

    pairs = defaultdict(int)
    for i in range(len(data) - 1):
        pair = (data[i], data[i+1])
        pairs[pair] += 1

    # Filter for interesting pairs
    print("Non-note byte + marker pairs:")
    for (b1, b2), count in sorted(pairs.items(), key=lambda x: -x[1]):
        if b2 in MAJOR_MARKERS and b1 not in NOTES:
            print(f"  0x{b1:02X} → 0x{b2:02X}: {count}")
            if count < 10:
                break

    print("\nMarker + non-note byte pairs:")
    for (b1, b2), count in sorted(pairs.items(), key=lambda x: -x[1]):
        if b1 in MAJOR_MARKERS and b2 not in NOTES:
            print(f"  0x{b1:02X} → 0x{b2:02X}: {count}")
            if count < 10:
                break

def calculate_estimated_duration(data):
    """Estimate song duration from timing markers"""
    print("\n=== Duration Estimation ===")

    # Count markers
    marker_counts = {m: data.count(bytes([m])) for m in MAJOR_MARKERS}
    total_markers = sum(marker_counts.values())

    print(f"Marker counts: {marker_counts}")
    print(f"Total major markers: {total_markers}")

    # Hypothesis: Each marker = 1 beat at 120 BPM
    beats_at_120 = total_markers
    duration_at_120 = beats_at_120 / 2  # 120 BPM = 2 beats/sec

    print(f"\nIf each marker = 1 beat:")
    print(f"  At 120 BPM: {duration_at_120:.1f} seconds ({duration_at_120/60:.1f} min)")
    print(f"  At 150 BPM: {total_markers / 2.5:.1f} seconds ({total_markers/2.5/60:.1f} min)")
    print(f"  At 180 BPM: {total_markers / 3:.1f} seconds ({total_markers/3/60:.1f} min)")

    # Target: ~2.9 minutes = 174 seconds
    target_duration = 174
    implied_bpm = total_markers / target_duration * 60
    print(f"\n  To match 2.9 min reference: need {implied_bpm:.0f} BPM")

def main():
    print("EOP Timing Analysis V2")
    print("=" * 60)

    data = read_and_filter(EOP_FILE)
    print(f"Filtered data size: {len(data)} bytes")

    analyze_marker_prefix(data)
    analyze_byte_pairs(data)
    analyze_note_timing_structure(data)
    calculate_estimated_duration(data)

    print("\n=== Analysis Complete ===")

if __name__ == "__main__":
    main()
