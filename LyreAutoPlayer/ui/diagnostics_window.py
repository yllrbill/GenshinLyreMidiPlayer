# -*- coding: utf-8 -*-
"""
DiagnosticsWindow - Input diagnostics window for debugging key events.

Features:
- Real-time key event logging with timestamps
- Source annotation (Hotkey/Playback/Manual)
- Filter modes: All keys / Non-F keys / Non-function keys
- Copy support and auto-scroll
- Clear on stop button
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox,
    QPushButton, QLabel, QCheckBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QTextCursor, QFont

from i18n import tr

if TYPE_CHECKING:
    from main import MainWindow


class KeySource(Enum):
    """Source of key event."""
    HOTKEY = "hotkey"       # Global hotkey (F5-F12)
    PLAYBACK = "playback"   # Playback output (SendInput)
    MANUAL = "manual"       # User manual input (keyboard listener)
    UNKNOWN = "unknown"     # Unknown source


class FilterMode(Enum):
    """Filter mode for key events."""
    ALL = "all"             # Show all keys
    NON_F_KEYS = "non_f"    # Hide F1-F12 keys
    NON_FUNCTION = "non_fn" # Hide all function keys (F1-F12, Esc, PrtSc, etc.)


# F-keys to filter
F_KEYS = frozenset([f"F{i}" for i in range(1, 13)])

# All function keys to filter
FUNCTION_KEYS = F_KEYS | frozenset([
    "Escape", "Esc", "PrintScreen", "PrtSc", "ScrollLock", "Pause",
    "Insert", "Delete", "Home", "End", "PageUp", "PageDown",
    "NumLock", "CapsLock"
])


class DiagnosticsWindow(QWidget):
    """Input diagnostics window for debugging key events."""

    # Signal to log a key event from external sources
    sig_log_key = pyqtSignal(str, str, str)  # (key_name, action, source)

    def __init__(self, parent: "MainWindow", lang: str = "English"):
        super().__init__()
        self.main_window = parent
        self.lang = lang
        self._filter_mode = FilterMode.ALL
        self._auto_scroll = True
        self._max_lines = 1000  # Limit log lines to prevent memory issues

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle(tr("diag_window_title", self.lang))
        self.setMinimumSize(450, 400)
        self.resize(500, 500)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Control group
        grp_control = QGroupBox(tr("diag_controls", self.lang))
        self.grp_control = grp_control
        ctrl_layout = QHBoxLayout(grp_control)

        # Filter mode
        self.lbl_filter = QLabel(tr("diag_filter", self.lang))
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItem(tr("diag_filter_all", self.lang), FilterMode.ALL)
        self.cmb_filter.addItem(tr("diag_filter_non_f", self.lang), FilterMode.NON_F_KEYS)
        self.cmb_filter.addItem(tr("diag_filter_non_fn", self.lang), FilterMode.NON_FUNCTION)

        ctrl_layout.addWidget(self.lbl_filter)
        ctrl_layout.addWidget(self.cmb_filter)
        ctrl_layout.addStretch()

        # Auto-scroll checkbox
        self.chk_auto_scroll = QCheckBox(tr("diag_auto_scroll", self.lang))
        self.chk_auto_scroll.setChecked(True)
        ctrl_layout.addWidget(self.chk_auto_scroll)

        layout.addWidget(grp_control)

        # Log display
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 9))
        self.txt_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.txt_log, 1)

        # Button row
        btn_layout = QHBoxLayout()

        self.btn_clear = QPushButton(tr("diag_clear", self.lang))
        self.btn_copy = QPushButton(tr("diag_copy", self.lang))
        self.chk_clear_on_stop = QCheckBox(tr("diag_clear_on_stop", self.lang))
        self.chk_clear_on_stop.setChecked(False)

        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addStretch()
        btn_layout.addWidget(self.chk_clear_on_stop)

        layout.addLayout(btn_layout)

        # Status bar
        self.lbl_status = QLabel(tr("diag_status_ready", self.lang))
        layout.addWidget(self.lbl_status)

    def _connect_signals(self):
        """Connect signals to slots."""
        self.cmb_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.chk_auto_scroll.stateChanged.connect(self._on_auto_scroll_changed)
        self.btn_clear.clicked.connect(self.clear_log)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        self.sig_log_key.connect(self._on_log_key)

    def _on_filter_changed(self, index: int):
        """Handle filter mode change."""
        self._filter_mode = self.cmb_filter.itemData(index)

    def _on_auto_scroll_changed(self, state: int):
        """Handle auto-scroll checkbox change."""
        self._auto_scroll = state == Qt.CheckState.Checked.value

    def _on_log_key(self, key_name: str, action: str, source: str):
        """Handle key log signal."""
        try:
            key_source = KeySource(source) if source else KeySource.UNKNOWN
        except ValueError:
            key_source = KeySource.UNKNOWN
        self.log_key(key_name, action, key_source)

    def log_key(self, key_name: str, action: str, source: KeySource = KeySource.UNKNOWN):
        """
        Log a key event.

        Args:
            key_name: Name of the key (e.g., "A", "F5", "Space")
            action: Action type ("down", "up", "press")
            source: Source of the event
        """
        # Apply filter
        if not self._should_log(key_name):
            return

        # Format log entry
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        source_tag = self._format_source(source)
        action_tag = action.upper()

        entry = f"[{timestamp}] [{source_tag}] {key_name:12} {action_tag}"
        self._append_log(entry)

    def log_playback_key(self, key_name: str, action: str):
        """Log a key event from playback (SendInput)."""
        self.log_key(key_name, action, KeySource.PLAYBACK)

    def log_hotkey(self, key_name: str):
        """Log a global hotkey event."""
        self.log_key(key_name, "press", KeySource.HOTKEY)

    def log_manual_key(self, key_name: str, action: str):
        """Log a manual user key event."""
        self.log_key(key_name, action, KeySource.MANUAL)

    def _should_log(self, key_name: str) -> bool:
        """Check if key should be logged based on filter mode."""
        if self._filter_mode == FilterMode.ALL:
            return True
        elif self._filter_mode == FilterMode.NON_F_KEYS:
            return key_name.upper() not in F_KEYS
        elif self._filter_mode == FilterMode.NON_FUNCTION:
            return key_name.upper() not in FUNCTION_KEYS and key_name not in FUNCTION_KEYS
        return True

    def _format_source(self, source: KeySource) -> str:
        """Format source tag for display."""
        source_map = {
            KeySource.HOTKEY: "HOTKEY  ",
            KeySource.PLAYBACK: "PLAYBACK",
            KeySource.MANUAL: "MANUAL  ",
            KeySource.UNKNOWN: "UNKNOWN ",
        }
        return source_map.get(source, "UNKNOWN ")

    def _append_log(self, text: str):
        """Append text to log with line limit."""
        self.txt_log.append(text)

        # Limit lines
        doc = self.txt_log.document()
        if doc.blockCount() > self._max_lines:
            cursor = self.txt_log.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 100)
            cursor.removeSelectedText()
            cursor.deleteChar()  # Remove extra newline

        # Auto-scroll
        if self._auto_scroll:
            scrollbar = self.txt_log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        # Update status
        self._update_status()

    def _update_status(self):
        """Update status bar."""
        count = self.txt_log.document().blockCount()
        self.lbl_status.setText(tr("diag_status_count", self.lang).format(count=count))

    def clear_log(self):
        """Clear the log."""
        self.txt_log.clear()
        self._update_status()

    def on_playback_stopped(self):
        """Called when playback stops. Clears log if checkbox is checked."""
        if self.chk_clear_on_stop.isChecked():
            self.clear_log()

    def _copy_to_clipboard(self):
        """Copy log content to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.txt_log.toPlainText())
        self.lbl_status.setText(tr("diag_copied", self.lang))

    def apply_language(self, lang: str):
        """Apply language translations."""
        self.lang = lang
        self.setWindowTitle(tr("diag_window_title", lang))
        self.grp_control.setTitle(tr("diag_controls", lang))
        self.lbl_filter.setText(tr("diag_filter", lang))
        self.chk_auto_scroll.setText(tr("diag_auto_scroll", lang))
        self.btn_clear.setText(tr("diag_clear", lang))
        self.btn_copy.setText(tr("diag_copy", lang))
        self.chk_clear_on_stop.setText(tr("diag_clear_on_stop", lang))

        # Update filter combo items
        current_filter = self._filter_mode
        self.cmb_filter.clear()
        self.cmb_filter.addItem(tr("diag_filter_all", lang), FilterMode.ALL)
        self.cmb_filter.addItem(tr("diag_filter_non_f", lang), FilterMode.NON_F_KEYS)
        self.cmb_filter.addItem(tr("diag_filter_non_fn", lang), FilterMode.NON_FUNCTION)
        # Restore selection
        for i in range(self.cmb_filter.count()):
            if self.cmb_filter.itemData(i) == current_filter:
                self.cmb_filter.setCurrentIndex(i)
                break

        self._update_status()
