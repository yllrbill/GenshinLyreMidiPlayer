# -*- coding: utf-8 -*-
"""
Floating Controller - Simplified always-on-top control panel.

A compact (260×150 px) frameless, draggable floating window that provides:
- Play/Pause/Stop/Open controls
- BPM display (read-only)
- Playback progress
- File name display

Note: This is the simplified version. Advanced controls (octave, speed, style)
have been removed and replaced with compatibility stubs.
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)

from i18n import tr, LANG_ZH


class FloatingController(QWidget):
    """Simplified always-on-top floating control panel for playback control."""

    def __init__(self, main_window, lang: str = LANG_ZH):
        super().__init__()
        self.main = main_window
        self.lang = lang
        self.drag_pos = None

        # Window flags: frameless + always on top + tool (no taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # Simplified size: 260w × 150h (was 260×320 before simplification)
        self.setFixedSize(260, 150)
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QLabel {
                background: transparent;
            }
        """)

        self.init_ui()

        # Timer for progress update
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(100)  # 10 FPS update
        self._progress_timer.timeout.connect(self._update_progress)
        self._progress_timer.start()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)

        # Title bar with close button
        title_bar = QHBoxLayout()
        self.lbl_title = QLabel(f"🎹 {tr('floating_title', self.lang)}")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        btn_close = QPushButton("×")
        btn_close.setFixedSize(20, 20)
        btn_close.setStyleSheet("min-width: 20px; padding: 0;")
        btn_close.clicked.connect(self.hide)
        title_bar.addWidget(self.lbl_title)
        title_bar.addStretch()
        title_bar.addWidget(btn_close)
        layout.addLayout(title_bar)

        # File name display
        file_row = QHBoxLayout()
        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        file_row.addWidget(self.lbl_file)
        layout.addLayout(file_row)

        # Control buttons row
        btn_row = QHBoxLayout()
        self.btn_play_pause = QPushButton("▶")
        self.btn_stop = QPushButton("⏹")
        self.btn_open = QPushButton("📂")
        self._is_playing = False
        self.btn_play_pause.setToolTip(tr("start", self.lang))
        self.btn_stop.setToolTip(tr("stop", self.lang))
        self.btn_open.setToolTip(tr("load_midi", self.lang))
        self.btn_play_pause.clicked.connect(self._on_play_pause_toggle)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_open.clicked.connect(self.main.on_load)
        btn_row.addWidget(self.btn_play_pause)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_open)
        layout.addLayout(btn_row)

        # Progress and BPM row
        info_row = QHBoxLayout()
        self.lbl_progress = QLabel("0:00 / 0:00")
        self.lbl_progress.setStyleSheet("font-size: 11px;")
        self.lbl_bpm = QLabel("120 BPM")
        self.lbl_bpm.setStyleSheet("font-size: 11px; color: #88ccff;")
        info_row.addWidget(self.lbl_progress)
        info_row.addStretch()
        info_row.addWidget(self.lbl_bpm)
        layout.addLayout(info_row)

        layout.addStretch()

    def _update_progress(self):
        """Update progress display from main window."""
        try:
            # Get playback info from main window
            current = getattr(self.main, 'current_time', 0.0)
            total = getattr(self.main, 'total_duration', 0.0)

            def fmt_time(t):
                m = int(t // 60)
                s = int(t % 60)
                return f"{m}:{s:02d}"

            self.lbl_progress.setText(f"{fmt_time(current)} / {fmt_time(total)}")
        except Exception:
            pass  # Ignore errors during update

    def set_file_name(self, name: str):
        """Set the displayed file name."""
        if name:
            # Truncate if too long
            if len(name) > 30:
                name = name[:27] + "..."
            self.lbl_file.setText(name)
        else:
            self.lbl_file.setText("No file loaded")

    def set_bpm(self, bpm: int):
        """Set the displayed BPM."""
        self.lbl_bpm.setText(f"{bpm} BPM")

    def _on_play_pause_toggle(self):
        """Toggle between play/pause states."""
        if not self._is_playing:
            self.main.on_start()
            if self.main.thread and self.main.thread.isRunning():
                self._is_playing = True
                self._update_play_pause_button()
        else:
            if self.main.thread:
                if self.main.thread.is_paused():
                    self.main.on_pause()
                    self._update_play_pause_button(is_paused=False, is_pending=False)
                elif self.main.thread.is_pause_pending():
                    self.main.on_pause()
                    self._update_play_pause_button(is_paused=False, is_pending=False)
                else:
                    self.main.on_pause()
                    self._update_play_pause_button(is_paused=False, is_pending=True)

    def _on_stop(self):
        """Stop playback and reset button state."""
        self.main.on_stop()
        self._is_playing = False
        self._update_play_pause_button()

    def _update_play_pause_button(self, is_paused: bool = False, is_pending: bool = False):
        """Update play/pause button appearance based on state."""
        if not self._is_playing:
            self.btn_play_pause.setText("▶")
            self.btn_play_pause.setToolTip(tr("start", self.lang))
            self.btn_play_pause.setStyleSheet("")
        elif is_paused:
            self.btn_play_pause.setText("▶")
            self.btn_play_pause.setToolTip(tr("resume", self.lang))
            self.btn_play_pause.setStyleSheet("")
        elif is_pending:
            self.btn_play_pause.setText("⏸")
            self.btn_play_pause.setToolTip(tr("pause", self.lang) + " (waiting...)")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background-color: #e67e22;
                    border: 1px solid #f39c12;
                }
                QPushButton:hover {
                    background-color: #f39c12;
                }
            """)
        else:
            self.btn_play_pause.setText("⏸")
            self.btn_play_pause.setToolTip(tr("pause", self.lang))
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background-color: #c0392b;
                    border: 1px solid #e74c3c;
                }
                QPushButton:hover {
                    background-color: #e74c3c;
                }
            """)

    def update_playback_state(self, is_playing: bool, is_paused: bool = False, is_pending: bool = False):
        """Called by main window to sync playback state."""
        self._is_playing = is_playing
        self._update_play_pause_button(is_paused, is_pending)

    def update_language(self, lang: str):
        """Update floating controller language."""
        self.lang = lang
        self.lbl_title.setText(f"🎹 {tr('floating_title', lang)}")
        self.btn_play_pause.setToolTip(tr("start", lang))
        self.btn_stop.setToolTip(tr("stop", lang))
        self.btn_open.setToolTip(tr("load_midi", lang))

    def _sync_from_main(self):
        """Sync state from main window (called when showing floating controller)."""
        try:
            # Sync file name
            mid_path = getattr(self.main, 'mid_path', None)
            if mid_path:
                import os
                self.set_file_name(os.path.basename(mid_path))
            else:
                self.set_file_name(None)

            # Sync BPM from main window (with fallback)
            bpm = getattr(self.main, 'current_bpm', 120)
            self.set_bpm(bpm)

            # Sync playback state
            is_playing = False
            is_paused = False
            is_pending = False
            thread = getattr(self.main, 'thread', None)
            if thread and thread.isRunning():
                is_playing = True
                if hasattr(thread, 'is_paused') and thread.is_paused():
                    is_paused = True
                elif hasattr(thread, 'is_pause_pending') and thread.is_pause_pending():
                    is_pending = True
            self.update_playback_state(is_playing, is_paused, is_pending)

        except Exception as e:
            # Fail silently - floating controller should not crash main app
            print(f"[FloatingController] _sync_from_main error: {e}")

    # Compatibility stubs for methods that may be called by main window
    def sync_speed(self, value: float):
        """Compatibility stub - speed control removed."""
        pass

    def sync_octave_range(self, min_note: int, max_note: int):
        """Compatibility stub - octave range removed."""
        pass

    def sync_octave_range_mode(self, auto_enabled: bool):
        """Compatibility stub - octave range mode removed."""
        pass

    def sync_error_settings(self, enabled: bool, freq: int):
        """Compatibility stub - error settings removed."""
        pass

    def sync_eight_bar_enabled(self, enabled: bool):
        """Compatibility stub - 8-bar toggle removed."""
        pass

    def sync_style(self, style_name: str):
        """Compatibility stub - style selector removed."""
        pass

    def rebuild_style_combo(self, current_style: str = None):
        """Compatibility stub - style combo removed."""
        pass

    def mousePressEvent(self, event):
        """Enable window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Handle window dragging."""
        if self.drag_pos:
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
