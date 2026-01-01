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
            self._select_style_in_combo(self.cmb_input_style, style_name)
            self._select_style_in_combo(self.cmb_style_tab, style_name)
            self._update_style_params_display(style_name)

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

        if 'error_config' in preset_settings:
            ec = preset_settings['error_config']
            if 'enabled' in ec:
                self._error_enabled = ec['enabled']
                self.chk_error_enabled.setChecked(ec['enabled'])
                self.chk_quick_error_enable.setChecked(ec['enabled'])
            if 'errors_per_8bars' in ec:
                self._error_freq = ec['errors_per_8bars']
                self.sp_error_freq.setValue(ec['errors_per_8bars'])
            if 'wrong_note' in ec:
                self.chk_wrong_note.setChecked(ec['wrong_note'])
                self.chk_quick_wrong.setChecked(ec['wrong_note'])
            if 'miss_note' in ec:
                self.chk_miss_note.setChecked(ec['miss_note'])
                self.chk_quick_miss.setChecked(ec['miss_note'])

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

        self._current_input_style = 'mechanical'
        self._select_style_in_combo(self.cmb_input_style, 'mechanical')
        self._select_style_in_combo(self.cmb_style_tab, 'mechanical')
        self._update_style_params_display('mechanical')

        self._error_enabled = False
        self._error_freq = 1
        self.chk_error_enabled.setChecked(False)
        self.chk_quick_error_enable.setChecked(False)
        self.sp_error_freq.setValue(1)
        self.chk_eight_bar_clamp.setChecked(False)
        self.sp_eight_bar_clamp_min.setValue(85)
        self.sp_eight_bar_clamp_max.setValue(115)

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
            "error_config": {
                "enabled": self._error_enabled,
                "errors_per_8bars": self._error_freq,
                "wrong_note": self.chk_wrong_note.isChecked(),
                "miss_note": self.chk_miss_note.isChecked(),
                "extra_note": self.chk_extra_note.isChecked(),
                "pause_error": self.chk_pause_error.isChecked(),
                "pause_min_ms": self.sp_pause_min.value(),
                "pause_max_ms": self.sp_pause_max.value(),
            },
            "eight_bar_config": {
                "enabled": self.chk_eight_bar_enabled.isChecked(),
                "mode": self.cmb_eight_bar_mode.currentData() or "warp",
                "pattern": self.cmb_eight_bar_pattern.currentData() or "skip2_pick1",
                "speed_min": self.sp_speed_min.value(),
                "speed_max": self.sp_speed_max.value(),
                "timing_min": self.sp_timing_var_min.value(),
                "timing_max": self.sp_timing_var_max.value(),
                "duration_min": self.sp_dur_var_min.value(),
                "duration_max": self.sp_dur_var_max.value(),
                "clamp_enabled": self.chk_eight_bar_clamp.isChecked(),
                "clamp_min": self.sp_eight_bar_clamp_min.value(),
                "clamp_max": self.sp_eight_bar_clamp_max.value(),
                "show_indicator": self.chk_show_indicator.isChecked(),
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

        if "input_style" in settings:
            style_name = settings["input_style"]
            self._current_input_style = style_name
            self._select_style_in_combo(self.cmb_input_style, style_name)
            self._select_style_in_combo(self.cmb_style_tab, style_name)
            self._update_style_params_display(style_name)

        if "error_config" in settings:
            ec = settings["error_config"]
            if "enabled" in ec:
                self._error_enabled = ec["enabled"]
                self.chk_error_enabled.setChecked(ec["enabled"])
                self.chk_quick_error_enable.setChecked(ec["enabled"])
            if "errors_per_8bars" in ec:
                self._error_freq = ec["errors_per_8bars"]
                self.sp_error_freq.setValue(ec["errors_per_8bars"])
            if "wrong_note" in ec:
                self.chk_wrong_note.setChecked(ec["wrong_note"])
                self.chk_quick_wrong.setChecked(ec["wrong_note"])
            if "miss_note" in ec:
                self.chk_miss_note.setChecked(ec["miss_note"])
                self.chk_quick_miss.setChecked(ec["miss_note"])
            if "extra_note" in ec:
                self.chk_extra_note.setChecked(ec["extra_note"])
                self.chk_quick_extra.setChecked(ec["extra_note"])
            if "pause_error" in ec:
                self.chk_pause_error.setChecked(ec["pause_error"])
                self.chk_quick_pause.setChecked(ec["pause_error"])
            if "pause_min_ms" in ec:
                self.sp_pause_min.setValue(ec["pause_min_ms"])
            if "pause_max_ms" in ec:
                self.sp_pause_max.setValue(ec["pause_max_ms"])

        if "input_manager" in settings:
            self._input_manager_params = settings["input_manager"]

        if "enable_diagnostics" in settings:
            self._enable_diagnostics = settings["enable_diagnostics"]
        # Unconditionally sync diagnostics state after preset apply
        self._sync_diagnostics_state()

        # Apply eight_bar_config (nested structure)
        if "eight_bar_config" in settings:
            ebc = settings["eight_bar_config"]
            if "enabled" in ebc:
                self.chk_eight_bar_enabled.setChecked(ebc["enabled"])
                self.chk_quick_eight_bar.setChecked(ebc["enabled"])
            if "mode" in ebc:
                mode = ebc["mode"]
                for i in range(self.cmb_eight_bar_mode.count()):
                    if self.cmb_eight_bar_mode.itemData(i) == mode:
                        self.cmb_eight_bar_mode.setCurrentIndex(i)
                        break
            if "pattern" in ebc:
                pattern = ebc["pattern"]
                for i in range(self.cmb_eight_bar_pattern.count()):
                    if self.cmb_eight_bar_pattern.itemData(i) == pattern:
                        self.cmb_eight_bar_pattern.setCurrentIndex(i)
                        break
            if "speed_min" in ebc:
                self.sp_speed_min.setValue(ebc["speed_min"])
            if "speed_max" in ebc:
                self.sp_speed_max.setValue(ebc["speed_max"])
            if "timing_min" in ebc:
                self.sp_timing_var_min.setValue(ebc["timing_min"])
            if "timing_max" in ebc:
                self.sp_timing_var_max.setValue(ebc["timing_max"])
            if "duration_min" in ebc:
                self.sp_dur_var_min.setValue(ebc["duration_min"])
            if "duration_max" in ebc:
                self.sp_dur_var_max.setValue(ebc["duration_max"])
            if "clamp_enabled" in ebc:
                self.chk_eight_bar_clamp.setChecked(ebc["clamp_enabled"])
            if "clamp_min" in ebc:
                self.sp_eight_bar_clamp_min.setValue(ebc["clamp_min"])
            if "clamp_max" in ebc:
                self.sp_eight_bar_clamp_max.setValue(ebc["clamp_max"])
            if "show_indicator" in ebc:
                self.chk_show_indicator.setChecked(ebc["show_indicator"])
