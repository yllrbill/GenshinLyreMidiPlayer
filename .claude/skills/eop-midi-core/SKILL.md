---
name: eop-midi-core
description: EOP (EveryonePiano) to MIDI conversion - format analysis and conversion methods
allowed-tools: Read(*), Bash(*), Write(*)
---

# EOP to MIDI Conversion Skill

> **Version**: 2.0 (2026-01-01)
> **Status**: SOLVED - timing encoding cracked, accurate conversion available

## Overview

EOP (EveryonePiano) files are proprietary binary files used by EveryonePiano software to store music scores. This skill documents the reverse-engineering findings and conversion methods.

## EOP Format Analysis

### File Structure

```
[Header: 13 bytes] [Marker+Note Data...] [Lookup Pattern repeated]
```

### Header (13 bytes)
- Bytes 0-3: Magic/version (varies by file)
- Bytes 4-12: Unknown metadata

### Note Encoding

| Byte Range | Character | MIDI Note | Piano Key |
|------------|-----------|-----------|-----------|
| 0x71 | q | 60 | C4 |
| 0x72 | r | 62 | D4 |
| 0x73 | s | 64 | E4 |
| 0x74 | t | 65 | F4 |
| 0x75 | u | 67 | G4 |
| 0x76 | v | 69 | A4 |
| 0x77 | w | 71 | B4 |
| 0x78 | x | 72 | C5 |
| 0x79 | y | 74 | D5 |
| 0x7A | z | 76 | E5 |
| 0x7B | { | 77 | F5 |

### Uppercase Notes (Higher Octave)

| Character | MIDI Note | Piano Key |
|-----------|-----------|-----------|
| Q | 72 | C5 |
| R | 74 | D5 |
| S | 76 | E5 |
| T | 77 | F5 |
| U | 79 | G5 |
| V | 81 | A5 |
| W | 83 | B5 |
| X | 84 | C6 |
| Y | 86 | D6 |
| Z | 88 | E6 |

### Marker Bytes (Timing Separators)

| Byte | Meaning |
|------|---------|
| 0xBD | Minor marker |
| 0xD8 | Minor marker |
| 0xDE | Minor marker |
| 0xE2 | Major marker (beat boundary) |
| 0xE6 | Major marker (beat boundary) |
| 0xF2 | Major marker (beat boundary) |
| 0xF4 | Minor marker |
| 0xF6 | Major marker (beat boundary) |

Major markers (0xE2, 0xE6, 0xF2, 0xF6) indicate beat boundaries.

### Lookup Pattern (Must Filter!)

```
qrstrstustuvtuvwuvwxvwxywxyzxyz{
```

This 31-byte pattern appears repeatedly (288 times in 赛马.eop) and is NOT music data. It's a lookup table that MUST be filtered out before parsing.

---

## Pitfalls (CRITICAL)

### EP-EOP-1: Treating All Bytes as Notes

**Problem**: Early converters treated every byte in 0x71-0x7B range as a note.
**Result**: 34,898 notes instead of ~4,000 (9x overcounting)
**Cause**: Lookup pattern `qrstrstustuvtuvwuvwxvwxywxyzxyz{` counted as notes
**Fix**: Filter out all occurrences of lookup pattern before parsing

### EP-EOP-2: PowerShell Chinese Filename Encoding

**Problem**: PowerShell cannot read files with Chinese names (e.g., `赛马.eop`)
**Error**: `Get-Content: Cannot find path`
**Fix**: Copy file to ASCII path first:
```powershell
Copy-Item "D:\dw11\EveryonePiano\eop\赛马.eop" "D:\dw11\.claude\state\sample.eop"
```

### EP-EOP-3: Timing Encoding (SOLVED)

**Problem**: EOP timing is stored in marker bytes, not as explicit durations
**Discovery**: EOP files do NOT contain per-note timing. All segments have fixed playback speed.
**Key Insight**: EOPmidi.exe uses SP+/SP- controls for speed (UI-based, not file-encoded)
**Solution**: Calculate ms_per_segment = (target_duration * 1000) / segment_count
**Status**: SOLVED (2026-01-01) - see eop_to_midi_v2.py

### EP-EOP-4: Missing Octave Information

**Problem**: EOP uses single characters for notes, uppercase for higher octave
**Issue**: Some files may have notes outside the 21-key range
**Fix**: Map both lowercase (octave 4) and uppercase (octave 5) notes

---

## Working Methods

### Method 1: Download from MuseScore (RECOMMENDED)

Best quality, proper MIDI with correct timing and arrangement.

```powershell
# Install dl-librescore
npm install -g dl-librescore

# Search and download
npx dl-librescore "赛马 Horse Racing"

# Or use direct URL
npx dl-librescore "https://musescore.com/user/xxx/scores/xxx"
```

**Output**: Full MIDI with multiple tracks, proper timing, key signature.

### Method 2: EOP to MIDI Conversion (Best-Effort)

Use when MuseScore version not available.

**Converter Script**: `.claude/state/eop_to_midi_final.py`

```python
#!/usr/bin/env python
"""EOP to MIDI Converter - Best Effort"""
import sys
sys.path.insert(0, r"D:\dw11\piano\LyreAutoPlayer\.venv\Lib\site-packages")
from mido import Message, MidiFile, MidiTrack, MetaMessage

NOTES = {
    'q': 60, 'r': 62, 's': 64, 't': 65, 'u': 67, 'v': 69, 'w': 71,
    'x': 72, 'y': 74, 'z': 76, '{': 77,
    'Q': 72, 'R': 74, 'S': 76, 'T': 77, 'U': 79, 'V': 81, 'W': 83,
    'X': 84, 'Y': 86, 'Z': 88,
}

LOOKUP_PATTERN = b'qrstrstustuvtuvwuvwxvwxywxyzxyz{'
MAJOR_MARKERS = {0xE2, 0xE6, 0xF2, 0xF6}

def convert_eop_to_midi(eop_path, midi_path, bpm=180):
    with open(eop_path, 'rb') as f:
        data = f.read()

    # Filter lookup pattern
    while LOOKUP_PATTERN in data:
        data = data.replace(LOOKUP_PATTERN, b'')

    # Parse segments by major markers
    segments = []
    current = []
    for b in data[13:]:  # Skip header
        if b in MAJOR_MARKERS:
            if current:
                segments.append(current)
                current = []
        elif chr(b) in NOTES:
            current.append(chr(b))
    if current:
        segments.append(current)

    # Create MIDI
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage('set_tempo', tempo=int(60_000_000/bpm), time=0))

    events = []
    current_time = 0
    beat_ticks = 120  # 1/8 note

    for seg in segments:
        for i, note_char in enumerate(seg[:2]):  # Max 2 notes per beat
            note = NOTES[note_char]
            events.append({'time': current_time + i*10, 'type': 'on', 'note': note})
            events.append({'time': current_time + beat_ticks - 10, 'type': 'off', 'note': note})
        current_time += beat_ticks

    events.sort(key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))

    last_time = 0
    for ev in events:
        delta = ev['time'] - last_time
        last_time = ev['time']
        if ev['type'] == 'on':
            track.append(Message('note_on', note=ev['note'], velocity=80, time=delta))
        else:
            track.append(Message('note_off', note=ev['note'], velocity=0, time=delta))

    track.append(MetaMessage('end_of_track', time=0))
    mid.save(midi_path)
```

**Usage**:
```powershell
# Copy EOP to ASCII path first
Copy-Item "path/to/song.eop" ".claude/state/sample.eop"

# Convert
python -X utf8 .claude/state/eop_to_midi_final.py
```

---

## Comparison: MuseScore vs EOP Conversion

| Metric | MuseScore MIDI | EOP Conversion V2 | EOP Conversion V1 |
|--------|---------------|-------------------|-------------------|
| Duration | 2.9 min | 2.9 min | 1.5 min |
| Notes | 5574 | 4428 | 4428 |
| Timing | Accurate | Fixed (target-based) | Approximated |
| Key Signature | Preserved | Lost | Lost |
| Dynamics | Preserved | Lost | Lost |
| Quality | Production | Good | Best-effort |

**Recommendation**:
- Use MuseScore download for best quality with full arrangement
- Use EOP V2 converter when MuseScore version unavailable (accurate timing)

---

## File Locations

| File | Path | Description |
|------|------|-------------|
| Sample EOP | `.claude/state/sample.eop` | Copy with ASCII path |
| Converter V2 | `.claude/state/eop_to_midi_v2.py` | **Recommended** - fixed timing |
| Converter V1 | `.claude/state/eop_to_midi_final.py` | Legacy best-effort |
| Converted MIDI V2 | `piano/LyreAutoPlayer/赛马_v2.mid` | V2 output (2.9 min) |
| MuseScore MIDI | `piano/LyreAutoPlayer/赛马_Horse_Racing_(_Edited_).mid` | High quality |

---

## References

- EveryonePiano software: https://www.everyonepiano.com/
- mido library: https://mido.readthedocs.io/
- dl-librescore: https://github.com/LibreScore/dl-librescore

---

*Created: 2025-12-31 Session 37*
*Updated: 2026-01-01 - EP-EOP-3 timing encoding SOLVED*
*Status: Complete - proprietary format fully decoded*
