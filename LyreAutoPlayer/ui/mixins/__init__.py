# ui/mixins - Mixin classes for MainWindow
# Extracted from main.py to separate concerns

from .config_mixin import ConfigMixin
from .playback_mixin import PlaybackMixin
from .settings_preset_mixin import SettingsPresetMixin
from .hotkeys_mixin import HotkeysMixin
from .language_mixin import LanguageMixin
from .logs_mixin import LogsMixin

__all__ = [
    'ConfigMixin',
    'PlaybackMixin',
    'SettingsPresetMixin',
    'HotkeysMixin',
    'LanguageMixin',
    'LogsMixin',
]
