# -*- coding: utf-8 -*-
"""
Player module for LyreAutoPlayer.

Contains:
- thread: PlayerThread for playback control
- quantize: Note quantization strategies
- midi_parser: MIDI parsing with duration
- scheduler: Event scheduling with priority queue
"""

from .thread import PlayerThread
from .config import PlayerConfig
from .quantize import (
    quantize_note,
    get_octave_shift,
    build_available_notes,
    DIATONIC_OFFSETS,
    SHARP_OFFSETS,
    MIDI_C2,
    MIDI_C6,
)
from .midi_parser import NoteEvent, midi_to_events_with_duration
from .scheduler import KeyEvent
from .errors import ErrorConfig, ErrorType, DEFAULT_ERROR_TYPES, plan_errors_for_group
from .bar_utils import calculate_bar_and_beat_duration, calculate_bar_duration

__all__ = [
    # Thread
    'PlayerThread',
    # Config
    'PlayerConfig',
    # Quantize
    'quantize_note',
    'get_octave_shift',
    'build_available_notes',
    'DIATONIC_OFFSETS',
    'SHARP_OFFSETS',
    'MIDI_C2',
    'MIDI_C6',
    # MIDI Parser
    'NoteEvent',
    'midi_to_events_with_duration',
    # Scheduler
    'KeyEvent',
    # Errors
    'ErrorConfig',
    'ErrorType',
    'DEFAULT_ERROR_TYPES',
    'plan_errors_for_group',
    # Bar utilities
    'calculate_bar_and_beat_duration',
    'calculate_bar_duration',
]
