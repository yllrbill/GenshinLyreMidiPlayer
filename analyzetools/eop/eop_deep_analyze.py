#!/usr/bin/env python
"""
Deep analysis of EOP file structure
"""
import struct

def analyze_deep(filepath: str):
    with open(filepath, 'rb') as f:
        data = f.read()

    print(f"=== Deep EOP Analysis ===")
    print(f"Size: {len(data)} bytes")

    # Look for structure in first 256 bytes
    print("\n--- First 256 bytes (hex dump) ---")
    for i in range(0, min(256, len(data)), 16):
        hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[i:i+16])
        print(f"{i:04X}: {hex_str}  {ascii_str}")

    # Look for potential length fields
    print("\n--- Potential length/offset fields ---")
    for i in range(0, min(64, len(data) - 4), 2):
        # Little-endian 16-bit
        val16 = struct.unpack_from('<H', data, i)[0]
        # Little-endian 32-bit
        if i < len(data) - 4:
            val32 = struct.unpack_from('<I', data, i)[0]
            if 100 < val16 < 50000 or 100 < val32 < 50000:
                print(f"  Offset {i:04X}: u16={val16}, u32={val32}")

    # Look for repeating section markers
    print("\n--- Section markers (non-letter bytes before letter sequences) ---")
    in_letter_seq = False
    marker_count = 0
    for i in range(len(data) - 1):
        is_letter = 0x71 <= data[i] <= 0x7B
        next_is_letter = 0x71 <= data[i+1] <= 0x7B

        if not is_letter and next_is_letter and not in_letter_seq:
            marker_count += 1
            if marker_count <= 30:
                context_before = data[max(0,i-3):i+1]
                context_after = data[i+1:min(len(data), i+9)]
                print(f"  {i:04X}: marker={data[i]:02X} -> {' '.join(f'{b:02X}' for b in context_after)}")
            in_letter_seq = True
        elif not is_letter:
            in_letter_seq = False

    print(f"  Total markers: {marker_count}")

    # Analyze byte sequences between markers
    print("\n--- Analyzing structure between E6/F2/F6/E2 markers ---")
    special_bytes = [0xE6, 0xF2, 0xF6, 0xE2, 0xD8, 0xBD, 0xF4, 0xDE]
    segments = []
    current_segment = []
    last_special = -1

    for i, b in enumerate(data):
        if b in special_bytes:
            if current_segment:
                segments.append({
                    'start': last_special + 1,
                    'end': i,
                    'length': i - last_special - 1,
                    'marker': b,
                    'data': bytes(current_segment)
                })
            current_segment = []
            last_special = i
        else:
            current_segment.append(b)

    print(f"  Found {len(segments)} segments")
    if segments:
        lengths = [s['length'] for s in segments]
        print(f"  Segment lengths: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)/len(lengths):.1f}")

        # Check if segments have consistent structure
        print("\n  First 10 segments:")
        for i, seg in enumerate(segments[:10]):
            marker = f"{seg['marker']:02X}"
            content = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in seg['data'][:20])
            print(f"    {i}: marker=0x{marker}, len={seg['length']}, content='{content}'")

    # Look for timing information
    print("\n--- Looking for timing bytes ---")
    # EOP might encode timing as:
    # - Relative delays
    # - Absolute timestamps
    # - Beat/measure positions

    # Count non-letter bytes (potential timing/control data)
    non_letter = [b for b in data if not (0x71 <= b <= 0x7B)]
    print(f"  Non-letter bytes: {len(non_letter)} ({100*len(non_letter)/len(data):.1f}%)")

    # Common non-letter values
    from collections import Counter
    non_letter_freq = Counter(non_letter).most_common(20)
    print("  Top non-letter bytes:")
    for b, c in non_letter_freq:
        print(f"    0x{b:02X}: {c} times")

if __name__ == "__main__":
    analyze_deep(r"D:\dw11\.claude\state\sample.eop")
