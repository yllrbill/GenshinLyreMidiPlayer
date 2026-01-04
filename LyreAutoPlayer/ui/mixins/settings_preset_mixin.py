# ui/mixins/settings_preset_mixin.py
# SettingsPresetMixin - Settings preset and keyboard preset methods

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from settings_manager import BUILTIN_PRESETS
from i18n import tr, LANG_ZH

if TYPE_CHECKING:
    from main import MainWindow


class SettingsPresetMixin:
    """Mixin for settings preset and keyboard preset methods."""

    def _rebuild_settings_preset_combo(self: "MainWindow"):
        """Populate the settings preset combo box from BUILTIN_PRESETS."""
        self.cmb_settings_preset.blockSignals(True)
        self.cmb_settings_preset.clear()
        for key, preset in BUILTIN_PRESETS.items():
            name = preset['name_zh'] if self.lang == LANG_ZH else preset['name_en']
            desc = preset['description_zh'] if self.lang == LANG_ZH else preset['description_en']
            display = f"{name} - {desc}"
            self.cmb_settings_preset.addItem(display, key)
        self.cmb_settings_preset.blockSignals(False)

    def on_apply_settings_preset(self: "MainWindow"):
        """Apply selected settings preset from BUILTIN_PRESETS."""
        preset_key = self.cmb_settings_preset.currentData()
        if not preset_key or preset_key not in BUILTIN_PRESETS:
            return

        preset = BUILTIN_PRESETS[preset_key]
        preset_settings = preset.get('settings', {})

        # Apply settings from preset
        if 'input_style' in preset_settings:
            style_name = preset_settings['input_style']
            self._current_input_style = style_name

        if 'press_ms' in preset_settings:
            self.sp_press.setValue(preset_settings['press_ms'])

        if 'use_midi_duration' in preset_settings:
            self.chk_midi_duration.setChecked(preset_settings['use_midi_duration'])

        if 'keyboard_preset' in preset_settings:
            kb_preset = preset_settings['keyboard_preset']
            for i in range(self.cmb_preset.count()):
                if self.cmb_preset.itemData(i) == kb_preset:
                    self.cmb_preset.setCurrentIndex(i)
                    break

        if 'input_manager' in preset_settings:
            im = preset_settings['input_manager']
            # Store for later use when creating InputManager
            if not hasattr(self, '_input_manager_params'):
                self._input_manager_params = {}
            self._input_manager_params.update(im)

        # Error config - feature removed from main GUI, just store internal state
        if 'error_config' in preset_settings:
            ec = preset_settings['error_config']
            if 'enabled' in ec:
                self._error_enabled = ec['enabled']
            if 'errors_per_8bars' in ec:
                self._error_freq = ec['errors_per_8bars']

        name = preset['name_zh'] if self.lang == LANG_ZH else preset['name_en']
        self.append_log(f"[OK] {tr('preset_applied', self.lang)}: {name}")

    def on_reset_defaults(self: "MainWindow"):
        """Reset all settings to defaults after user confirmation."""
        reply = QMessageBox.question(
            self,
            tr('reset_defaults', self.lang),
            tr('reset_confirm', self.lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Reset to defaults
        self.cmb_root.setCurrentIndex(1)  # C4
        self.cmb_octave.setCurrentIndex(2)  # 0
        self.sp_octave_min.setValue(36)
        self.sp_octave_max.setValue(84)
        self.chk_octave_range_auto.setChecked(False)
        self.sp_transpose.setValue(0)
        self.sp_speed.setValue(1.0)
        self.sp_press.setValue(25)
        self.sp_countdown.setValue(2)
        self.cmb_preset.setCurrentIndex(0)  # 21-key
        self.chk_midi_duration.setChecked(False)
        self.chk_sound.setChecked(False)
        self.sp_velocity.setValue(90)

        # Input style - just store internal state (UI controls removed from main GUI)
        self._current_input_style = 'mechanical'

        # Error config - feature removed from main GUI
        self._error_enabled = False
        self._error_freq = 1

        self.append_log(f"[OK] {tr('reset_defaults', self.lang)}")

    def on_preset_changed(self: "MainWindow", index: int):
        """Called when main tab keyboard preset combo box changes."""
        # Sync keyboard tab combobox (block signals to avoid recursion)
        self.cmb_kb_preset.blockSignals(True)
        self.cmb_kb_preset.setCurrentIndex(index)
        self.cmb_kb_preset.blockSignals(False)
        self._build_keyboard_display()

    def on_kb_preset_changed(self: "MainWindow", index: int):
        """Called when keyboard tab preset combo box changes."""
        # Sync main tab combobox (block signals to avoid recursion)
        self.cmb_preset.blockSignals(True)
        self.cmb_preset.setCurrentIndex(index)
        self.cmb_preset.blockSignals(False)
        self._build_keyboard_display()

    def _collect_current_settings(self: "MainWindow") -> dict:
        """Collect current UI settings into a dictionary (unified nested structure)."""
        return {
            "version": getattr(self, 'SETTINGS_VERSION', 1),
            "language": self.lang,
            "root_note": self.cmb_root.currentData(),
            "octave_shift": self.cmb_octave.currentData(),
            "octave_range": {
                "min": self.sp_octave_min.value(),
                "max": self.sp_octave_max.value(),
            },
            "octave_range_auto": self.chk_octave_range_auto.isChecked(),
            "transpose": self.sp_transpose.value(),
            "speed": self.sp_speed.value(),
            "press_ms": self.sp_press.value(),
            "countdown_sec": self.sp_countdown.value(),
            "keyboard_preset": self.cmb_preset.currentData(),
            "use_midi_duration": self.chk_midi_duration.isChecked(),
            "play_sound": self.chk_sound.isChecked(),
            "velocity": self.sp_velocity.value(),
            "input_style": getattr(self, '_current_input_style', 'mechanical'),
            "enable_diagnostics": getattr(self, '_enable_diagnostics', False),
            "soundfont_path": getattr(self, 'soundfont_path', '') or '',
            "last_midi_path": getattr(self, 'mid_path', '') or '',
            "input_manager": getattr(self, '_input_manager_params', {}),
            # Error config - feature removed from main GUI, use stored state
            "error_config": {
                "enabled": getattr(self, '_error_enabled', False),
                "errors_per_8bars": getattr(self, '_error_freq', 0),
                "wrong_note": False,
                "miss_note": False,
                "extra_note": False,
                "pause_error": False,
                "pause_min_ms": 100,
                "pause_max_ms": 500,
            },
            # Eight-bar config - feature removed from main GUI
            "eight_bar_config": {
                "enabled": False,
                "mode": "warp",
                "pattern": "skip2_pick1",
                "speed_min": 95,
                "speed_max": 105,
                "timing_min": 95,
                "timing_max": 105,
                "duration_min": 95,
                "duration_max": 105,
                "clamp_enabled": False,
                "clamp_min": 85,
                "clamp_max": 115,
                "show_indicator": False,
            },
            "strict_mode_config": {
                "enabled": hasattr(self, 'chk_strict_mode') and self.chk_strict_mode.isChecked(),
                "pause_every_bars": self.cmb_pause_bars.currentData() if hasattr(self, 'cmb_pause_bars') else 0,
                "auto_resume_countdown": self.sp_auto_resume_countdown.value() if hasattr(self, 'sp_auto_resume_countdown') else 3,
            },
        }

    def _apply_settings_dict(self: "MainWindow", settings: dict):
        """Apply settings from a dictionary to UI."""
        if "language" in settings:
            lang = settings["language"]
            for i in range(self.cmb_lang.count()):
                if self.cmb_lang.itemData(i) == lang or self.cmb_lang.itemText(i) == lang:
                    self.cmb_lang.setCurrentIndex(i)
                    break

        if "root_note" in settings:
            for i in range(self.cmb_root.count()):
                if self.cmb_root.itemData(i) == settings["root_note"]:
                    self.cmb_root.setCurrentIndex(i)
                    break

        if "octave_shift" in settings:
            for i in range(self.cmb_octave.count()):
                if self.cmb_octave.itemData(i) == settings["octave_shift"]:
                    self.cmb_octave.setCurrentIndex(i)
                    break

        if "octave_range" in settings:
            oct_range = settings["octave_range"]
            if "min" in oct_range:
                self.sp_octave_min.setValue(oct_range["min"])
            if "max" in oct_range:
                self.sp_octave_max.setValue(oct_range["max"])
        if "octave_range_auto" in settings:
            self.chk_octave_range_auto.setChecked(bool(settings["octave_range_auto"]))

        if "transpose" in settings:
            self.sp_transpose.setValue(settings["transpose"])
        if "speed" in settings:
            self.sp_speed.setValue(settings["speed"])
        if "press_ms" in settings:
            self.sp_press.setValue(settings["press_ms"])
        if "countdown_sec" in settings:
            self.sp_countdown.setValue(settings["countdown_sec"])
        if "velocity" in settings:
            self.sp_velocity.setValue(settings["velocity"])

        if "keyboard_preset" in settings:
            for i in range(self.cmb_preset.count()):
                if self.cmb_preset.itemData(i) == settings["keyboard_preset"]:
                    self.cmb_preset.setCurrentIndex(i)
                    break

        if "use_midi_duration" in settings:
            self.chk_midi_duration.setChecked(settings["use_midi_duration"])
        if "play_sound" in settings:
            self.chk_sound.setChecked(settings["play_sound"])

        # Input style - just store internal state (UI controls removed from main GUI)
        if "input_style" in settings:
            self._current_input_style = settings["input_style"]

        # Error config - feature removed from main GUI, just store internal state
        if "error_config" in settings:
            ec = settings["error_config"]
            if "enabled" in ec:
                self._error_enabled = ec["enabled"]
            if "errors_per_8bars" in ec:
                self._error_freq = ec["errors_per_8bars"]

        if "input_manager" in settings:
            self._input_manager_params = settings["input_manager"]

        if "enable_diagnostics" in settings:
            self._enable_diagnostics = settings["enable_diagnostics"]
        # Unconditionally sync diagnostics state after preset apply
        self._sync_diagnostics_state()

        # Eight-bar config - feature removed from main GUI, skip widget updates
