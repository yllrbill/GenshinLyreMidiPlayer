# Acceptance Criteria - Piano Project

> Last verified: 2026-01-01

## EOP to MIDI Conversion

### AC-1: EOP Converter Runs Without Error

**Status**: ✅ PASS

**Command**:
```powershell
d:/dw11/piano/LyreAutoPlayer/.venv/Scripts/python.exe -X utf8 d:/dw11/piano/analyzetools/eop/eop_to_midi_v2.py <input.eop> <output.mid> --duration 174
```

**Verification**:
- Exit code 0
- Output file created
- Console shows segment count and timing

### AC-2: Output Duration Matches Target

**Status**: ✅ PASS

**Expected**: 174s (2.9 min)
**Actual**: 173.0s (2.9 min)
**Tolerance**: ±5s

**Evidence**:
```
Segments: 2214
ms per segment: 78.6
Actual duration: 173.0s
```

### AC-3: Note Count in Expected Range

**Status**: ✅ PASS

**Expected**: 4000-5000 notes
**Actual**: 4428 notes

**Command**:
```python
import mido
m = mido.MidiFile('test_output.mid')
notes = sum(1 for t in m.tracks for msg in t if msg.type=='note_on')
print(f'Notes: {notes}')
```

---

## LyreAutoPlayer

### AC-4: Virtual Environment Dependencies

**Status**: ✅ PASS

**Command**:
```powershell
d:/dw11/piano/LyreAutoPlayer/.venv/Scripts/python.exe -c "import mido; import PyQt6; import pydirectinput; print('OK')"
```

**Expected**: "OK" without errors

### AC-5: GUI Launches

**Status**: ⏳ UNKNOWN (requires manual test)

**Command**:
```powershell
cd d:/dw11/piano/LyreAutoPlayer
.venv\Scripts\python.exe main.py
```

**Expected**: Window appears with controls

---

## Workflow Recommendations

### Preferred: MuseScore Download

For best quality MIDI with proper timing and arrangement:

```powershell
npx dl-librescore@latest -i "<musescore_url>" -t midi -o "<output_dir>"
```

### Fallback: EOP Conversion

When MuseScore version unavailable:

```powershell
# 1. Copy to ASCII path (避免中文文件名问题)
Copy-Item "path/to/song.eop" ".claude/state/sample.eop"

# 2. Convert with V2 converter
python -X utf8 analyzetools/eop/eop_to_midi_v2.py .claude/state/sample.eop output.mid --duration 174
```

---

## Known Pitfalls

| ID | Issue | Workaround |
|----|-------|------------|
| EP-EOP-1 | Lookup pattern counted as notes | Filter `qrstrstustuvtuvwuvwxvwxywxyzxyz{` |
| EP-EOP-2 | Chinese filename in PowerShell | Copy to ASCII path first |
| EP-EOP-3 | Missing per-note timing | Use fixed segment timing |
| EP-EOP-4 | Missing octave info | Map lowercase=C4, uppercase=C5 |

---

## Verification Log

| Date | Verifier | Items | Result |
|------|----------|-------|--------|
| 2026-01-01 | Claude (voteplan) | AC-1, AC-2, AC-3, AC-4 | 4/4 PASS |
