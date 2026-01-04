# ui/tab_builders.py
# Tab Builder functions for MainWindow
# Phase 2 of main.py modularization

from __future__ import annotations
import os
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QLineEdit, QScrollArea, QGridLayout
)

# Import from project modules (same as main.py)
from core import PRESET_COMBO_ITEMS, DEFAULT_SOUNDFONT, GM_PROGRAM
from keyboard_layout import PRESET_21KEY, PRESET_36KEY
from i18n import tr
from .constants import ROOT_CHOICES

if TYPE_CHECKING:
    from main import MainWindow


def build_main_tab(window: "MainWindow") -> QWidget:
    """Build Tab 1: Main Settings tab and attach widgets to window."""
    tab = QWidget()
    layout = QVBoxLayout(tab)

    # --- Config Group ---
    window.grp_config = QGroupBox()
    form = QFormLayout(window.grp_config)

    # Root note selector
    window.cmb_root = QComboBox()
    for name, val in ROOT_CHOICES:
        window.cmb_root.addItem(name, val)
    window.cmb_root.setCurrentIndex(1)
    window.lbl_root = QLabel()
    form.addRow(window.lbl_root, window.cmb_root)

    # Octave shift: -2, -1, 0, +1, +2
    window.cmb_octave = QComboBox()
    for shift in [-2, -1, 0, 1, 2]:
        label = f"{shift:+d}" if shift != 0 else "0"
        window.cmb_octave.addItem(label, shift)
    window.cmb_octave.setCurrentIndex(2)  # Default: 0
    window.lbl_octave = QLabel()
    form.addRow(window.lbl_octave, window.cmb_octave)

    # Transpose
    window.sp_transpose = QSpinBox()
    window.sp_transpose.setRange(-24, 24)
    window.lbl_transpose = QLabel()
    form.addRow(window.lbl_transpose, window.sp_transpose)

    # Policy
    window.cmb_policy = QComboBox()
    window.cmb_policy.addItems(["octave", "lower", "upper", "drop"])
    window.lbl_policy = QLabel()
    form.addRow(window.lbl_policy, window.cmb_policy)

    # Octave range mode (auto/manual)
    window.chk_octave_range_auto = QCheckBox()
    window.chk_octave_range_auto.setChecked(False)
    window.lbl_octave_range_mode = QLabel()
    form.addRow(window.lbl_octave_range_mode, window.chk_octave_range_auto)

    # Octave range (MIDI)
    range_row = QHBoxLayout()
    window.sp_octave_min = QSpinBox()
    window.sp_octave_min.setRange(0, 127)
    window.sp_octave_min.setValue(36)
    window.lbl_octave_range_to = QLabel("~")
    window.sp_octave_max = QSpinBox()
    window.sp_octave_max.setRange(0, 127)
    window.sp_octave_max.setValue(84)
    range_row.addWidget(window.sp_octave_min)
    range_row.addWidget(window.lbl_octave_range_to)
    range_row.addWidget(window.sp_octave_max)
    window.lbl_octave_range = QLabel()
    form.addRow(window.lbl_octave_range, range_row)

    # Speed
    window.sp_speed = QDoubleSpinBox()
    window.sp_speed.setRange(0.25, 4.0)
    window.sp_speed.setValue(1.0)
    window.sp_speed.setSingleStep(0.05)
    window.lbl_speed = QLabel()
    form.addRow(window.lbl_speed, window.sp_speed)

    # Press duration
    window.sp_press = QSpinBox()
    window.sp_press.setRange(5, 500)
    window.sp_press.setValue(25)
    window.lbl_press = QLabel()
    form.addRow(window.lbl_press, window.sp_press)

    # MIDI duration checkbox
    window.chk_midi_duration = QCheckBox()
    window.lbl_midi_duration = QLabel()
    form.addRow(window.lbl_midi_duration, window.chk_midi_duration)

    # Keyboard preset
    window.cmb_preset = QComboBox()
    for label, data in PRESET_COMBO_ITEMS:
        window.cmb_preset.addItem(label, data)
    window.cmb_preset.currentIndexChanged.connect(window.on_preset_changed)
    window.lbl_preset = QLabel()
    form.addRow(window.lbl_preset, window.cmb_preset)

    # Countdown
    window.sp_countdown = QSpinBox()
    window.sp_countdown.setRange(0, 10)
    window.sp_countdown.setValue(2)
    window.lbl_countdown = QLabel()
    form.addRow(window.lbl_countdown, window.sp_countdown)

    # Target window selector
    win_row = QHBoxLayout()
    window.cmb_window = QComboBox()
    window.cmb_window.setToolTip(tr("target_window_hint", window.lang))
    window.btn_refresh = QPushButton()
    win_row.addWidget(window.cmb_window, 1)
    win_row.addWidget(window.btn_refresh)
    window.lbl_window = QLabel()
    form.addRow(window.lbl_window, win_row)

    layout.addWidget(window.grp_config)

    # --- Sound Settings Group ---
    window.grp_sound = QGroupBox()
    snd_form = QFormLayout(window.grp_sound)

    window.chk_sound = QCheckBox()
    window.lbl_play_sound = QLabel()
    snd_form.addRow(window.lbl_play_sound, window.chk_sound)

    sf_row = QHBoxLayout()
    window.lbl_sf = QLabel()
    window.btn_sf = QPushButton()
    sf_row.addWidget(window.lbl_sf, 1)
    sf_row.addWidget(window.btn_sf)
    window.lbl_soundfont = QLabel()
    snd_form.addRow(window.lbl_soundfont, sf_row)

    # Load default soundfont
    if os.path.isfile(DEFAULT_SOUNDFONT):
        window.soundfont_path = DEFAULT_SOUNDFONT
        window.lbl_sf.setText(os.path.basename(DEFAULT_SOUNDFONT))

    window.cmb_instrument = QComboBox()
    window.cmb_instrument.addItems(list(GM_PROGRAM.keys()))
    window.lbl_instrument = QLabel()
    snd_form.addRow(window.lbl_instrument, window.cmb_instrument)

    window.sp_velocity = QSpinBox()
    window.sp_velocity.setRange(1, 127)
    window.sp_velocity.setValue(90)
    window.lbl_velocity = QLabel()
    snd_form.addRow(window.lbl_velocity, window.sp_velocity)

    layout.addWidget(window.grp_sound)

    # --- Strict Mode / Auto-Pause Group ---
    window.grp_strict_mode = QGroupBox()
    strict_form = QFormLayout(window.grp_strict_mode)

    # Strict mode checkbox (default ON)
    window.chk_strict_mode = QCheckBox()
    window.chk_strict_mode.setChecked(True)
    window.chk_strict_mode.stateChanged.connect(window._on_strict_mode_changed)
    window.lbl_strict_mode = QLabel()
    strict_form.addRow(window.lbl_strict_mode, window.chk_strict_mode)

    # Auto-pause interval selector
    pause_row = QHBoxLayout()
    window.cmb_pause_bars = QComboBox()
    window.cmb_pause_bars.addItem("Disabled", 0)
    window.cmb_pause_bars.addItem("Every bar", 1)
    window.cmb_pause_bars.addItem("Every 2 bars", 2)
    window.cmb_pause_bars.addItem("Every 4 bars", 4)
    window.cmb_pause_bars.addItem("Every 8 bars", 8)
    window.cmb_pause_bars.setCurrentIndex(0)
    window.lbl_pause_bars = QLabel()
    pause_row.addWidget(window.cmb_pause_bars)
    strict_form.addRow(window.lbl_pause_bars, pause_row)

    # Auto-resume countdown spinner
    countdown_row = QHBoxLayout()
    window.sp_auto_resume_countdown = QSpinBox()
    window.sp_auto_resume_countdown.setRange(1, 10)
    window.sp_auto_resume_countdown.setValue(3)
    window.sp_auto_resume_countdown.setSuffix(" sec")
    window.lbl_auto_resume_countdown = QLabel()
    countdown_row.addWidget(window.sp_auto_resume_countdown)
    countdown_row.addStretch()
    strict_form.addRow(window.lbl_auto_resume_countdown, countdown_row)

    layout.addWidget(window.grp_strict_mode)

    # --- Settings Presets Group ---
    window.grp_presets = QGroupBox()
    presets_layout = QHBoxLayout(window.grp_presets)

    window.lbl_preset_select = QLabel()
    presets_layout.addWidget(window.lbl_preset_select)

    window.cmb_settings_preset = QComboBox()
    window._rebuild_settings_preset_combo()
    presets_layout.addWidget(window.cmb_settings_preset)

    window.btn_apply_preset = QPushButton()
    window.btn_apply_preset.clicked.connect(window.on_apply_settings_preset)
    presets_layout.addWidget(window.btn_apply_preset)

    window.btn_import_settings = QPushButton()
    window.btn_import_settings.clicked.connect(window.on_import_settings)
    presets_layout.addWidget(window.btn_import_settings)

    window.btn_export_settings = QPushButton()
    window.btn_export_settings.clicked.connect(window.on_export_settings)
    presets_layout.addWidget(window.btn_export_settings)

    window.btn_reset_defaults = QPushButton()
    window.btn_reset_defaults.clicked.connect(window.on_reset_defaults)
    presets_layout.addWidget(window.btn_reset_defaults)

    presets_layout.addStretch()
    layout.addWidget(window.grp_presets)

    layout.addStretch()
    return tab


