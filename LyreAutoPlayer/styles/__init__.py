"""
Styles Plugin System

Provides extensible input style definitions for humanization.
Drop a .py file into styles/plugins/ to add custom styles.
"""

from .registry import InputStyle, StyleRegistry
from .loader import load_plugins, get_default_registry

__all__ = ["InputStyle", "StyleRegistry", "load_plugins", "get_default_registry"]
