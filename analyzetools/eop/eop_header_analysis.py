"""
EOP Header Analysis - Find timing parameters

Header hex: 340416060b1c1a10231d14181b (13 bytes)

Hypothesis: Header contains BPM/tempo/delay parameters
"""

import struct

EOP_FILE = r"D:\dw11\.claude\state\sample.eop"

def analyze_header():
    with open(EOP_FILE, 'rb') as f:
        data = f.read()

    header = data[:13]
    print("EOP Header Analysis")
    print("=" * 60)
    print(f"Header (hex): {header.hex()}")
    print(f"Header (dec): {[b for b in header]}")
    print()

    # Individual byte analysis
    print("Individual bytes:")
    for i, b in enumerate(header):
        char = chr(b) if 32 <= b < 127 else '.'
        print(f"  Byte {i:2d}: 0x{b:02X} = {b:3d} = '{char}'")

    print()

    # Try different interpretations
    print("Possible interpretations:")

    # First byte as timing unit
    print(f"\n1) First byte as delay (ms):")
    delay_ms = header[0]
    print(f"   header[0] = {delay_ms}ms per segment")
    print(f"   2253 segments × {delay_ms}ms = {2253 * delay_ms}ms = {2253 * delay_ms / 1000:.1f}s")

    # First 2 bytes as 16-bit delay
    delay_16 = struct.unpack('<H', header[0:2])[0]
    print(f"\n2) First 2 bytes as 16-bit delay (LE): {delay_16}")
    print(f"   If delay = {delay_16}ms per 10 segments: {2253 * delay_16 / 10 / 1000:.1f}s")

    # Look for BPM patterns
    print(f"\n3) BPM interpretations:")
    for i in range(len(header) - 1):
        val = header[i]
        if 30 <= val <= 200:  # Reasonable BPM range
            beat_duration = 60000 / val  # ms per beat
            total_beats = 2253  # if each segment is one beat
            duration = total_beats * beat_duration / 1000
            print(f"   Byte {i} = {val} BPM: {duration:.1f}s for 2253 beats (1 beat/seg)")

            # Try 0.5 beats per segment
            duration_half = total_beats * 0.5 * beat_duration / 1000
            print(f"   Byte {i} = {val} BPM: {duration_half:.1f}s for 2253×0.5 beats")

    # Check for time signature
    print(f"\n4) Time signature check:")
    print(f"   Bytes 0-1: {header[0]}/{header[1]} = {header[0]}/{header[1]}")

    # Look at file size correlation
    file_size = len(data)
    data_size = file_size - 13
    print(f"\n5) File structure:")
    print(f"   Total file size: {file_size} bytes")
    print(f"   Data size: {data_size} bytes")
    print(f"   Header: {13} bytes")

    # Check for patterns in header
    print(f"\n6) Byte differences (header[i+1] - header[i]):")
    for i in range(len(header) - 1):
        diff = header[i+1] - header[i]
        print(f"   {header[i]:3d} -> {header[i+1]:3d}: diff = {diff:+d}")

    # Interpret as note-related data
    print(f"\n7) Note interpretations:")
    print(f"   First byte 0x34 = '4' - could be octave/key indicator")
    print(f"   Second byte 0x04 = 4 - could be time signature numerator")

    # Try to find timing from segment analysis
    print(f"\n8) Reverse engineering from target duration:")
    target_duration = 174  # seconds (2.9 min)
    total_segments = 2253
    ms_per_segment = (target_duration * 1000) / total_segments
    print(f"   Target: {target_duration}s")
    print(f"   Segments: {total_segments}")
    print(f"   Required ms/segment: {ms_per_segment:.1f}ms")
    print(f"   If ticks_per_segment = 10: {ms_per_segment * 10:.1f}ms tick")
    print(f"   If ticks_per_segment = 100: {ms_per_segment * 100:.1f}ms tick")

    # Check if header contains timing tick value
    print(f"\n9) Header value × coefficient analysis:")
    for coeff in [1, 2, 4, 8, 10, 16, 32]:
        for i, b in enumerate(header):
            if b > 0:
                seg_time = b * coeff
                total_time = seg_time * total_segments / 1000
                if 150 < total_time < 200:  # Close to 174s
                    print(f"   header[{i}]={b} × {coeff} = {seg_time}ms/seg → {total_time:.1f}s total !!!")

if __name__ == "__main__":
    analyze_header()
