# -*- coding: utf-8 -*-
"""
Bar and beat duration utilities.
"""

from typing import Tuple


def calculate_bar_and_beat_duration(midi_obj) -> Tuple[float, float]:
    """
    Calculate duration of one bar and one beat in seconds based on MIDI tempo and time signature.

    MIDI tempo is always defined as microseconds per quarter note.
    Time signature numerator = beats per bar, denominator = note value that gets one beat.

    Example:
      - 4/4 @ 120 BPM: 4 quarter notes per bar, 0.5s per beat, 2.0s per bar
      - 6/8 @ 120 BPM: 6 eighth notes per bar, 0.25s per beat, 1.5s per bar
      - 3/4 @ 100 BPM: 3 quarter notes per bar, 0.6s per beat, 1.8s per bar

    Args:
        midi_obj: mido.MidiFile object

    Returns:
        Tuple of (bar_duration, beat_duration) in seconds
        Default: (2.0, 0.5) for 4/4 @ 120 BPM
    """
    # Defaults: 4/4 time, 120 BPM
    tempo = 500000  # microseconds per quarter note (120 BPM = 500000 μs/beat)
    numerator = 4   # beats per bar
    denominator = 4  # note value that gets one beat (4 = quarter note)

    for track in midi_obj.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
            elif msg.type == 'time_signature':
                numerator = msg.numerator
                denominator = msg.denominator

    # Tempo is in microseconds per quarter note
    seconds_per_quarter = tempo / 1_000_000.0

    # Calculate beat duration based on denominator
    # denominator=4 means quarter note gets one beat -> beat = seconds_per_quarter
    # denominator=8 means eighth note gets one beat -> beat = seconds_per_quarter / 2
    # denominator=2 means half note gets one beat -> beat = seconds_per_quarter * 2
    # General formula: beat_duration = seconds_per_quarter * (4.0 / denominator)
    beat_duration = seconds_per_quarter * (4.0 / float(denominator))

    # Bar duration = beat_duration * number of beats per bar
    bar_duration = beat_duration * float(numerator)

    return (bar_duration, beat_duration)


def calculate_bar_duration(midi_obj) -> float:
    """
    Legacy wrapper for calculate_bar_and_beat_duration.
    Returns only bar_duration for backward compatibility.
    """
    bar_duration, _ = calculate_bar_and_beat_duration(midi_obj)
    return bar_duration
