# ui/mixins/config_mixin.py
# ConfigMixin - Configuration collection and settings persistence

import os
import json
from typing import TYPE_CHECKING

from core import SETTINGS_FILE
from player import PlayerConfig, ErrorConfig
from style_manager import (
    InputStyle, INPUT_STYLES, EightBarStyle, get_style, get_style_names, register_style
)
from i18n import LANG_EN, LANG_ZH, TRANSLATIONS

if TYPE_CHECKING:
    from main import MainWindow


class ConfigMixin:
    """Mixin for configuration collection and settings persistence."""

    def _sync_diagnostics_state(self: "MainWindow"):
        """Sync diagnostics button visibility and close window if disabled."""
        enabled = getattr(self, '_enable_diagnostics', False)
        self.btn_diagnostics.setVisible(enabled)
        # Close diagnostics window if disabled and currently open
        if not enabled and self.diagnostics_window is not None:
            self.diagnostics_window.close()
            self.diagnostics_window = None

    def collect_cfg(self: "MainWindow") -> PlayerConfig:
        """Collect current UI values into PlayerConfig."""
        # Check if strict mode is enabled
        strict_mode = getattr(self, '_strict_mode', False)
        if hasattr(self, 'chk_strict_mode'):
            strict_mode = self.chk_strict_mode.isChecked()

        # Build error config (feature removed from main GUI - always disabled)
        error_cfg = ErrorConfig(
            enabled=False,
            errors_per_8bars=0,
            wrong_note=False,
            miss_note=False,
            extra_note=False,
            pause_error=False,
            pause_min_ms=100,
            pause_max_ms=500,
        )

        octave_min = int(self.sp_octave_min.value())
        octave_max = int(self.sp_octave_max.value())
        if octave_min > octave_max:
            octave_min, octave_max = octave_max, octave_min

        # Build eight-bar style (disabled in strict mode)
        eight_bar = self._collect_eight_bar_style()
        if strict_mode:
            eight_bar.enabled = False

        # Get pause_every_bars from UI if available
        pause_every_bars = 0
        if hasattr(self, 'cmb_pause_bars'):
            pause_every_bars = self.cmb_pause_bars.currentData() or 0

        # Get auto_resume_countdown from UI if available
        auto_resume_countdown = 3
        if hasattr(self, 'sp_auto_resume_countdown'):
            auto_resume_countdown = self.sp_auto_resume_countdown.value()

        # Strict MIDI timing (disable humanization without forcing speed=1.0)
        strict_midi_timing = getattr(self, '_strict_midi_timing', False)
        if hasattr(self, 'chk_strict_midi_timing'):
            strict_midi_timing = self.chk_strict_midi_timing.isChecked()

        return PlayerConfig(
            root_mid_do=int(self.cmb_root.currentData()),
            octave_shift=int(self.cmb_octave.currentData()),
            transpose=int(self.sp_transpose.value()),
            speed=1.0 if strict_mode else float(self.sp_speed.value()),
            accidental_policy=str(self.cmb_policy.currentText()),
            enable_accidental_policy=hasattr(self, 'chk_enable_accidental_policy') and self.chk_enable_accidental_policy.isChecked(),
            octave_min_note=octave_min,
            octave_max_note=octave_max,
            octave_range_auto=self.chk_octave_range_auto.isChecked(),
            press_ms=int(self.sp_press.value()),
            use_midi_duration=True if (strict_mode or strict_midi_timing) else self.chk_midi_duration.isChecked(),
            keyboard_preset=str(self.cmb_preset.currentData()),
            countdown_sec=int(self.sp_countdown.value()),
            target_hwnd=self.cmb_window.currentData(),
            midi_path=self.mid_path or "",
            play_sound=self.chk_sound.isChecked(),
            soundfont_path=self.soundfont_path,
            instrument=str(self.cmb_instrument.currentText()),
            velocity=int(self.sp_velocity.value()),
            input_style="mechanical" if (strict_mode or strict_midi_timing) else self._current_input_style,
            error_config=error_cfg,
            enable_diagnostics=self._enable_diagnostics,
            eight_bar_style=eight_bar,
            strict_mode=strict_mode,
            strict_midi_timing=strict_midi_timing,
            pause_every_bars=pause_every_bars,
            auto_resume_countdown=auto_resume_countdown,
            # Late-drop policy for output scheduler
            late_drop_ms=self.sp_late_drop_ms.value() if hasattr(self, 'sp_late_drop_ms') else 25.0,
            enable_late_drop=hasattr(self, 'chk_late_drop') and self.chk_late_drop.isChecked(),
        )

    def _collect_eight_bar_style(self: "MainWindow") -> EightBarStyle:
        """Return default disabled eight-bar style (feature removed from main GUI)."""
        return EightBarStyle(
            enabled=False,
            mode="warp",
            selection_pattern="skip2_pick1",
            speed_mult_min=0.95,
            speed_mult_max=1.05,
            timing_mult_min=0.95,
            timing_mult_max=1.05,
            duration_mult_min=0.95,
            duration_mult_max=1.05,
            clamp_enabled=False,
            clamp_min=0.85,
            clamp_max=1.15,
            show_indicator=False,
        )

    def save_settings(self: "MainWindow"):
        """Save user settings to JSON file (unified nested structure)."""
        # Use _collect_current_settings for unified structure
        settings = self._collect_current_settings()

        # Add custom styles (non-builtin, excluding plugin styles which are auto-loaded)
        custom_styles = []
        for name in get_style_names():
            style = get_style(name)
            if style and not style.builtin:
                custom_styles.append({
                    "name": style.name,
                    "timing_offset_ms": list(style.timing_offset_ms),
                    "stagger_ms": style.stagger_ms,
                    "duration_variation": style.duration_variation,
                    "description_en": style.description_en,
                    "description_zh": style.description_zh,
                })
        settings["custom_styles"] = custom_styles

        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.append_log(f"[WARN] Failed to save settings: {e}")

    def load_settings(self: "MainWindow"):
        """Load user settings from JSON file with backward compatibility."""
        if not os.path.exists(SETTINGS_FILE):
            return

        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            # Migrate old flat format to nested format
            settings = self._migrate_settings(settings)

            # Load custom styles first (before applying input_style selection)
            if "custom_styles" in settings:
                for style_data in settings["custom_styles"]:
                    name = style_data.get("name")
                    # Skip if style already exists (e.g., plugin styles)
                    if name and name not in INPUT_STYLES:
                        custom_style = InputStyle(
                            name=name,
                            timing_offset_ms=tuple(style_data.get("timing_offset_ms", (0, 0))),
                            stagger_ms=style_data.get("stagger_ms", 0),
                            duration_variation=style_data.get("duration_variation", 0.0),
                            description_en=style_data.get("description_en", name),
                            description_zh=style_data.get("description_zh", name),
                            builtin=False,
                        )
                        register_style(custom_style)
                        # Add translation for the style
                        TRANSLATIONS[f"style_{name}"] = {
                            LANG_EN: custom_style.description_en,
                            LANG_ZH: custom_style.description_zh
                        }

            # Apply language
            if "language" in settings:
                lang = settings["language"]
                for i in range(self.cmb_lang.count()):
                    if self.cmb_lang.itemData(i) == lang:
                        self.cmb_lang.setCurrentIndex(i)
                        break

            # Apply root note
            if "root_note" in settings:
                for i in range(self.cmb_root.count()):
                    if self.cmb_root.itemData(i) == settings["root_note"]:
                        self.cmb_root.setCurrentIndex(i)
                        break

            # Apply octave shift
            if "octave_shift" in settings:
                for i in range(self.cmb_octave.count()):
                    if self.cmb_octave.itemData(i) == settings["octave_shift"]:
                        self.cmb_octave.setCurrentIndex(i)
                        break

            # Apply octave range mode
            if "octave_range_auto" in settings:
                self.chk_octave_range_auto.setChecked(bool(settings["octave_range_auto"]))

            # Apply octave range
            if "octave_range" in settings:
                oct_range = settings["octave_range"]
                if "min" in oct_range:
                    self.sp_octave_min.setValue(oct_range["min"])
                if "max" in oct_range:
                    self.sp_octave_max.setValue(oct_range["max"])

            # Apply transpose
            if "transpose" in settings:
                self.sp_transpose.setValue(settings["transpose"])
            if "accidental_policy" in settings and hasattr(self, 'cmb_policy'):
                policy = settings["accidental_policy"]
                for i in range(self.cmb_policy.count()):
                    if self.cmb_policy.itemText(i) == policy:
                        self.cmb_policy.setCurrentIndex(i)
                        break
            if "enable_accidental_policy" in settings and hasattr(self, 'chk_enable_accidental_policy'):
                self.chk_enable_accidental_policy.setChecked(bool(settings["enable_accidental_policy"]))

            # Apply numeric settings
            if "speed" in settings:
                self.sp_speed.setValue(settings["speed"])
            if "press_ms" in settings:
                self.sp_press.setValue(settings["press_ms"])
            if "countdown_sec" in settings:
                self.sp_countdown.setValue(settings["countdown_sec"])
            if "velocity" in settings:
                self.sp_velocity.setValue(settings["velocity"])

            # Apply keyboard preset
            if "keyboard_preset" in settings:
                for i in range(self.cmb_preset.count()):
                    if self.cmb_preset.itemData(i) == settings["keyboard_preset"]:
                        self.cmb_preset.setCurrentIndex(i)
                        break

            # Apply checkboxes
            if "use_midi_duration" in settings:
                self.chk_midi_duration.setChecked(settings["use_midi_duration"])
            if "play_sound" in settings:
                self.chk_sound.setChecked(settings["play_sound"])

            # Apply input style (only store the value - UI controls removed from main GUI)
            if "input_style" in settings:
                style_name = settings["input_style"]
                self._current_input_style = style_name

            # Apply soundfont path
            if "soundfont_path" in settings and settings["soundfont_path"]:
                if os.path.exists(settings["soundfont_path"]):
                    self.soundfont_path = settings["soundfont_path"]
                    self.lbl_soundfont.setText(os.path.basename(self.soundfont_path))

            # Apply last MIDI path
            if "last_midi_path" in settings and settings["last_midi_path"]:
                if os.path.exists(settings["last_midi_path"]):
                    path = settings["last_midi_path"]
                    try:
                        from player import midi_to_events_with_duration
                        self.events = midi_to_events_with_duration(path)
                        self.mid_path = path
                        self.lbl_file.setText(f"{path}  (notes: {len(self.events)})")
                    except Exception:
                        pass  # Silently ignore if MIDI file can't be loaded

            # Apply diagnostics
            if "enable_diagnostics" in settings:
                self._enable_diagnostics = settings["enable_diagnostics"]
                # Control diagnostics button visibility based on setting
                self.btn_diagnostics.setVisible(self._enable_diagnostics)
                if hasattr(self, 'chk_enable_diagnostics'):
                    self.chk_enable_diagnostics.setChecked(self._enable_diagnostics)

            # Apply input_manager params
            if "input_manager" in settings:
                self._input_manager_params = settings["input_manager"]

            # Apply error_config (feature removed from main GUI - just store internal state)
            if "error_config" in settings:
                ec = settings["error_config"]
                if "enabled" in ec:
                    self._error_enabled = ec["enabled"]
                if "errors_per_8bars" in ec:
                    self._error_freq = ec["errors_per_8bars"]

            # Apply eight_bar_config (feature removed from main GUI - skip widget updates)

            # Apply strict_mode_config (nested structure)
            if "strict_mode_config" in settings:
                smc = settings["strict_mode_config"]
                if "enabled" in smc and hasattr(self, 'chk_strict_mode'):
                    self.chk_strict_mode.setChecked(smc["enabled"])
                    self._strict_mode = smc["enabled"]
                if "strict_midi_timing" in smc and hasattr(self, 'chk_strict_midi_timing'):
                    self.chk_strict_midi_timing.setChecked(smc["strict_midi_timing"])
                    self._strict_midi_timing = smc["strict_midi_timing"]
                if "pause_every_bars" in smc and hasattr(self, 'cmb_pause_bars'):
                    pause_bars = smc["pause_every_bars"]
                    for i in range(self.cmb_pause_bars.count()):
                        if self.cmb_pause_bars.itemData(i) == pause_bars:
                            self.cmb_pause_bars.setCurrentIndex(i)
                            break
                if "auto_resume_countdown" in smc and hasattr(self, 'sp_auto_resume_countdown'):
                    self.sp_auto_resume_countdown.setValue(smc["auto_resume_countdown"])
                if "enable_late_drop" in smc and hasattr(self, 'chk_late_drop'):
                    self.chk_late_drop.setChecked(smc["enable_late_drop"])
                if "late_drop_ms" in smc and hasattr(self, 'sp_late_drop_ms'):
                    self.sp_late_drop_ms.setValue(smc["late_drop_ms"])

            # Unconditionally sync diagnostics state after loading
            self._sync_diagnostics_state()

            self.append_log("[OK] Settings loaded")

        except Exception as e:
            self.append_log(f"[WARN] Failed to load settings: {e}")

    def _migrate_settings(self: "MainWindow", settings: dict) -> dict:
        """Migrate old flat format to new nested format for backward compatibility."""
        # Migrate countdown -> countdown_sec
        if "countdown" in settings and "countdown_sec" not in settings:
            settings["countdown_sec"] = settings.pop("countdown")

        # Migrate flat error fields to error_config
        if "error_config" not in settings:
            error_config = {}
            flat_to_nested = {
                "error_enabled": "enabled",
                "error_freq": "errors_per_8bars",
                "error_wrong_note": "wrong_note",
                "error_miss_note": "miss_note",
                "error_extra_note": "extra_note",
                "error_pause": "pause_error",
                "pause_min_ms": "pause_min_ms",
                "pause_max_ms": "pause_max_ms",
            }
            for flat_key, nested_key in flat_to_nested.items():
                if flat_key in settings:
                    error_config[nested_key] = settings.pop(flat_key)
            if error_config:
                settings["error_config"] = error_config

        # Migrate flat eight_bar fields to eight_bar_config
        if "eight_bar_config" not in settings:
            eight_bar_config = {}
            flat_to_nested = {
                "eight_bar_enabled": "enabled",
                "eight_bar_mode": "mode",
                "eight_bar_pattern": "pattern",
                "eight_bar_speed_min": "speed_min",
                "eight_bar_speed_max": "speed_max",
                "eight_bar_timing_min": "timing_min",
                "eight_bar_timing_max": "timing_max",
                "eight_bar_duration_min": "duration_min",
                "eight_bar_duration_max": "duration_max",
                "eight_bar_show_indicator": "show_indicator",
            }
            for flat_key, nested_key in flat_to_nested.items():
                if flat_key in settings:
                    eight_bar_config[nested_key] = settings.pop(flat_key)
            if eight_bar_config:
                settings["eight_bar_config"] = eight_bar_config
        if "eight_bar_config" in settings:
            settings["eight_bar_config"].setdefault("clamp_enabled", False)
            settings["eight_bar_config"].setdefault("clamp_min", 85)
            settings["eight_bar_config"].setdefault("clamp_max", 115)

        # Migrate flat octave range fields to octave_range
        if "octave_range" not in settings:
            octave_range = {}
            if "octave_min_note" in settings:
                octave_range["min"] = settings.pop("octave_min_note")
            if "octave_max_note" in settings:
                octave_range["max"] = settings.pop("octave_max_note")
            if octave_range:
                settings["octave_range"] = octave_range

        if "octave_range_auto" not in settings:
            settings["octave_range_auto"] = False

        # Set default version if missing
        if "version" not in settings:
            settings["version"] = 1

        # Set default transpose if missing
        if "transpose" not in settings:
            settings["transpose"] = 0

        return settings
