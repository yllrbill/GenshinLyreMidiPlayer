#!/usr/bin/env python
"""
EOP File Format Analyzer
Reverse-engineer EveryonePiano's .eop format
"""
import struct
import sys
from collections import Counter
from typing import List, Tuple

def analyze_eop(filepath: str):
    """Analyze EOP file structure."""
    with open(filepath, 'rb') as f:
        data = f.read()

    print(f"=== EOP File Analysis ===")
    print(f"Size: {len(data)} bytes")
    print()

    # Header analysis
    print("Header (first 32 bytes):")
    for i in range(0, 32, 16):
        hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[i:i+16])
        print(f"  {i:04X}: {hex_str}  {ascii_str}")

    # Look for structure
    print()
    print("Potential structure markers:")

    # Find repeating 4-byte patterns
    patterns_4 = Counter()
    for i in range(0, len(data) - 4, 4):
        pattern = data[i:i+4]
        patterns_4[pattern] += 1

    print("  Top 4-byte patterns:")
    for pattern, count in patterns_4.most_common(10):
        hex_str = ' '.join(f'{b:02X}' for b in pattern)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in pattern)
        print(f"    {hex_str} ({ascii_str}): {count} times")

    # Analyze byte distribution by position mod 4
    print()
    print("Byte distribution by position mod 4:")
    for pos in range(4):
        bytes_at_pos = [data[i] for i in range(pos, len(data), 4)]
        top_bytes = Counter(bytes_at_pos).most_common(5)
        top_str = ', '.join(f'{b:02X}({chr(b) if 32<=b<=126 else "."}):{c}' for b, c in top_bytes)
        print(f"  Pos {pos}: {top_str}")

    # Look for note-like patterns
    print()
    print("Potential note mapping analysis:")

    # Count bytes in piano key range (common MIDI: 21-108)
    # But EOP might use different encoding

    # Map ASCII letters that appear frequently
    letter_bytes = [b for b in data if 0x71 <= b <= 0x7B]  # q-{
    letter_freq = Counter(letter_bytes)
    print(f"  Bytes in range 0x71-0x7B (q-{{): {len(letter_bytes)} ({100*len(letter_bytes)/len(data):.1f}%)")
    print("  Distribution:", dict(sorted({chr(b): c for b, c in letter_freq.items()}.items())))

    # Try to decode as note events
    print()
    print("Attempting to decode note events...")

    # Hypothesis: 4-byte records (note, timing, duration, velocity?)
    notes = []
    for i in range(0, len(data) - 4, 4):
        b0, b1, b2, b3 = data[i:i+4]
        # If b0 is in note range
        if 0x30 <= b0 <= 0x7F:
            notes.append((i, b0, b1, b2, b3))

    print(f"  Found {len(notes)} potential note records")
    print("  First 20 records:")
    for i, (offset, n, t1, t2, t3) in enumerate(notes[:20]):
        note_char = chr(n) if 32 <= n <= 126 else '?'
        print(f"    {offset:04X}: note={n:02X}({note_char}) t1={t1:02X} t2={t2:02X} t3={t3:02X}")

    return data

def find_note_mapping(data: bytes) -> dict:
    """Try to find EOP note to MIDI note mapping."""
    # EveryonePiano keyboard layout (assumption):
    # Lower row: z x c v b n m (C3-B3)
    # Middle row: a s d f g h j (C4-B4)
    # Upper row: q w e r t y u (C5-B5)
    # Numbers: 1-7 for black keys

    eop_to_midi = {
        # Based on common layouts
        ord('z'): 48, ord('x'): 50, ord('c'): 52, ord('v'): 53,
        ord('b'): 55, ord('n'): 57, ord('m'): 59,
        ord('a'): 60, ord('s'): 62, ord('d'): 64, ord('f'): 65,
        ord('g'): 67, ord('h'): 69, ord('j'): 71,
        ord('q'): 72, ord('w'): 74, ord('e'): 76, ord('r'): 77,
        ord('t'): 79, ord('y'): 81, ord('u'): 83,
    }

    # Extended mapping for higher notes
    for i, char in enumerate("iop[]"):
        eop_to_midi[ord(char)] = 84 + i * 2

    return eop_to_midi

def try_decode_v1(data: bytes) -> List[Tuple[float, int, float]]:
    """
    Decode attempt 1: Simple sequential notes
    Returns list of (time, midi_note, duration)
    """
    mapping = find_note_mapping(data)
    notes = []
    time = 0.0
    tick = 0.1  # 100ms per note (guess)

    for b in data:
        if b in mapping:
            notes.append((time, mapping[b], 0.2))
            time += tick

    return notes

def try_decode_v2(data: bytes) -> List[Tuple[float, int, float]]:
    """
    Decode attempt 2: 4-byte records
    Format guess: [note_byte, time_offset, duration, unused]
    """
    mapping = find_note_mapping(data)
    notes = []

    i = 0
    while i < len(data) - 4:
        note_byte = data[i]

        if note_byte in mapping:
            # Next bytes might be timing info
            t1 = data[i+1]
            t2 = data[i+2]
            t3 = data[i+3]

            # Decode timing (various attempts)
            time = (t1 << 8 | t2) / 1000.0  # as milliseconds
            duration = t3 / 100.0  # as centiseconds

            notes.append((time, mapping[note_byte], max(0.05, duration)))
            i += 4
        else:
            i += 1

    return notes

if __name__ == "__main__":
    filepath = r"D:\dw11\.claude\state\sample.eop"
    data = analyze_eop(filepath)

    print()
    print("=== Decode Attempts ===")

    # Try decode v1
    notes_v1 = try_decode_v1(data)
    print(f"V1 (sequential): {len(notes_v1)} notes")
    if notes_v1:
        print(f"  First 10: {[(t, n) for t, n, d in notes_v1[:10]]}")

    # Try decode v2
    notes_v2 = try_decode_v2(data)
    print(f"V2 (4-byte records): {len(notes_v2)} notes")
    if notes_v2:
        print(f"  First 10: {notes_v2[:10]}")
