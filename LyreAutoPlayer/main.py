import sys
import os
import time
import json
from typing import Optional, List, Dict

# Import core module (constants and utilities)
from core import (
    SCRIPT_DIR, DEFAULT_SOUNDFONT, SETTINGS_FILE, SETTINGS_MIDI_DIR, SETTINGS_SF_DIR,
    setup_dll_path,
    DEFAULT_TEMPO_US, DEFAULT_BPM, DEFAULT_BEAT_DURATION, DEFAULT_BAR_DURATION, DEFAULT_SEGMENT_BARS,
    PRESET_COMBO_ITEMS, DEFAULT_KEYBOARD_PRESET,
    GM_PROGRAM,
    is_admin, get_best_audio_driver,
)

# Setup DLL path for FluidSynth (must be done before importing fluidsynth)
setup_dll_path()

# Import our input manager module
from input_manager import InputManager, InputManagerConfig, create_input_manager, disable_ime_for_window, enable_ime_for_window

# Import settings manager for presets and persistence
from settings_manager import SettingsManager, BUILTIN_PRESETS, SETTINGS_VERSION, create_settings_manager

# Import style system (plugin-based, see styles/ directory)
from style_manager import (
    InputStyle, INPUT_STYLES, EightBarStyle, EIGHT_BAR_PRESETS,
    get_style, get_style_names, get_eight_bar_preset,
    register_style, unregister_style, get_plugin_styles
)

# Import keyboard layout (PRESET_21KEY, PRESET_36KEY for UI compatibility)
from keyboard_layout import PRESET_21KEY, PRESET_36KEY, get_preset_dict

# Import i18n module for translations
from i18n import tr, LANG_EN, LANG_ZH, set_language, get_language, TRANSLATIONS

# Import player module (thread, config, data classes, utilities)
from player import (
    PlayerThread, PlayerConfig,
    ErrorConfig, ErrorType, DEFAULT_ERROR_TYPES, plan_errors_for_group,
    NoteEvent, midi_to_events_with_duration,
    KeyEvent, quantize_note, get_octave_shift, build_available_notes,
    calculate_bar_and_beat_duration, calculate_bar_duration,
    DIATONIC_OFFSETS, SHARP_OFFSETS, MIDI_C2, MIDI_C6,
)

# Import UI module (FloatingController, DiagnosticsWindow, EditorWindow)
from ui import FloatingController, DiagnosticsWindow, ROOT_CHOICES, EditorWindow

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox,
    QFormLayout, QMessageBox, QCheckBox, QTabWidget, QLineEdit, QGridLayout,
    QScrollArea
)

import mido
import pydirectinput
import ctypes

# pydirectinput optimizations for DirectX games
pydirectinput.PAUSE = 0
pydirectinput.FAILSAFE = False

# Windows window focus helpers (optional)
try:
    import win32gui
    import win32con
except Exception:
    win32gui = None
    win32con = None

# FluidSynth for local sound playback (optional)
try:
    import fluidsynth
    _fluidsynth_error = None
    if sys.platform == 'win32':
        # Silence non-fatal FluidSynth MIDI device errors on Windows consoles.
        try:
            _fs_lib = ctypes.CDLL("libfluidsynth-3.dll")
            _fs_lib.fluid_set_log_function.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
            _fs_lib.fluid_set_log_function.restype = ctypes.c_void_p
            # Keep PANIC (0), silence ERR/WARN/INFO/DBG.
            for _level in (1, 2, 3, 4):
                _fs_lib.fluid_set_log_function(_level, None, None)
        except Exception:
            pass
except Exception as e:
    fluidsynth = None
    _fluidsynth_error = str(e)

# sounddevice for audio device enumeration
try:
    import sounddevice as sd
except Exception:
    sd = None

# Global hotkeys - use RegisterHotKey API (more reliable than keyboard library)
try:
    from global_hotkey import GlobalHotkeyManager
    _hotkey_manager: "GlobalHotkeyManager | None" = None
    _hotkey_error = None
except Exception as e:
    GlobalHotkeyManager = None
    _hotkey_manager = None
    _hotkey_error = str(e)

# Fallback: keyboard library (less reliable but works on older systems)
try:
    import keyboard as kb
    _keyboard_error = None
except Exception as e:
    kb = None
    _keyboard_error = str(e)

# NOTE: Constants (GM_PROGRAM, TIMING, PRESETS) moved to core/constants.py
# NOTE: Utilities (is_admin, get_best_audio_driver) moved to core/constants.py
# NOTE: i18n, PlayerThread, FloatingController moved to respective modules


def list_windows() -> List[Tuple[int, str]]:
    """Enumerate visible windows with titles."""
    if win32gui is None:
        return []
    out: List[Tuple[int, str]] = []

    def enum_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title.strip():
                out.append((hwnd, title.strip()))

    win32gui.EnumWindows(enum_cb, None)
    out.sort(key=lambda x: x[1].lower())
    return out


# Import Mixin classes for MainWindow
from ui.mixins import (
    ConfigMixin, PlaybackMixin, SettingsPresetMixin,
    HotkeysMixin, LanguageMixin, LogsMixin
)

# Import Tab Builders for UI construction
from ui.tab_builders import (
    build_main_tab, build_keyboard_tab, build_shortcuts_tab,
    build_style_tab, build_errors_tab
)


