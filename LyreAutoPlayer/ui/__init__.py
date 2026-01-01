# -*- coding: utf-8 -*-
"""
UI module for LyreAutoPlayer.

Contains:
- floating: FloatingController for always-on-top control panel
- diagnostics_window: DiagnosticsWindow for input diagnostics
- main_window: MainWindow main application window
- constants: UI-related constants (ROOT_CHOICES, etc.)
- editor: MIDI Editor (EditorWindow)
"""

from .floating import FloatingController
from .diagnostics_window import DiagnosticsWindow
from .constants import ROOT_CHOICES
from .editor import EditorWindow

__all__ = [
    'FloatingController',
    'DiagnosticsWindow',
    'ROOT_CHOICES',
    'EditorWindow',
]
