# -*- coding: utf-8 -*-
"""
Note quantization strategies.

Handles mapping of MIDI notes to available keyboard keys.
"""

from typing import List, Tuple, Optional

from keyboard_layout import PRESET_21KEY, PRESET_36KEY


# Diatonic scale offsets (C, D, E, F, G, A, B)
DIATONIC_OFFSETS = [0, 2, 4, 5, 7, 9, 11]

# Sharp/black key offsets (C#, D#, F#, G#, A#)
SHARP_OFFSETS = [1, 3, 6, 8, 10]

# MIDI note boundaries for octave shifting
MIDI_C2 = 36
MIDI_C6 = 84


def build_available_notes(root_mid_do: int, preset: str = "21-key") -> List[Tuple[int, str]]:
    """
    Build available notes mapping based on keyboard preset.

    Args:
        root_mid_do: MIDI note number for middle-row Do (C)
        preset: "21-key" for diatonic, "36-key" for chromatic

    Returns:
        List of (midi_note, key) tuples
    """
    avail = []

    if preset == "36-key":
        # 36-key mode: completely different layout
        # Note: In 36-key mode, the octaves are arranged differently:
        #   - high = top octave (QWERTYU + 23567)
        #   - mid = middle octave (ZXCVBNM + SDGHJ)
        #   - low = bottom octave (.,/IOP[ + L;90-)
        for row, octave_shift in [("low", -12), ("mid", 0), ("high", 12)]:
            # Add white keys
            white_keys = PRESET_36KEY[row]
            for i, off in enumerate(DIATONIC_OFFSETS):
                avail.append((root_mid_do + octave_shift + off, white_keys[i].lower()))

            # Add black keys
            black_keys = PRESET_36KEY[f"{row}_sharp"]
            for i, off in enumerate(SHARP_OFFSETS):
                avail.append((root_mid_do + octave_shift + off, black_keys[i].lower()))
    else:
        # 21-key mode: standard QWERTYU/ASDFGHJ/ZXCVBNM layout
        for row, octave_shift in [("low", -12), ("mid", 0), ("high", 12)]:
            white_keys = PRESET_21KEY[row]
            for i, off in enumerate(DIATONIC_OFFSETS):
                avail.append((root_mid_do + octave_shift + off, white_keys[i].lower()))

    return avail


def get_octave_shift(note: int, min_note: Optional[int] = None, max_note: Optional[int] = None) -> Optional[int]:
    """
    Determine octave shift for out-of-range notes.

    Args:
        note: MIDI note number

    Returns:
        Octave shift (+12 or -12) or None if note is in range
    """
    if min_note is not None and max_note is not None:
        if note > max_note:
            return -12
        if note < min_note:
            return 12
        return None
    if note >= MIDI_C6:
        return -12
    if note <= MIDI_C2:
        return 12
    return None


def quantize_note(
    note: int,
    available: List[int],
    policy: str,
    min_note: Optional[int] = None,
    max_note: Optional[int] = None
) -> Optional[int]:
    """
    Quantize a MIDI note to an available note based on policy.

    Args:
        note: MIDI note number
        available: List of available MIDI notes
        policy: Quantization policy:
            - "drop": Drop notes not in available set
            - "lower": Map to nearest lower note
            - "upper": Map to nearest upper note
            - "octave": Shift by octave if out of range

    Returns:
        Quantized MIDI note number or None if dropped
    """
    sorted_av = sorted(available)
    min_av = sorted_av[0]
    max_av = sorted_av[-1]

    if policy == "octave":
        if min_note is None:
            min_note = min_av
        if max_note is None:
            max_note = max_av
        shifted = note
        if shifted < min_note:
            while shifted < min_note:
                shifted += 12
        elif shifted > max_note:
            while shifted > max_note:
                shifted -= 12
        return shifted if shifted in available else None

    if note in available:
        return note

    if policy == "drop":
        return None

    if policy == "lower":
        lowers = [n for n in sorted_av if n <= note]
        return lowers[-1] if lowers else sorted_av[0]

    if policy == "upper":
        uppers = [n for n in sorted_av if n >= note]
        return uppers[0] if uppers else sorted_av[-1]

    return None
