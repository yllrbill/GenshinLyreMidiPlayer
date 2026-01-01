# Clean up duplicated constants in main.py
$file = "d:\dw11\piano\LyreAutoPlayer\main.py"
$content = Get-Content -Path $file -Raw

# Pattern to remove: from line 119 to line 171
# We'll replace everything from "# Determine best audio driver" to "# FloatingController moved"
$pattern = @"
# Determine best audio driver for FluidSynth on Windows
def get_best_audio_driver\(\) -> str:
    """Get the best audio driver for the current platform."""
    if sys.platform == 'win32':
        return 'dsound'  # DirectSound is most reliable on Windows
    elif sys.platform == 'darwin':
        return 'coreaudio'
    else:
        return 'pulseaudio'

# GM Program numbers \(1-based\)
GM_PROGRAM = \{
    "Piano": 1,           # Acoustic Grand Piano
    "Harpsichord": 7,     # Harpsichord \(缇界閿惔/绠″鸡鐞\?
    "Organ": 20,          # Church Organ
    "Celesta": 9,         # Celesta \(钢片琴\)
    "Harp": 47,           # Harp \(竖琴\)
\}

# ---------------- i18n ----------------
# NOTE: Translations moved to i18n/ module\. Import: from i18n import tr, LANG_EN, LANG_ZH


# ---------------- Timing Constants ----------------
DEFAULT_TEMPO_US = 500000       # 默认 tempo \(微秒/拍\) = 120 BPM
DEFAULT_BPM = 120               # 默认 BPM
DEFAULT_BEAT_DURATION = 0\.5     # 默认拍时长 \(秒\) = 60/120
DEFAULT_BAR_DURATION = 2\.0      # 默认小节时长 \(秒\) = 4拍 \* 0\.5秒
DEFAULT_SEGMENT_BARS = 8        # 8小节为一段


# ---------------- Keyboard Presets \(21-key / 36-key\) ----------------
# Diatonic: C D E F G A B \(7 white keys per octave\)
DIATONIC_OFFSETS = \[0, 2, 4, 5, 7, 9, 11\]
# Sharp offsets: C# D# _ F# G# A# \(5 black keys per octave, no E# or B#\)
SHARP_OFFSETS = \[1, 3, 6, 8, 10\]

# PRESET_21KEY and PRESET_36KEY are imported from keyboard_layout\.py

# Preset combo items for UI
PRESET_COMBO_ITEMS = \[
    \("21-key \(21键\)", "21-key"\),
    \("36-key \(36键\)", "36-key"\),
\]
DEFAULT_KEYBOARD_PRESET = "21-key"



# Data classes, utilities, and PlayerThread moved to player/ module



# FloatingController moved to ui/ module
"@

$replacement = @"
# NOTE: Constants (GM_PROGRAM, TIMING, KEYBOARD_PRESETS) moved to core/constants.py
# NOTE: Utilities (is_admin, get_best_audio_driver) moved to core/constants.py
# NOTE: i18n moved to i18n/ module
# NOTE: Data classes, utilities, PlayerThread moved to player/ module
# NOTE: FloatingController moved to ui/ module
"@

# Use simple string replacement instead of regex
$content = $content -replace [regex]::Escape($pattern.Trim()), $replacement

$content | Set-Content -Path $file -NoNewline -Encoding UTF8
Write-Host "Done"
