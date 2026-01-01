# -*- coding: utf-8 -*-
"""
Player configuration dataclass.
"""

from dataclasses import dataclass, field
from typing import Optional

from .errors import ErrorConfig
from style_manager import EightBarStyle


@dataclass
class PlayerConfig:
    """Configuration for the PlayerThread."""
    root_mid_do: int = 60
    octave_shift: int = 0  # -2, -1, 0, +1, +2 octaves (×12 semitones)
    transpose: int = 0
    speed: float = 1.0
    accidental_policy: str = "octave"
    octave_min_note: int = 36  # C2
    octave_max_note: int = 84  # C6
    octave_range_auto: bool = False
    press_ms: int = 25
    use_midi_duration: bool = False  # use MIDI note duration
    keyboard_preset: str = "21-key"  # "21-key" or "36-key"
    countdown_sec: int = 2
    target_hwnd: Optional[int] = None
    midi_path: str = ""  # MIDI file path for bar duration calculation

    # Sound settings
    play_sound: bool = False
    soundfont_path: str = ""
    instrument: str = "Piano"
    velocity: int = 90

    # Input style (humanization)
    input_style: str = "mechanical"  # mechanical, natural, expressive, aggressive

    # Error simulation (human-like mistakes)
    error_config: ErrorConfig = field(default_factory=ErrorConfig)

    # Eight-bar style variation
    eight_bar_style: EightBarStyle = field(default_factory=EightBarStyle)

    # Diagnostics (for debugging input issues)
    enable_diagnostics: bool = False
