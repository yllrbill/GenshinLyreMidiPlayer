# -*- coding: utf-8 -*-
"""
Configuration Management Module.

This module provides a unified interface for configuration access,
wrapping the existing settings_manager with additional conveniences.

Usage:
    from core.config import ConfigManager, get_config

    config = get_config()
    config.load()

    # Access settings
    speed = config.settings.speed
    language = config.settings.language

    # Save changes
    config.save()
"""

import os
from typing import Optional, Any

# Import the existing settings manager
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings_manager import (
    SettingsManager,
    SettingsSchema,
    ErrorConfigParams,
    InputManagerParams,
    InputStyleParams,
    BUILTIN_PRESETS,
    SETTINGS_VERSION,
    create_settings_manager,
)

# Re-export for convenience
__all__ = [
    'ConfigManager',
    'get_config',
    'SettingsSchema',
    'ErrorConfigParams',
    'InputManagerParams',
    'InputStyleParams',
    'BUILTIN_PRESETS',
    'SETTINGS_VERSION',
]


class ConfigManager:
    """
    Configuration Manager.

    Wraps SettingsManager with additional conveniences:
    - Singleton pattern for global access
    - Simplified get/set API
    - Domain-based access (playback, sound, error, etc.)
    """

    _instance: Optional['ConfigManager'] = None

    def __init__(self, settings_file: str):
        """
        Initialize ConfigManager.

        Args:
            settings_file: Path to settings.json file
        """
        self._manager = SettingsManager(settings_file)
        self._loaded = False

    @classmethod
    def get_instance(cls, settings_file: str = None) -> 'ConfigManager':
        """
        Get singleton instance.

        Args:
            settings_file: Path to settings file (only used on first call)

        Returns:
            ConfigManager instance
        """
        if cls._instance is None:
            if settings_file is None:
                # Default path
                script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                settings_file = os.path.join(script_dir, "settings.json")
            cls._instance = cls(settings_file)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)."""
        cls._instance = None

    @property
    def settings(self) -> SettingsSchema:
        """Access the settings schema directly."""
        return self._manager.settings

    def load(self) -> bool:
        """Load settings from file."""
        result = self._manager.load()
        self._loaded = True
        return result

    def save(self) -> bool:
        """Save settings to file."""
        return self._manager.save()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.

        Args:
            key: Setting key (e.g., 'speed', 'language')
            default: Default value if key not found

        Returns:
            Setting value
        """
        return getattr(self._manager.settings, key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Set a setting value by key.

        Args:
            key: Setting key
            value: New value

        Returns:
            True if successful
        """
        if hasattr(self._manager.settings, key):
            setattr(self._manager.settings, key, value)
            self._manager._dirty = True
            return True
        return False

    # ============== Domain Accessors ==============

    @property
    def playback(self) -> dict:
        """Get playback-related settings as dict."""
        s = self._manager.settings
        return {
            'root_note': s.root_note,
            'octave_shift': s.octave_shift,
            'transpose': s.transpose,
            'speed': s.speed,
            'press_ms': s.press_ms,
            'countdown_sec': s.countdown_sec,
            'keyboard_preset': s.keyboard_preset,
            'use_midi_duration': s.use_midi_duration,
        }

    @property
    def sound(self) -> dict:
        """Get sound-related settings as dict."""
        s = self._manager.settings
        return {
            'play_sound': s.play_sound,
            'soundfont_path': s.soundfont_path,
            'instrument': s.instrument,
            'velocity': s.velocity,
        }

    @property
    def error_config(self) -> ErrorConfigParams:
        """Get error simulation config."""
        return self._manager.settings.error_config

    @property
    def input_manager_config(self) -> InputManagerParams:
        """Get input manager config."""
        return self._manager.settings.input_manager

    # ============== Delegated Methods ==============

    def apply_preset(self, preset_name: str) -> bool:
        """Apply a built-in preset."""
        return self._manager.apply_preset(preset_name)

    def reset_to_defaults(self):
        """Reset to default settings."""
        self._manager.reset_to_defaults()

    def get_preset_list(self):
        """Get list of available presets."""
        return self._manager.get_preset_list()

    def validate(self):
        """Validate settings, return list of errors."""
        return self._manager.validate()

    def export_to_file(self, filepath: str) -> bool:
        """Export settings to file."""
        return self._manager.export_to_file(filepath)

    def import_from_file(self, filepath: str):
        """Import settings from file."""
        return self._manager.import_from_file(filepath)


# Convenience function
def get_config(settings_file: str = None) -> ConfigManager:
    """
    Get the global ConfigManager instance.

    Args:
        settings_file: Path to settings file (only used on first call)

    Returns:
        ConfigManager instance
    """
    return ConfigManager.get_instance(settings_file)