def build_keyboard_tab(window: "MainWindow") -> QWidget:
    """Build Tab 2: Keyboard Settings tab and attach widgets to window."""
    tab = QWidget()
    layout = QVBoxLayout(tab)

    # Preset selector row (synced with main tab)
    preset_row = QHBoxLayout()
    window.lbl_kb_preset = QLabel()
    window.cmb_kb_preset = QComboBox()
    for label, data in PRESET_COMBO_ITEMS:
        window.cmb_kb_preset.addItem(label, data)
    window.cmb_kb_preset.currentIndexChanged.connect(window.on_kb_preset_changed)
    preset_row.addWidget(window.lbl_kb_preset)
    preset_row.addWidget(window.cmb_kb_preset)
    preset_row.addStretch()
    layout.addLayout(preset_row)

    # Keyboard mapping display (scrollable)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll_content = QWidget()
    window.keyboard_grid = QGridLayout(scroll_content)
    window.keyboard_grid.setSpacing(5)
    scroll.setWidget(scroll_content)
    layout.addWidget(scroll, 1)

    # Note editors dictionary
    window.key_editors = {}

    # Build initial keyboard display
    window._build_keyboard_display()

    return tab


def build_shortcuts_tab(window: "MainWindow") -> QWidget:
    """Build Tab 3: Shortcuts tab and attach widgets to window."""
    tab = QWidget()
    layout = QVBoxLayout(tab)

    # Shortcuts display group
    sc_group = QGroupBox()
    sc_form = QFormLayout(sc_group)

    # Define shortcuts with their display info
    window.shortcut_info = [
        ("shortcut_start", "F5"),
        ("shortcut_stop", "F6"),
        ("shortcut_speed_down", "F7"),
        ("shortcut_speed_up", "F8"),
        ("shortcut_octave_down", "F9"),
        ("shortcut_octave_up", "F10"),
        ("shortcut_open_midi", "F11"),
        ("shortcut_toggle_duration", "F12"),
    ]

    window.shortcut_labels = {}
    for key, shortcut in window.shortcut_info:
        lbl = QLabel()
        window.shortcut_labels[key] = lbl
        sc_form.addRow(lbl, QLabel(f"<b>{shortcut}</b>"))

    layout.addWidget(sc_group)

    # Note about global hotkeys
    window.lbl_global_note = QLabel()
    window.lbl_global_note.setStyleSheet("color: #666; font-style: italic;")
    layout.addWidget(window.lbl_global_note)

    layout.addStretch()
    return tab


