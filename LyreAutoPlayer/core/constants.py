# -*- coding: utf-8 -*-
"""
Constants and utility functions for LyreAutoPlayer.

Contains:
- Path constants
- Timing constants
- Keyboard preset constants
- Admin check helper
- Audio driver selection
"""

import os
import sys
import ctypes

# ---------------- Path Constants ----------------
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOUNDFONT = os.path.join(SCRIPT_DIR, "FluidR3_GM.sf2")

# Application settings file
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "settings.json")
SETTINGS_MIDI_DIR = "last_midi_directory"
SETTINGS_SF_DIR = "last_soundfont_directory"

# Add bin/ to PATH for FluidSynth DLL
BIN_DIR = os.path.join(SCRIPT_DIR, "bin")


def setup_dll_path():
    """Setup DLL path for FluidSynth on Windows."""
    if os.path.isdir(BIN_DIR):
        os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ.get("PATH", "")
        # Python 3.8+ requires explicit DLL directory registration
        if sys.version_info >= (3, 8) and hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(BIN_DIR)


# ---------------- Timing Constants ----------------
DEFAULT_TEMPO_US = 500000       # 默认 tempo (微秒/拍) = 120 BPM
DEFAULT_BPM = 120               # 默认 BPM
DEFAULT_BEAT_DURATION = 0.5     # 默认拍时长 (秒) = 60/120
DEFAULT_BAR_DURATION = 2.0      # 默认小节时长 (秒) = 4拍 * 0.5秒
DEFAULT_SEGMENT_BARS = 8        # 8小节为一段


# ---------------- Keyboard Presets ----------------
PRESET_COMBO_ITEMS = [
    ("21-key (21键)", "21-key"),
    ("36-key (36键)", "36-key"),
]
DEFAULT_KEYBOARD_PRESET = "21-key"


# ---------------- GM Program Numbers ----------------
GM_PROGRAM = {
    "Piano": 1,           # Acoustic Grand Piano
    "Harpsichord": 7,     # Harpsichord
    "Organ": 20,          # Church Organ
    "Celesta": 9,         # Celesta (钢片琴)
    "Harp": 47,           # Harp (竖琴)
}


# ---------------- Utility Functions ----------------

def is_admin() -> bool:
    """Check if running with administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def get_best_audio_driver() -> str:
    """Get the best audio driver for the current platform."""
    if sys.platform == 'win32':
        return 'dsound'  # DirectSound is most reliable on Windows
    elif sys.platform == 'darwin':
        return 'coreaudio'
    else:
        return 'pulseaudio'


__all__ = [
    # Path constants
    'SCRIPT_DIR',
    'DEFAULT_SOUNDFONT',
    'SETTINGS_FILE',
    'SETTINGS_MIDI_DIR',
    'SETTINGS_SF_DIR',
    'BIN_DIR',
    'setup_dll_path',
    # Timing constants
    'DEFAULT_TEMPO_US',
    'DEFAULT_BPM',
    'DEFAULT_BEAT_DURATION',
    'DEFAULT_BAR_DURATION',
    'DEFAULT_SEGMENT_BARS',
    # Keyboard presets
    'PRESET_COMBO_ITEMS',
    'DEFAULT_KEYBOARD_PRESET',
    # GM program
    'GM_PROGRAM',
    # Utility functions
    'is_admin',
    'get_best_audio_driver',
]