class MainWindow(
    QWidget,
    ConfigMixin,
    PlaybackMixin,
    SettingsPresetMixin,
    HotkeysMixin,
    LanguageMixin,
    LogsMixin
):
    # Signals for global hotkeys (thread-safe communication from keyboard thread)
    sig_start = pyqtSignal()
    sig_stop = pyqtSignal()
    sig_toggle_play_pause = pyqtSignal()  # F5: toggle start/pause/resume
    sig_octave_up = pyqtSignal()
    sig_octave_down = pyqtSignal()
    sig_open_midi = pyqtSignal()
    sig_toggle_duration = pyqtSignal()
    sig_speed_up = pyqtSignal()
    sig_speed_down = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.lang = LANG_ZH  # Default language

        self.mid_path: Optional[str] = None
        self.events: List[NoteEvent] = []
        self.thread: Optional[PlayerThread] = None
        self.soundfont_path = ""
        self.floating_controller: Optional[FloatingController] = None
        self.diagnostics_window: Optional[DiagnosticsWindow] = None
        self.editor_window: Optional[EditorWindow] = None
        self._current_input_style = "mechanical"

        # Playback progress tracking (for floating controller)
        self.current_time: float = 0.0
        self.total_duration: float = 0.0
        self.current_bpm: int = 120  # BPM for floating controller sync

        self.init_ui()
        self.apply_language()
        self.refresh_windows()
        self._update_style_params_display(self._current_input_style)  # Initialize style tab params
        self.show_init_messages()

    def init_ui(self):
        self.resize(950, 680)
        layout = QVBoxLayout(self)

        # Language selector at top
        lang_row = QHBoxLayout()
        self.lbl_lang = QLabel("Language / 语言:")
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems([LANG_EN, LANG_ZH])
        self.cmb_lang.setCurrentText(self.lang)
        self.cmb_lang.currentTextChanged.connect(self.on_language_changed)
        lang_row.addStretch()
        lang_row.addWidget(self.lbl_lang)
        lang_row.addWidget(self.cmb_lang)
        layout.addLayout(lang_row)

        # file row
        top = QHBoxLayout()
        self.btn_load = QPushButton()
        self.lbl_file = QLabel()
        self.lbl_file.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top.addWidget(self.btn_load)
        top.addWidget(self.lbl_file, 1)
        layout.addLayout(top)

        # ============== Tab Widget ==============
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Build tabs using tab_builders (Phase 2 modularization)
        self.tabs.addTab(build_main_tab(self), "Main")
        self.tabs.addTab(build_keyboard_tab(self), "Keyboard")
        self.tabs.addTab(build_shortcuts_tab(self), "Shortcuts")
        self.tabs.addTab(build_style_tab(self), "Input Style")
        self.tabs.addTab(build_errors_tab(self), tr("tab_errors", self.lang))

        # --- REMOVED: Tab construction code moved to ui/tab_builders.py ---
        # See: build_main_tab, build_keyboard_tab, build_shortcuts_tab,
        #      build_style_tab, build_errors_tab

        # Connect signals to slots (for thread-safe global hotkey handling)
        self.sig_start.connect(self.on_start)
        self.sig_stop.connect(self.on_stop)
        self.sig_toggle_play_pause.connect(self.on_toggle_play_pause)
        self.sig_octave_up.connect(self.on_octave_up)
        self.sig_octave_down.connect(self.on_octave_down)
        self.sig_open_midi.connect(self.on_load)
        self.sig_toggle_duration.connect(self.on_toggle_midi_duration)
        self.sig_speed_up.connect(self.on_speed_up)
        self.sig_speed_down.connect(self.on_speed_down)
        self.sp_speed.valueChanged.connect(self._on_speed_changed)
        self.chk_octave_range_auto.stateChanged.connect(self._on_octave_range_mode_changed)
        self.sp_octave_min.valueChanged.connect(self._on_octave_range_changed)
        self.sp_octave_max.valueChanged.connect(self._on_octave_range_changed)

        # buttons
        btns = QHBoxLayout()
        self.btn_start = QPushButton()
        self.btn_stop = QPushButton()
        self.btn_stop.setEnabled(False)
        self.btn_test = QPushButton()
        self.btn_test_sound = QPushButton()
        self.btn_floating = QPushButton()  # Floating controller button
        self.btn_diagnostics = QPushButton()  # Input diagnostics button
        btns.addWidget(self.btn_start)
        btns.addWidget(self.btn_stop)
        btns.addWidget(self.btn_test)
        btns.addWidget(self.btn_test_sound)
        btns.addWidget(self.btn_floating)
        btns.addWidget(self.btn_diagnostics)
        layout.addLayout(btns)

        # log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)

        # wiring
        self.btn_load.clicked.connect(self.on_load)
        self.btn_refresh.clicked.connect(self.refresh_windows)
        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_test.clicked.connect(self.on_test)
        self.btn_test_sound.clicked.connect(self.on_test_sound)
        self.btn_sf.clicked.connect(self.on_browse_sf)
        self.btn_floating.clicked.connect(self.on_show_floating)
        self.btn_diagnostics.clicked.connect(self.on_show_diagnostics)

        # Register global hotkeys (must be after self.log is created)
        self._register_global_hotkeys()

        # Initialize octave range mode state
        self._on_octave_range_mode_changed(self.chk_octave_range_auto.checkState().value)

        # Load saved settings (must be after all UI is created)
        self.load_settings()

    def apply_language(self):
        """Apply translations to all UI elements."""
        self.setWindowTitle(tr("window_title", self.lang))
        self.btn_load.setText(tr("load_midi", self.lang))
        self.lbl_file.setText(tr("no_file", self.lang))
        self.grp_config.setTitle(tr("config", self.lang))
        self.lbl_root.setText(tr("middle_row_do", self.lang))
        self.lbl_octave.setText(tr("octave_shift", self.lang))
        self.lbl_transpose.setText(tr("transpose", self.lang))
        self.lbl_policy.setText(tr("accidental_policy", self.lang))
        self.lbl_octave_range_mode.setText(tr("octave_range_mode", self.lang))
        self.chk_octave_range_auto.setText(tr("octave_range_auto", self.lang))
        self.lbl_octave_range.setText(tr("octave_range", self.lang))
        self.lbl_octave_range_to.setText(tr("range_to", self.lang))
        self.sp_octave_min.setToolTip(tr("octave_range_hint", self.lang))
        self.sp_octave_max.setToolTip(tr("octave_range_hint", self.lang))
        self.lbl_speed.setText(tr("speed", self.lang))
        self.lbl_press.setText(tr("press_duration", self.lang))
        self.lbl_midi_duration.setText(tr("use_midi_duration", self.lang))
        self.lbl_preset.setText(tr("keyboard_preset", self.lang))
        self.lbl_countdown.setText(tr("countdown", self.lang))
        self.lbl_window.setText(tr("target_window", self.lang))
        self.cmb_window.setToolTip(tr("target_window_hint", self.lang))
        self.btn_refresh.setText(tr("refresh", self.lang))
        self.grp_sound.setTitle(tr("sound_group", self.lang))
        self.lbl_play_sound.setText(tr("play_sound", self.lang))
        self.chk_sound.setText(tr("enable_sound", self.lang))
        self.lbl_soundfont.setText(tr("soundfont", self.lang))
        if not self.soundfont_path:
            self.lbl_sf.setText(tr("no_sf2", self.lang))
        self.btn_sf.setText(tr("browse", self.lang))
        self.lbl_instrument.setText(tr("instrument", self.lang))
        self.lbl_velocity.setText(tr("velocity", self.lang))
        self.btn_start.setText(tr("start", self.lang))
        self.btn_stop.setText(tr("stop", self.lang))
        self.btn_test.setText(tr("test_keys", self.lang))
        self.btn_test_sound.setText(tr("test_sound", self.lang))
        # Tab titles
        self.tabs.setTabText(0, tr("tab_main", self.lang))
        self.tabs.setTabText(1, tr("tab_keyboard", self.lang))
        self.tabs.setTabText(2, tr("tab_shortcuts", self.lang))
        # Keyboard tab
        self.lbl_kb_preset.setText(tr("current_preset", self.lang) + ":")
        # Shortcuts tab
        for key, _ in self.shortcut_info:
            if key in self.shortcut_labels:
                self.shortcut_labels[key].setText(tr(key, self.lang) + ":")
        self.lbl_global_note.setText(tr("global_hotkey_note", self.lang))
        # Floating button
        self.btn_floating.setText(tr("show_floating", self.lang))
        # Diagnostics button
        self.btn_diagnostics.setText(tr("show_diagnostics", self.lang))
        # Main settings input style
        self.lbl_input_style.setText(tr("input_style", self.lang))
        # Input style tab
        self.tabs.setTabText(3, tr("tab_input_style", self.lang))
        self.lbl_current_style.setText(tr("current_style", self.lang) + ":")
        self.grp_style_params.setTitle(tr("style_params", self.lang))
        self.lbl_timing_offset.setText(tr("timing_offset", self.lang))
        self.lbl_timing_min.setText(tr("timing_offset_min", self.lang) + ":")
        self.lbl_timing_max.setText(tr("timing_offset_max", self.lang) + ":")
        self.lbl_stagger.setText(tr("chord_stagger", self.lang))
        self.lbl_duration_var.setText(tr("duration_variation", self.lang))
        self.grp_custom_style.setTitle(tr("style_custom", self.lang))
        self.lbl_style_name.setText(tr("style_name", self.lang))
        self.lbl_style_desc.setText(tr("style_description", self.lang))
        self.btn_add_style.setText(tr("add_style", self.lang))
        self.btn_delete_style.setText(tr("delete_style", self.lang))
        self.btn_apply_style.setText(tr("apply_style", self.lang))
        # Eight-Bar Style translations
        self.grp_eight_bar.setTitle(tr("eight_bar_style", self.lang))
        self.lbl_eight_bar_enabled.setText(tr("eight_bar_enabled", self.lang))
        self.lbl_eight_bar_mode.setText(tr("eight_bar_mode", self.lang))
        # Update mode combo translations
        self.cmb_eight_bar_mode.setItemText(0, tr("mode_warp", self.lang))
        self.cmb_eight_bar_mode.setItemText(1, tr("mode_beat_lock", self.lang))
        self.lbl_eight_bar_pattern.setText(tr("eight_bar_pattern", self.lang))
        self.lbl_eight_bar_clamp.setText(tr("eight_bar_clamp", self.lang))
        self.lbl_eight_bar_clamp_min.setText(tr("range_min", self.lang))
        self.lbl_eight_bar_clamp_max.setText(tr("range_max", self.lang))
        self.lbl_speed_var.setText(tr("speed_variation", self.lang))
        self.lbl_timing_var.setText(tr("timing_variation", self.lang))
        self.lbl_dur_var_8bar.setText(tr("duration_variation_8bar", self.lang))
        self.lbl_eight_bar_preset.setText(tr("eight_bar_preset", self.lang))
        self.btn_preset_subtle.setText(tr("preset_subtle", self.lang))
        self.btn_preset_moderate.setText(tr("preset_moderate", self.lang))
        self.btn_preset_dramatic.setText(tr("preset_dramatic", self.lang))
        self.lbl_show_indicator.setText(tr("show_indicator", self.lang))
        # Update pattern combo translations
        self.cmb_eight_bar_pattern.setItemText(0, tr("pattern_skip3", self.lang))
        self.cmb_eight_bar_pattern.setItemText(1, tr("pattern_skip2", self.lang))
        self.cmb_eight_bar_pattern.setItemText(2, tr("pattern_skip1", self.lang))
        self.cmb_eight_bar_pattern.setItemText(3, tr("pattern_continuous", self.lang))
        # Rebuild style combos with new language
        self._rebuild_all_style_combos()
        # Error Settings tab (Tab 5)
        self.tabs.setTabText(4, tr("tab_errors", self.lang))
        self.grp_error_types.setTitle(tr("error_types", self.lang))
        self.lbl_error_enabled.setText(tr("enable_errors", self.lang))
        self.lbl_error_freq.setText(tr("errors_per_8bars", self.lang))
        self.chk_wrong_note.setText(tr("error_wrong_note", self.lang))
        self.chk_miss_note.setText(tr("error_miss_note", self.lang))
        self.chk_extra_note.setText(tr("error_extra_note", self.lang))
        self.chk_pause_error.setText(tr("error_pause", self.lang))
        self.lbl_pause_range.setText(tr("pause_duration", self.lang))
        # Quick Error Select in Tab 1
        self.grp_quick_error.setTitle(tr("quick_error_select", self.lang))
        self.chk_quick_error_enable.setText(tr("errors", self.lang))
        self.chk_quick_wrong.setText(tr("error_wrong_note", self.lang))
        self.chk_quick_miss.setText(tr("error_miss_note", self.lang))
        self.chk_quick_extra.setText(tr("error_extra_note", self.lang))
        self.chk_quick_pause.setText(tr("error_pause", self.lang))
        # Quick 8-Bar toggle in Tab 1
        self.lbl_quick_eight_bar.setText(tr("eight_bar_enabled", self.lang))
        # Settings Presets group
        self.grp_presets.setTitle(tr("settings_presets", self.lang))
        self.lbl_preset_select.setText(tr("preset_select", self.lang))
        self.btn_apply_preset.setText(tr("preset_apply", self.lang))
        self.btn_import_settings.setText(tr("import_settings", self.lang))
        self.btn_export_settings.setText(tr("export_settings", self.lang))
        self.btn_reset_defaults.setText(tr("reset_defaults", self.lang))
        # Rebuild preset combo for language change
        self._rebuild_settings_preset_combo()
        # Range labels (Phase 2 i18n fix)
        self.lbl_speed_min.setText(tr("range_min", self.lang))
        self.lbl_speed_max.setText(tr("range_max", self.lang))
        self.lbl_timing_min.setText(tr("range_min", self.lang))
        self.lbl_timing_max.setText(tr("range_max", self.lang))
        self.lbl_dur_min.setText(tr("range_min", self.lang))
        self.lbl_dur_max.setText(tr("range_max", self.lang))
        self.lbl_pause_to.setText(tr("range_to", self.lang))
        # Placeholder texts
        self.txt_style_name.setPlaceholderText(tr("placeholder_style_name", self.lang))
        self.txt_style_desc.setPlaceholderText(tr("placeholder_style_desc", self.lang))
        # Sync diagnostics window language if open
        if self.diagnostics_window:
            self.diagnostics_window.apply_language(self.lang)

    # ---- Input Style Methods ----

    def _rebuild_style_combo(self, combo: QComboBox):
        """Populate a style combo box with current INPUT_STYLES."""
        combo.blockSignals(True)
        combo.clear()
        for style_name, style in INPUT_STYLES.items():
            desc = style.description_zh if self.lang == LANG_ZH else style.description_en
            # Use translation if available, otherwise use style name directly
            trans_key = f"style_{style_name}"
            if trans_key in TRANSLATIONS:
                label = tr(trans_key, self.lang)
            else:
                # Plugin styles: use capitalized name
                label = style_name.replace("_", " ").title()
            display = f"{label} - {desc}"
            combo.addItem(display, style_name)
        combo.blockSignals(False)

    def _rebuild_all_style_combos(self):
        """Rebuild all style combo boxes (after language change or style add/delete)."""
        current_style = getattr(self, '_current_input_style', 'mechanical')

        # Rebuild main settings combo
        self._rebuild_style_combo(self.cmb_input_style)
        self._select_style_in_combo(self.cmb_input_style, current_style)

        # Rebuild style tab combo
        self._rebuild_style_combo(self.cmb_style_tab)
        self._select_style_in_combo(self.cmb_style_tab, current_style)

        # Rebuild floating controller combo if exists
        if self.floating_controller:
            self.floating_controller.rebuild_style_combo(current_style)

    def _select_style_in_combo(self, combo: QComboBox, style_name: str):
        """Select a style in combo box by name."""
        combo.blockSignals(True)
        for i in range(combo.count()):
            if combo.itemData(i) == style_name:
                combo.setCurrentIndex(i)
                break
        combo.blockSignals(False)

    def _update_style_params_display(self, style_name: str):
        """Update the style parameters spinboxes to show the selected style."""
        style = INPUT_STYLES.get(style_name)
        if not style:
            return
        self.sp_timing_min.blockSignals(True)
        self.sp_timing_max.blockSignals(True)
        self.sp_stagger.blockSignals(True)
        self.sp_duration_var.blockSignals(True)

        self.sp_timing_min.setValue(style.timing_offset_ms[0])
        self.sp_timing_max.setValue(style.timing_offset_ms[1])
        self.sp_stagger.setValue(style.stagger_ms)
        self.sp_duration_var.setValue(int(style.duration_variation * 100))

        self.sp_timing_min.blockSignals(False)
        self.sp_timing_max.blockSignals(False)
        self.sp_stagger.blockSignals(False)
        self.sp_duration_var.blockSignals(False)

    def on_input_style_changed(self, index: int):
        """Called when main settings input style combo changes."""
        style_name = self.cmb_input_style.itemData(index)
        if not style_name:
            return
        self._current_input_style = style_name

        # Sync style tab combo
        self._select_style_in_combo(self.cmb_style_tab, style_name)
        self._update_style_params_display(style_name)

        # Sync floating controller
        if self.floating_controller:
            self.floating_controller.sync_style(style_name)

        # Log
        style = INPUT_STYLES.get(style_name)
        if style:
            desc = style.description_zh if self.lang == LANG_ZH else style.description_en
            self.append_log(f"Input style: {style_name} ({desc})")

        # Auto-save settings
        self.save_settings()

    def on_style_tab_changed(self, index: int):
        """Called when style tab combo changes."""
        style_name = self.cmb_style_tab.itemData(index)
        if not style_name:
            return
        self._current_input_style = style_name

        # Sync main settings combo
        self._select_style_in_combo(self.cmb_input_style, style_name)
        self._update_style_params_display(style_name)

        # Sync floating controller
        if self.floating_controller:
            self.floating_controller.sync_style(style_name)

        # Log
        style = INPUT_STYLES.get(style_name)
        if style:
            desc = style.description_zh if self.lang == LANG_ZH else style.description_en
            self.append_log(f"Input style: {style_name} ({desc})")

        # Auto-save settings
        self.save_settings()

    def on_add_custom_style(self):
        """Add a new custom style with current parameter values."""
        name = self.txt_style_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a style name." if self.lang == LANG_EN else "请输入风格名称。")
            return
        if name in INPUT_STYLES:
            QMessageBox.warning(self, "Error", f"Style '{name}' already exists." if self.lang == LANG_EN else f"风格 '{name}' 已存在。")
            return

        desc = self.txt_style_desc.text().strip() or name
        timing_min = self.sp_timing_min.value()
        timing_max = self.sp_timing_max.value()
        stagger = self.sp_stagger.value()
        duration_var = self.sp_duration_var.value() / 100.0

        # Add translation for the new style
        TRANSLATIONS[f"style_{name}"] = {LANG_EN: name.capitalize(), LANG_ZH: desc}

        # Create and register the new style
        new_style = InputStyle(
            name=name,
            timing_offset_ms=(timing_min, timing_max),
            stagger_ms=stagger,
            duration_variation=duration_var,
            description_en=desc,
            description_zh=desc,
            builtin=False,  # User-created styles are not builtin
        )
        register_style(new_style)

        # Rebuild all combos and select the new style
        self._current_input_style = name
        self._rebuild_all_style_combos()
        self._select_style_in_combo(self.cmb_input_style, name)
        self._select_style_in_combo(self.cmb_style_tab, name)

        self.append_log(f"Added custom style: {name}")
        self.txt_style_name.clear()
        self.txt_style_desc.clear()
        self.save_settings()  # Auto-save custom styles

    def on_delete_custom_style(self):
        """Delete the currently selected custom style (cannot delete built-in styles)."""
        style_name = self.cmb_style_tab.currentData()
        if not style_name:
            return

        # Check if style is built-in (via registry)
        style = get_style(style_name)
        if style and getattr(style, 'builtin', False):
            QMessageBox.warning(self, "Error",
                "Cannot delete built-in styles." if self.lang == LANG_EN else "无法删除内置风格。")
            return

        # Confirm deletion
        result = QMessageBox.question(self, "Confirm",
            f"Delete style '{style_name}'?" if self.lang == LANG_EN else f"删除风格 '{style_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes:
            return

        # Delete the style using registry
        unregister_style(style_name)
        if f"style_{style_name}" in TRANSLATIONS:
            del TRANSLATIONS[f"style_{style_name}"]

        # Reset to mechanical and rebuild
        self._current_input_style = "mechanical"
        self._rebuild_all_style_combos()
        self._update_style_params_display("mechanical")

        self.append_log(f"Deleted custom style: {style_name}")
        self.save_settings()  # Auto-save custom styles

    def on_apply_style_params(self):
        """Apply the current parameter values to the selected style."""
        style_name = self.cmb_style_tab.currentData()
        if not style_name:
            return

        # Check if style is built-in (via registry)
        style = get_style(style_name)
        if style and getattr(style, 'builtin', False):
            QMessageBox.information(self, "Info",
                "Cannot modify built-in styles. Use 'Add Style' to create a custom copy." if self.lang == LANG_EN
                else "无法修改内置风格。请使用'添加风格'创建自定义副本。")
            return

        # Update the custom style
        if style:
            timing_min = self.sp_timing_min.value()
            timing_max = self.sp_timing_max.value()
            stagger = self.sp_stagger.value()
            duration_var = self.sp_duration_var.value() / 100.0

            # Create a new style with updated values (dataclass is immutable by default)
            updated_style = InputStyle(
                name=style_name,
                timing_offset_ms=(timing_min, timing_max),
                stagger_ms=stagger,
                duration_variation=duration_var,
                description_en=style.description_en,
                description_zh=style.description_zh,
                builtin=False,  # Modified styles are not builtin
            )
            INPUT_STYLES[style_name] = updated_style
            self.append_log(f"Updated style: {style_name} (offset={timing_min}~{timing_max}ms, stagger={stagger}ms, var={duration_var*100:.0f}%)")
            self.save_settings()  # Auto-save custom styles

    # ---- Settings Preset Methods ----

    def on_import_settings(self):
        """Import settings from a JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr('import_settings', self.lang),
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            # Apply imported settings
            self._apply_settings_dict(settings)
            self.append_log(f"[OK] {tr('import_success', self.lang)}: {os.path.basename(path)}")

        except Exception as e:
            self.append_log(f"[FAIL] {tr('import_failed', self.lang)}: {e}")

    def on_export_settings(self):
        """Export current settings to a JSON file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr('export_settings', self.lang),
            "lyre_settings.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return

        try:
            settings = self._collect_current_settings()
            settings['_exported_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
            settings['_export_version'] = SETTINGS_VERSION

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            self.append_log(f"[OK] {tr('export_success', self.lang)}: {os.path.basename(path)}")

        except Exception as e:
            self.append_log(f"[FAIL] {tr('export_failed', self.lang)}: {e}")

    def _build_keyboard_display(self):
        """Build the keyboard mapping display grid."""
        # Clear existing widgets
        while self.keyboard_grid.count():
            item = self.keyboard_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.key_editors.clear()

        preset = self.cmb_preset.currentData() or "21-key"

        # Note names for display
        note_names = ["Do", "Re", "Mi", "Fa", "Sol", "La", "Si"]
        sharp_names = ["Do#", "Re#", "Fa#", "Sol#", "La#"]

        if preset == "21-key":
            preset_data = PRESET_21KEY
            rows = [
                ("octave_high", "high", note_names, False),
                ("octave_mid", "mid", note_names, False),
                ("octave_low", "low", note_names, False),
            ]
        else:
            preset_data = PRESET_36KEY
            rows = [
                ("octave_high", "high", note_names, False),
                ("octave_high", "high_sharp", sharp_names, True),
                ("octave_mid", "mid", note_names, False),
                ("octave_mid", "mid_sharp", sharp_names, True),
                ("octave_low", "low", note_names, False),
                ("octave_low", "low_sharp", sharp_names, True),
            ]

        row_idx = 0
        for label_key, preset_key, names, is_sharp in rows:
            # Row label
            label_text = tr(label_key, self.lang)
            if is_sharp:
                label_text += " (#)"
            lbl = QLabel(f"<b>{label_text}</b>")
            self.keyboard_grid.addWidget(lbl, row_idx, 0)

            keys = preset_data.get(preset_key, [])
            for col, (note_name, key_char) in enumerate(zip(names, keys)):
                # Note name label
                note_lbl = QLabel(note_name)
                note_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.keyboard_grid.addWidget(note_lbl, row_idx, col * 2 + 1)

                # Key editor
                editor = QLineEdit(key_char)
                editor.setMaxLength(1)
                editor.setFixedWidth(40)
                editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.keyboard_grid.addWidget(editor, row_idx, col * 2 + 2)
                self.key_editors[(preset_key, col)] = editor

            row_idx += 1

    def show_init_messages(self):
        admin_status = is_admin()
        if admin_status:
            self.append_log(tr("admin_ok", self.lang))
        else:
            self.append_log(tr("admin_warn", self.lang))
            self.append_log(tr("uipi_hint", self.lang))
        self.append_log(tr("ready_msg", self.lang))
        self.append_log(tr("sound_hint", self.lang))

        # Show FluidSynth status
        if fluidsynth is None:
            self.append_log(f"[WARN] FluidSynth: not available")
        else:
            self.append_log("[OK] FluidSynth: available")

        # Show loaded style plugins
        plugin_styles = get_plugin_styles()
        if plugin_styles:
            self.append_log(f"[INFO] Loaded style plugins: {', '.join(plugin_styles)}")

    def refresh_windows(self):
        self.cmb_window.clear()
        if win32gui is None:
            self.cmb_window.addItem(tr("pywin32_unavail", self.lang), None)
            return
        self.cmb_window.addItem(tr("none_manual", self.lang), None)
        for hwnd, title in list_windows()[:300]:
            self.cmb_window.addItem(title, hwnd)

    def on_load(self):
        settings = QSettings("LyreAutoPlayer", "LyreAutoPlayer")
        last_dir = settings.value(SETTINGS_MIDI_DIR, "")
        path, _ = QFileDialog.getOpenFileName(self, "Select MIDI file", last_dir, "MIDI Files (*.mid *.midi)")
        if not path:
            return
        # Remember directory
        settings.setValue(SETTINGS_MIDI_DIR, os.path.dirname(path))

        # Step 1: Select version (returns selected_path to use)
        selected_path = self._select_version(path)

        # Step 2: Load MIDI for playback using selected_path
        try:
            self.events = midi_to_events_with_duration(selected_path)
        except Exception as e:
            QMessageBox.critical(self, "MIDI parse error", str(e))
            return

        # Step 3: Update main UI with selected_path
        self.mid_path = selected_path
        self.lbl_file.setText(f"{selected_path}  (notes: {len(self.events)})")
        self.append_log(f"Loaded: {selected_path}")
        self.append_log(f"Parsed note events: {len(self.events)}")

        # Show duration stats
        durations = [e.duration for e in self.events if e.duration > 0]
        if durations:
            avg_dur = sum(durations) / len(durations)
            self.append_log(f"Duration stats: avg={avg_dur*1000:.0f}ms, min={min(durations)*1000:.0f}ms, max={max(durations)*1000:.0f}ms")

        # Auto-save settings
        self.save_settings()

        # Step 4: Open editor with the same selected_path
        self._open_editor(selected_path)

    def _select_version(self, original_path: str) -> str:
        """选择版本：有历史版本时弹窗选择，取消时返回最新版本，无历史时返回原始路径"""
        versions, stats = EditorWindow.get_edited_versions(original_path, return_stats=True)

        # 显示索引维护结果（迁移/清理）
        EditorWindow.show_index_maintenance_result(stats, parent=self)

        if not versions:
            # 无已编辑版本，返回原始文件
            return original_path

        # 有已编辑版本（已按 last_modified 逆序排列，最新在前）
        from PyQt6.QtWidgets import QInputDialog

        # 构建选项列表：最新版本在第一位，原始文件在最后
        items = []
        for v in versions:
            items.append(f"{v.get('display_name', 'Unknown')} ({v.get('edit_style', '?')})")
        items.append(tr("original_file", self.lang))

        choice, ok = QInputDialog.getItem(
            self, tr("select_version", self.lang),
            tr("select_version_prompt", self.lang),
            items, 0, False  # 默认选中第一项（最新版本）
        )

        if not ok:
            # 用户取消选择：返回最新保存版本
            return versions[0].get("saved_path", original_path)

        if choice == items[-1]:
            # 选择原始文件
            return original_path
        else:
            # 选择已编辑版本
            idx = items.index(choice)
            return versions[idx].get("saved_path", original_path)

    def _open_editor(self, path: str):
        """Open the MIDI editor window with specified path."""
        # Create or reuse editor window
        if self.editor_window is None:
            self.editor_window = EditorWindow(parent=None)
            # Connect signals to sync data back to main window
            self.editor_window.midi_loaded.connect(self._on_editor_midi_loaded)
            self.editor_window.bpm_changed.connect(self._on_editor_bpm_changed)

        self.editor_window.load_midi(path)
        self.editor_window.show()
        self.editor_window.raise_()
        self.editor_window.activateWindow()

    def _on_editor_midi_loaded(self, path: str, events_list: list):
        """Called when editor loads a MIDI file - sync to main window."""
        self.mid_path = path
        # Convert dict list to NoteEvent list and sort by time
        self.events = sorted(
            [NoteEvent(time=ev["time"], note=ev["note"], duration=ev["duration"])
             for ev in events_list],
            key=lambda e: e.time
        )
        # Sync BPM from editor if available
        if self.editor_window and hasattr(self.editor_window, 'sp_bpm'):
            self.current_bpm = self.editor_window.sp_bpm.value()
        # Update UI
        filename = os.path.basename(path)
        self.lbl_file.setText(filename)
        self.append_log(f"[Editor] Synced MIDI: {filename} ({len(self.events)} notes)")
        # Sync floating controller if visible
        if self.floating_controller and self.floating_controller.isVisible():
            self.floating_controller._sync_from_main()

    def _on_editor_bpm_changed(self, bpm: int):
        """Called when editor BPM changes - sync to main window and floating controller."""
        self.current_bpm = bpm
        # Sync floating controller if visible
        if self.floating_controller and self.floating_controller.isVisible():
            self.floating_controller._sync_from_main()

    def on_browse_sf(self):
        settings = QSettings("LyreAutoPlayer", "LyreAutoPlayer")
        last_dir = settings.value(SETTINGS_SF_DIR, "")
        path, _ = QFileDialog.getOpenFileName(self, "Select SoundFont", last_dir, "SoundFont Files (*.sf2 *.sf3)")
        if not path:
            return
        settings.setValue(SETTINGS_SF_DIR, os.path.dirname(path))
        self.soundfont_path = path
        self.lbl_sf.setText(os.path.basename(path))
        self.append_log(f"SoundFont: {path}")

        # Auto-save settings
        self.save_settings()

    def _on_error_enabled_changed(self, state: int):
        """Toggle error simulation on/off."""
        self._error_enabled = state == Qt.CheckState.Checked.value
        if self.floating_controller:
            self.floating_controller.sync_error_settings(self._error_enabled, self._error_freq)
        self.append_log(f"Error simulation: {'ON' if self._error_enabled else 'OFF'}")

    def _on_error_freq_changed(self, value: int):
        """Change error frequency (per 8 bars)."""
        self._error_freq = value
        if self.floating_controller:
            self.floating_controller.sync_error_settings(self._error_enabled, self._error_freq)

    def _on_quick_error_enable_changed(self, state: int):
        """Sync quick error enable checkbox from Tab 1 to Tab 5."""
        enabled = state == Qt.CheckState.Checked.value
        self._error_enabled = enabled
        # Sync to Tab 5
        self.chk_error_enabled.setChecked(enabled)
        # Sync to FloatingController
        if self.floating_controller:
            self.floating_controller.sync_error_settings(self._error_enabled, self._error_freq)
        self.append_log(f"Error simulation: {'ON' if enabled else 'OFF'}")

    def _sync_quick_errors_to_tab5(self, state: int = None):
        """Sync error type checkboxes from Tab 1 to Tab 5 (with signal blocking)."""
        # Block Tab 5 signals to prevent infinite recursion
        self.chk_wrong_note.blockSignals(True)
        self.chk_miss_note.blockSignals(True)
        self.chk_extra_note.blockSignals(True)
        self.chk_pause_error.blockSignals(True)

        self.chk_wrong_note.setChecked(self.chk_quick_wrong.isChecked())
        self.chk_miss_note.setChecked(self.chk_quick_miss.isChecked())
        self.chk_extra_note.setChecked(self.chk_quick_extra.isChecked())
        self.chk_pause_error.setChecked(self.chk_quick_pause.isChecked())

        self.chk_wrong_note.blockSignals(False)
        self.chk_miss_note.blockSignals(False)
        self.chk_extra_note.blockSignals(False)
        self.chk_pause_error.blockSignals(False)

    def _sync_tab5_errors_to_quick(self):
        """Sync error settings from Tab 5 to Tab 1 quick checkboxes."""
        self.chk_quick_error_enable.setChecked(self.chk_error_enabled.isChecked())
        self.chk_quick_wrong.setChecked(self.chk_wrong_note.isChecked())
        self.chk_quick_miss.setChecked(self.chk_miss_note.isChecked())
        self.chk_quick_extra.setChecked(self.chk_extra_note.isChecked())
        self.chk_quick_pause.setChecked(self.chk_pause_error.isChecked())

    def _sync_tab5_to_quick_errors(self, state: int = None):
        """Sync from Tab 5 to Tab 1 (with signal blocking to prevent recursion)."""
        # Block Tab 1 signals to prevent infinite recursion
        self.chk_quick_wrong.blockSignals(True)
        self.chk_quick_miss.blockSignals(True)
        self.chk_quick_extra.blockSignals(True)
        self.chk_quick_pause.blockSignals(True)

        self.chk_quick_wrong.setChecked(self.chk_wrong_note.isChecked())
        self.chk_quick_miss.setChecked(self.chk_miss_note.isChecked())
        self.chk_quick_extra.setChecked(self.chk_extra_note.isChecked())
        self.chk_quick_pause.setChecked(self.chk_pause_error.isChecked())

        self.chk_quick_wrong.blockSignals(False)
        self.chk_quick_miss.blockSignals(False)
        self.chk_quick_extra.blockSignals(False)
        self.chk_quick_pause.blockSignals(False)

    # ---- Eight-Bar Style Methods ----

    def _on_eight_bar_enabled_changed(self, state: int):
        """Toggle eight-bar style variation on/off."""
        enabled = state == Qt.CheckState.Checked.value
        self.append_log(f"8-Bar variation: {'ON' if enabled else 'OFF'}")
        # Sync to quick checkbox in Tab 1
        self.chk_quick_eight_bar.blockSignals(True)
        self.chk_quick_eight_bar.setChecked(enabled)
        self.chk_quick_eight_bar.blockSignals(False)
        # Sync to floating controller if exists
        if self.floating_controller:
            self.floating_controller.sync_eight_bar_enabled(enabled)

    def _apply_eight_bar_preset(self, preset_name: str):
        """Apply a predefined eight-bar style preset."""
        if preset_name not in EIGHT_BAR_PRESETS:
            return
        preset = EIGHT_BAR_PRESETS[preset_name]

        # Apply values to UI
        self.sp_speed_min.setValue(int(preset.speed_mult_min * 100))
        self.sp_speed_max.setValue(int(preset.speed_mult_max * 100))
        self.sp_timing_var_min.setValue(int(preset.timing_mult_min * 100))
        self.sp_timing_var_max.setValue(int(preset.timing_mult_max * 100))
        self.sp_dur_var_min.setValue(int(preset.duration_mult_min * 100))
        self.sp_dur_var_max.setValue(int(preset.duration_mult_max * 100))

        self.append_log(f"8-Bar preset applied: {preset_name}")

    def _on_quick_eight_bar_changed(self, state: int):
        """Sync quick 8-bar toggle from Tab 1 to Tab 4 (Input Style)."""
        enabled = state == Qt.CheckState.Checked.value
        # Sync to Tab 4 checkbox (block signals to prevent recursion)
        self.chk_eight_bar_enabled.blockSignals(True)
        self.chk_eight_bar_enabled.setChecked(enabled)
        self.chk_eight_bar_enabled.blockSignals(False)
        # Trigger the main handler
        self._on_eight_bar_enabled_changed(state)

    def _sync_eight_bar_to_quick(self):
        """Sync 8-bar enabled state from Tab 4 to Tab 1 quick checkbox."""
        self.chk_quick_eight_bar.blockSignals(True)
        self.chk_quick_eight_bar.setChecked(self.chk_eight_bar_enabled.isChecked())
        self.chk_quick_eight_bar.blockSignals(False)

    def closeEvent(self, event):
        """Cleanup global hotkeys on window close."""
        # Save settings before closing
        self.save_settings()

        # Cleanup RegisterHotKey manager
        global _hotkey_manager
        if _hotkey_manager is not None:
            try:
                _hotkey_manager.stop()
                _hotkey_manager = None
            except Exception:
                pass

        # Cleanup keyboard library hooks
        if kb is not None:
            try:
                kb.unhook_all_hotkeys()
            except Exception:
                pass
        # Stop player thread if running
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait(1000)
        # Close floating controller
        if self.floating_controller:
            self.floating_controller.close()
        event.accept()

    def on_test(self):
        self.append_log(tr("test_pressing", self.lang))
        for k in "asdfghj":
            pydirectinput.press(k)
            time.sleep(0.05)

    def on_test_sound(self):
        """Test FluidSynth sound output directly."""
        self.append_log("=== Testing FluidSynth Sound ===")

        if fluidsynth is None:
            self.append_log(f"[FAIL] FluidSynth not available: {_fluidsynth_error}")
            return

        if not self.soundfont_path:
            self.append_log("[FAIL] No SoundFont selected")
            return

        if not os.path.isfile(self.soundfont_path):
            self.append_log(f"[FAIL] SoundFont not found: {self.soundfont_path}")
            return

        fs = None
        try:
            # Create synth
            fs = fluidsynth.Synth()
            self.append_log("[OK] FluidSynth.Synth() created")

            # Configure - use larger buffers for stability
            fs.setting('synth.sample-rate', 44100.0)
            fs.setting('audio.period-size', 1024)
            fs.setting('audio.periods', 4)
            fs.setting('synth.gain', 1.0)
            fs.setting('synth.polyphony', 64)
            if sys.platform != 'win32':
                fs.setting('midi.driver', 'none')  # Disable MIDI input
            self.append_log("[OK] Settings configured")

            # Try each driver
            drivers = ['dsound', 'wasapi', 'portaudio'] if sys.platform == 'win32' else ['pulseaudio', 'alsa']
            started = False
            for drv in drivers:
                try:
                    self.append_log(f"[TRY] Starting driver '{drv}'...")
                    fs.start(driver=drv)
                    self.append_log(f"[OK] Driver '{drv}' started!")
                    started = True
                    break
                except Exception as e:
                    self.append_log(f"[FAIL] Driver '{drv}': {e}")

            if not started:
                self.append_log("[FAIL] All audio drivers failed")
                fs.delete()
                return

            # Load soundfont
            sfid = fs.sfload(self.soundfont_path)
            if sfid == -1:
                self.append_log("[FAIL] Failed to load SoundFont")
                fs.delete()
                return
            self.append_log(f"[OK] SoundFont loaded (id={sfid})")

            # Select instrument
            prog = GM_PROGRAM.get(self.cmb_instrument.currentText(), 1) - 1
            fs.program_select(0, sfid, 0, prog)
            self.append_log(f"[OK] Program selected: {self.cmb_instrument.currentText()} (prog={prog})")

            # Play test notes (C major chord)
            vel = self.sp_velocity.value()
            self.append_log(f"[PLAY] Playing C-E-G chord at velocity {vel}...")

            fs.noteon(0, 60, vel)  # C4
            fs.noteon(0, 64, vel)  # E4
            fs.noteon(0, 67, vel)  # G4

            # Wait for sound to play
            time.sleep(1.0)

            fs.noteoff(0, 60)
            fs.noteoff(0, 64)
            fs.noteoff(0, 67)

            time.sleep(0.2)
            self.append_log("[OK] Test complete - did you hear sound?")

        except Exception as e:
            self.append_log(f"[FAIL] Exception: {e}")
            import traceback
            self.append_log(traceback.format_exc())
        finally:
            if fs:
                try:
                    fs.delete()
                except:
                    pass


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