def build_style_tab(window: "MainWindow") -> QWidget:
    """Build Tab 4: Input Style Settings tab and attach widgets to window."""
    tab = QWidget()
    layout = QVBoxLayout(tab)

    # Current style selector
    current_row = QHBoxLayout()
    window.lbl_current_style = QLabel()
    window.cmb_style_tab = QComboBox()
    window._rebuild_style_combo(window.cmb_style_tab)
    window.cmb_style_tab.currentIndexChanged.connect(window.on_style_tab_changed)
    current_row.addWidget(window.lbl_current_style)
    current_row.addWidget(window.cmb_style_tab, 1)
    layout.addLayout(current_row)

    # --- Style Parameters Group ---
    window.grp_style_params = QGroupBox()
    param_form = QFormLayout(window.grp_style_params)

    # Timing offset (min, max)
    timing_row = QHBoxLayout()
    window.lbl_timing_min = QLabel()
    window.sp_timing_min = QSpinBox()
    window.sp_timing_min.setRange(-50, 50)
    window.sp_timing_min.setValue(0)
    window.lbl_timing_max = QLabel()
    window.sp_timing_max = QSpinBox()
    window.sp_timing_max.setRange(-50, 50)
    window.sp_timing_max.setValue(0)
    timing_row.addWidget(window.lbl_timing_min)
    timing_row.addWidget(window.sp_timing_min)
    timing_row.addWidget(window.lbl_timing_max)
    timing_row.addWidget(window.sp_timing_max)
    timing_row.addStretch()
    window.lbl_timing_offset = QLabel()
    param_form.addRow(window.lbl_timing_offset, timing_row)

    # Chord stagger
    window.sp_stagger = QSpinBox()
    window.sp_stagger.setRange(0, 100)
    window.sp_stagger.setValue(0)
    window.lbl_stagger = QLabel()
    param_form.addRow(window.lbl_stagger, window.sp_stagger)

    # Duration variation
    window.sp_duration_var = QSpinBox()
    window.sp_duration_var.setRange(0, 50)
    window.sp_duration_var.setValue(0)
    window.sp_duration_var.setSuffix("%")
    window.lbl_duration_var = QLabel()
    param_form.addRow(window.lbl_duration_var, window.sp_duration_var)

    layout.addWidget(window.grp_style_params)

    # --- Custom Style Creation Group ---
    window.grp_custom_style = QGroupBox()
    custom_form = QFormLayout(window.grp_custom_style)

    window.txt_style_name = QLineEdit()
    window.txt_style_name.setPlaceholderText(tr("placeholder_style_name", window.lang))
    window.lbl_style_name = QLabel()
    custom_form.addRow(window.lbl_style_name, window.txt_style_name)

    window.txt_style_desc = QLineEdit()
    window.txt_style_desc.setPlaceholderText(tr("placeholder_style_desc", window.lang))
    window.lbl_style_desc = QLabel()
    custom_form.addRow(window.lbl_style_desc, window.txt_style_desc)

    # Add/Delete buttons
    style_btns = QHBoxLayout()
    window.btn_add_style = QPushButton()
    window.btn_delete_style = QPushButton()
    window.btn_apply_style = QPushButton()
    window.btn_add_style.clicked.connect(window.on_add_custom_style)
    window.btn_delete_style.clicked.connect(window.on_delete_custom_style)
    window.btn_apply_style.clicked.connect(window.on_apply_style_params)
    style_btns.addWidget(window.btn_add_style)
    style_btns.addWidget(window.btn_delete_style)
    style_btns.addWidget(window.btn_apply_style)
    style_btns.addStretch()
    custom_form.addRow("", style_btns)

    layout.addWidget(window.grp_custom_style)

    # --- Eight-Bar Style Group ---
    window.grp_eight_bar = QGroupBox()
    eight_bar_form = QFormLayout(window.grp_eight_bar)

    # Enable checkbox
    window.chk_eight_bar_enabled = QCheckBox()
    window.chk_eight_bar_enabled.setChecked(False)
    window.chk_eight_bar_enabled.stateChanged.connect(window._on_eight_bar_enabled_changed)
    window.lbl_eight_bar_enabled = QLabel()
    eight_bar_form.addRow(window.lbl_eight_bar_enabled, window.chk_eight_bar_enabled)

    # Mode selector
    window.cmb_eight_bar_mode = QComboBox()
    window.cmb_eight_bar_mode.addItem("Tempo Warp", "warp")
    window.cmb_eight_bar_mode.addItem("Beat-Lock", "beat_lock")
    window.cmb_eight_bar_mode.setCurrentIndex(0)
    window.lbl_eight_bar_mode = QLabel()
    eight_bar_form.addRow(window.lbl_eight_bar_mode, window.cmb_eight_bar_mode)

    # Selection pattern
    window.cmb_eight_bar_pattern = QComboBox()
    window.cmb_eight_bar_pattern.addItem("过三选一", "skip3_pick1")
    window.cmb_eight_bar_pattern.addItem("过二选一", "skip2_pick1")
    window.cmb_eight_bar_pattern.addItem("过一选一", "skip1_pick1")
    window.cmb_eight_bar_pattern.addItem("持续变化", "continuous")
    window.cmb_eight_bar_pattern.setCurrentIndex(1)
    window.lbl_eight_bar_pattern = QLabel()
    eight_bar_form.addRow(window.lbl_eight_bar_pattern, window.cmb_eight_bar_pattern)

    # Global clamp
    clamp_row = QHBoxLayout()
    window.chk_eight_bar_clamp = QCheckBox()
    window.chk_eight_bar_clamp.setChecked(False)
    window.lbl_eight_bar_clamp = QLabel()
    window.lbl_eight_bar_clamp_min = QLabel(tr("range_min", window.lang))
    window.sp_eight_bar_clamp_min = QSpinBox()
    window.sp_eight_bar_clamp_min.setRange(70, 130)
    window.sp_eight_bar_clamp_min.setValue(85)
    window.sp_eight_bar_clamp_min.setSuffix("%")
    window.lbl_eight_bar_clamp_max = QLabel(tr("range_max", window.lang))
    window.sp_eight_bar_clamp_max = QSpinBox()
    window.sp_eight_bar_clamp_max.setRange(70, 130)
    window.sp_eight_bar_clamp_max.setValue(115)
    window.sp_eight_bar_clamp_max.setSuffix("%")
    clamp_row.addWidget(window.chk_eight_bar_clamp)
    clamp_row.addWidget(window.lbl_eight_bar_clamp_min)
    clamp_row.addWidget(window.sp_eight_bar_clamp_min)
    clamp_row.addWidget(window.lbl_eight_bar_clamp_max)
    clamp_row.addWidget(window.sp_eight_bar_clamp_max)
    clamp_row.addStretch()
    eight_bar_form.addRow(window.lbl_eight_bar_clamp, clamp_row)

    # Speed variation range
    speed_row = QHBoxLayout()
    window.sp_speed_min = QSpinBox()
    window.sp_speed_min.setRange(70, 100)
    window.sp_speed_min.setValue(95)
    window.sp_speed_min.setSuffix("%")
    window.lbl_speed_min = QLabel(tr("range_min", window.lang))
    speed_row.addWidget(window.lbl_speed_min)
    speed_row.addWidget(window.sp_speed_min)
    window.sp_speed_max = QSpinBox()
    window.sp_speed_max.setRange(100, 130)
    window.sp_speed_max.setValue(105)
    window.sp_speed_max.setSuffix("%")
    window.lbl_speed_max = QLabel(tr("range_max", window.lang))
    speed_row.addWidget(window.lbl_speed_max)
    speed_row.addWidget(window.sp_speed_max)
    speed_row.addStretch()
    window.lbl_speed_var = QLabel()
    eight_bar_form.addRow(window.lbl_speed_var, speed_row)

    # Timing variation range
    timing_var_row = QHBoxLayout()
    window.sp_timing_var_min = QSpinBox()
    window.sp_timing_var_min.setRange(70, 100)
    window.sp_timing_var_min.setValue(90)
    window.sp_timing_var_min.setSuffix("%")
    window.lbl_timing_min = QLabel(tr("range_min", window.lang))
    timing_var_row.addWidget(window.lbl_timing_min)
    timing_var_row.addWidget(window.sp_timing_var_min)
    window.sp_timing_var_max = QSpinBox()
    window.sp_timing_var_max.setRange(100, 130)
    window.sp_timing_var_max.setValue(110)
    window.sp_timing_var_max.setSuffix("%")
    window.lbl_timing_max = QLabel(tr("range_max", window.lang))
    timing_var_row.addWidget(window.lbl_timing_max)
    timing_var_row.addWidget(window.sp_timing_var_max)
    timing_var_row.addStretch()
    window.lbl_timing_var = QLabel()
    eight_bar_form.addRow(window.lbl_timing_var, timing_var_row)

    # Duration variation range
    dur_var_row = QHBoxLayout()
    window.sp_dur_var_min = QSpinBox()
    window.sp_dur_var_min.setRange(70, 100)
    window.sp_dur_var_min.setValue(90)
    window.sp_dur_var_min.setSuffix("%")
    window.lbl_dur_min = QLabel(tr("range_min", window.lang))
    dur_var_row.addWidget(window.lbl_dur_min)
    dur_var_row.addWidget(window.sp_dur_var_min)
    window.sp_dur_var_max = QSpinBox()
    window.sp_dur_var_max.setRange(100, 130)
    window.sp_dur_var_max.setValue(110)
    window.sp_dur_var_max.setSuffix("%")
    window.lbl_dur_max = QLabel(tr("range_max", window.lang))
    dur_var_row.addWidget(window.lbl_dur_max)
    dur_var_row.addWidget(window.sp_dur_var_max)
    dur_var_row.addStretch()
    window.lbl_dur_var_8bar = QLabel()
    eight_bar_form.addRow(window.lbl_dur_var_8bar, dur_var_row)

    # Preset buttons
    preset_row = QHBoxLayout()
    window.btn_preset_subtle = QPushButton()
    window.btn_preset_moderate = QPushButton()
    window.btn_preset_dramatic = QPushButton()
    window.btn_preset_subtle.clicked.connect(lambda: window._apply_eight_bar_preset("subtle"))
    window.btn_preset_moderate.clicked.connect(lambda: window._apply_eight_bar_preset("moderate"))
    window.btn_preset_dramatic.clicked.connect(lambda: window._apply_eight_bar_preset("dramatic"))
    preset_row.addWidget(window.btn_preset_subtle)
    preset_row.addWidget(window.btn_preset_moderate)
    preset_row.addWidget(window.btn_preset_dramatic)
    preset_row.addStretch()
    window.lbl_eight_bar_preset = QLabel()
    eight_bar_form.addRow(window.lbl_eight_bar_preset, preset_row)

    # Show indicator checkbox
    window.chk_show_indicator = QCheckBox()
    window.chk_show_indicator.setChecked(True)
    window.lbl_show_indicator = QLabel()
    eight_bar_form.addRow(window.lbl_show_indicator, window.chk_show_indicator)

    layout.addWidget(window.grp_eight_bar)
    layout.addStretch()
    return tab


