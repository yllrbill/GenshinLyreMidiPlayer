"""
EOP Timing Analysis - Casio CSR Methodology
Based on: https://tomerv.github.io/posts/csr2midi/

Hypothesis: EOP uses event + delta time structure like MIDI/CSR
"""

import sys
from collections import Counter

# EOP file
EOP_FILE = r"D:\dw11\.claude\state\sample.eop"

# Known encodings
NOTES_LOWER = {ord(c): 60 + i for i, c in enumerate("qrstuvwxy")}
NOTES_LOWER[ord('z')] = 76
NOTES_LOWER[ord('{')] = 77

NOTES_UPPER = {ord(c): 72 + i for i, c in enumerate("QRSTUVWXY")}
NOTES_UPPER[ord('Z')] = 88

NOTES = {**NOTES_LOWER, **NOTES_UPPER}

MAJOR_MARKERS = {0xE2, 0xE6, 0xF2, 0xF6}  # Beat boundaries
MINOR_MARKERS = {0xBD, 0xD8, 0xDE, 0xF4}  # Sub-beat
ALL_MARKERS = MAJOR_MARKERS | MINOR_MARKERS

LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'

def read_eop(path):
    with open(path, 'rb') as f:
        return f.read()

def analyze_header(data):
    """Analyze first 100 bytes for structure"""
    print("=== Header Analysis (first 100 bytes) ===")
    for i in range(0, min(100, len(data)), 16):
        hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"  {i:04X}: {hex_str:48s}  {ascii_str}")

def find_note_sequences(data):
    """Find sequences of notes and analyze spacing"""
    print("\n=== Note Sequence Analysis ===")

    # Skip header and filter lookup pattern
    filtered = data[13:]
    while LOOKUP_PATTERN in filtered:
        filtered = filtered.replace(LOOKUP_PATTERN, b'')

    print(f"  Original size: {len(data)}, After filtering: {len(filtered) + 13}")

    # Find note positions
    note_positions = []
    for i, b in enumerate(filtered):
        if b in NOTES:
            note_positions.append((i, b, chr(b)))

    print(f"  Found {len(note_positions)} note bytes")

    # Analyze gaps between notes
    if len(note_positions) > 1:
        gaps = []
        for i in range(1, min(50, len(note_positions))):
            pos1, _, char1 = note_positions[i-1]
            pos2, _, char2 = note_positions[i]
            gap = pos2 - pos1
            gaps.append(gap)

            # Show bytes between notes
            between = filtered[pos1+1:pos2]
            between_hex = ' '.join(f'{b:02X}' for b in between)
            print(f"  Note {i-1}: {char1} @ {pos1} -> Note {i}: {char2} @ {pos2}, gap={gap}, between=[{between_hex}]")

        print(f"\n  Gap statistics: min={min(gaps)}, max={max(gaps)}, avg={sum(gaps)/len(gaps):.1f}")
        print(f"  Gap distribution: {Counter(gaps).most_common(10)}")

def analyze_marker_context(data):
    """Analyze bytes before and after markers"""
    print("\n=== Marker Context Analysis ===")

    filtered = data[13:]
    while LOOKUP_PATTERN in filtered:
        filtered = filtered.replace(LOOKUP_PATTERN, b'')

    marker_contexts = {m: [] for m in ALL_MARKERS}

    for i, b in enumerate(filtered):
        if b in ALL_MARKERS:
            # Get context: 3 bytes before, 3 bytes after
            before = filtered[max(0, i-3):i]
            after = filtered[i+1:min(len(filtered), i+4)]

            before_hex = ' '.join(f'{b:02X}' for b in before)
            after_hex = ' '.join(f'{b:02X}' for b in after)

            marker_contexts[b].append({
                'pos': i,
                'before': before,
                'after': after
            })

    for marker, contexts in marker_contexts.items():
        marker_type = "MAJOR" if marker in MAJOR_MARKERS else "minor"
        print(f"\n  0x{marker:02X} ({marker_type}): {len(contexts)} occurrences")

        # Show first 5 examples
        for ctx in contexts[:5]:
            before_hex = ' '.join(f'{b:02X}' for b in ctx['before'])
            after_hex = ' '.join(f'{b:02X}' for b in ctx['after'])
            print(f"    @ {ctx['pos']:5d}: [{before_hex}] | 0x{marker:02X} | [{after_hex}]")

        # Analyze byte after marker
        if contexts:
            bytes_after = [ctx['after'][0] if ctx['after'] else 0 for ctx in contexts]
            print(f"    Byte after marker: {Counter(bytes_after).most_common(5)}")

def look_for_delta_patterns(data):
    """Look for delta time patterns (variable length encoding)"""
    print("\n=== Delta Time Pattern Search ===")

    filtered = data[13:]
    while LOOKUP_PATTERN in filtered:
        filtered = filtered.replace(LOOKUP_PATTERN, b'')

    # Hypothesis 1: Delta time is single byte after marker
    # Hypothesis 2: Delta time is before note (like CSR)
    # Hypothesis 3: Delta time is encoded in marker type itself

    print("  Hypothesis: Different markers = different durations")
    print("  Testing by counting marker types in first 1000 bytes vs last 1000 bytes...")

    first_1k = filtered[:1000]
    last_1k = filtered[-1000:]

    for marker in sorted(ALL_MARKERS):
        first_count = first_1k.count(bytes([marker]))
        last_count = last_1k.count(bytes([marker]))
        print(f"    0x{marker:02X}: first_1k={first_count}, last_1k={last_count}")

def analyze_byte_frequency(data):
    """Analyze byte frequency to find structure"""
    print("\n=== Byte Frequency Analysis ===")

    filtered = data[13:]
    while LOOKUP_PATTERN in filtered:
        filtered = filtered.replace(LOOKUP_PATTERN, b'')

    freq = Counter(filtered)
    print("  Top 20 most common bytes:")
    for byte, count in freq.most_common(20):
        byte_type = ""
        if byte in NOTES:
            byte_type = f"NOTE({chr(byte)})"
        elif byte in MAJOR_MARKERS:
            byte_type = "MAJOR_MARKER"
        elif byte in MINOR_MARKERS:
            byte_type = "minor_marker"
        elif 0x00 <= byte <= 0x1F:
            byte_type = "control"
        elif 0x20 <= byte <= 0x7E:
            byte_type = f"ascii({chr(byte)})"

        print(f"    0x{byte:02X}: {count:5d} ({count/len(filtered)*100:.1f}%)  {byte_type}")

def main():
    print("EOP Timing Analysis")
    print("=" * 60)

    data = read_eop(EOP_FILE)
    print(f"File size: {len(data)} bytes")

    analyze_header(data)
    analyze_byte_frequency(data)
    find_note_sequences(data)
    analyze_marker_context(data)
    look_for_delta_patterns(data)

    print("\n=== Analysis Complete ===")

if __name__ == "__main__":
    main()
