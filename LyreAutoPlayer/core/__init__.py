# -*- coding: utf-8 -*-
"""
Core module for LyreAutoPlayer.

Contains essential components:
- config: Configuration management
- events: Event bus for publish/subscribe
"""

from .config import ConfigManager, get_config
from .events import EventBus, EventType, get_event_bus
from .constants import (
    SCRIPT_DIR, DEFAULT_SOUNDFONT, SETTINGS_FILE, SETTINGS_MIDI_DIR, SETTINGS_SF_DIR,
    BIN_DIR, setup_dll_path,
    DEFAULT_TEMPO_US, DEFAULT_BPM, DEFAULT_BEAT_DURATION, DEFAULT_BAR_DURATION, DEFAULT_SEGMENT_BARS,
    PRESET_COMBO_ITEMS, DEFAULT_KEYBOARD_PRESET,
    GM_PROGRAM,
    is_admin, get_best_audio_driver,
)

__all__ = [
    'ConfigManager',
    'get_config',
    'EventBus',
    'EventType',
    'get_event_bus',
    # Constants
    'SCRIPT_DIR',
    'DEFAULT_SOUNDFONT',
    'SETTINGS_FILE',
    'SETTINGS_MIDI_DIR',
    'SETTINGS_SF_DIR',
    'BIN_DIR',
    'setup_dll_path',
    'DEFAULT_TEMPO_US',
    'DEFAULT_BPM',
    'DEFAULT_BEAT_DURATION',
    'DEFAULT_BAR_DURATION',
    'DEFAULT_SEGMENT_BARS',
    'PRESET_COMBO_ITEMS',
    'DEFAULT_KEYBOARD_PRESET',
    'GM_PROGRAM',
    'is_admin',
    'get_best_audio_driver',
]