def build_errors_tab(window: "MainWindow") -> QWidget:
    """Build Tab 5: Error Settings tab and attach widgets to window."""
    tab = QWidget()
    layout = QVBoxLayout(tab)

    # Initialize error state
    window._error_enabled = False
    window._error_freq = 1
    window._enable_diagnostics = False

    # Enable error simulation
    err_enable_row = QHBoxLayout()
    window.chk_error_enabled = QCheckBox()
    window.lbl_error_enabled = QLabel(tr("enable_errors", window.lang))
    window.chk_error_enabled.stateChanged.connect(window._on_error_enabled_changed)
    err_enable_row.addWidget(window.chk_error_enabled)
    err_enable_row.addWidget(window.lbl_error_enabled)
    err_enable_row.addStretch()
    layout.addLayout(err_enable_row)

    # Error frequency
    freq_row = QHBoxLayout()
    window.lbl_error_freq = QLabel(tr("errors_per_8bars", window.lang))
    window.sp_error_freq = QSpinBox()
    window.sp_error_freq.setRange(1, 10)
    window.sp_error_freq.setValue(1)
    window.sp_error_freq.valueChanged.connect(window._on_error_freq_changed)
    freq_row.addWidget(window.lbl_error_freq)
    freq_row.addWidget(window.sp_error_freq)
    freq_row.addStretch()
    layout.addLayout(freq_row)

    # Error types group
    window.grp_error_types = QGroupBox(tr("error_types", window.lang))
    err_types_layout = QVBoxLayout(window.grp_error_types)

    window.chk_wrong_note = QCheckBox(tr("error_wrong_note", window.lang))
    window.chk_miss_note = QCheckBox(tr("error_miss_note", window.lang))
    window.chk_extra_note = QCheckBox(tr("error_extra_note", window.lang))
    window.chk_pause_error = QCheckBox(tr("error_pause", window.lang))

    window.chk_wrong_note.setChecked(True)
    window.chk_miss_note.setChecked(True)
    window.chk_extra_note.setChecked(True)
    window.chk_pause_error.setChecked(True)

    # Connect to sync back to Tab 1 quick checkboxes
    window.chk_wrong_note.stateChanged.connect(window._sync_tab5_to_quick_errors)
    window.chk_miss_note.stateChanged.connect(window._sync_tab5_to_quick_errors)
    window.chk_extra_note.stateChanged.connect(window._sync_tab5_to_quick_errors)
    window.chk_pause_error.stateChanged.connect(window._sync_tab5_to_quick_errors)

    err_types_layout.addWidget(window.chk_wrong_note)
    err_types_layout.addWidget(window.chk_miss_note)
    err_types_layout.addWidget(window.chk_extra_note)
    err_types_layout.addWidget(window.chk_pause_error)

    layout.addWidget(window.grp_error_types)

    # Pause duration settings
    pause_row = QHBoxLayout()
    window.lbl_pause_range = QLabel(tr("pause_duration", window.lang))
    window.sp_pause_min = QSpinBox()
    window.sp_pause_min.setRange(50, 1000)
    window.sp_pause_min.setValue(100)
    window.sp_pause_min.setSuffix(" ms")
    window.lbl_pause_to = QLabel(tr("range_to", window.lang))
    window.sp_pause_max = QSpinBox()
    window.sp_pause_max.setRange(50, 2000)
    window.sp_pause_max.setValue(500)
    window.sp_pause_max.setSuffix(" ms")
    pause_row.addWidget(window.lbl_pause_range)
    pause_row.addWidget(window.sp_pause_min)
    pause_row.addWidget(window.lbl_pause_to)
    pause_row.addWidget(window.sp_pause_max)
    pause_row.addStretch()
    layout.addLayout(pause_row)

    layout.addStretch()
    return tab
