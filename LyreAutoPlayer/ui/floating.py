# -*- coding: utf-8 -*-
"""
Floating Controller - Always-on-top control panel for playback.

A frameless, draggable floating window that provides quick access to
playback controls, speed/octave adjustment, and style settings.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QSpinBox
)

from i18n import tr, LANG_ZH
from style_manager import INPUT_STYLES


class FloatingController(QWidget):
    """Always-on-top floating control panel for playback control."""

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
        self.setFixedSize(260, 320)  # Extra height for error + 8-bar + range controls
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
            QComboBox {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 3px;
            }
        """)

        self.init_ui()

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

        # Control buttons row
        btn_row = QHBoxLayout()
        self.btn_play_pause = QPushButton("▶")
        self.btn_stop = QPushButton("⏹")
        self.btn_open = QPushButton("📂")
        self._is_playing = False  # Track playback state for toggle
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

        # Octave control
        oct_row = QHBoxLayout()
        lbl_oct = QLabel(tr("octave_shift", self.lang) + ":")
        self.btn_oct_down = QPushButton("▼")
        self.lbl_oct_val = QLabel("0")
        self.lbl_oct_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_oct_val.setFixedWidth(30)
        self.btn_oct_up = QPushButton("▲")
        self.btn_oct_down.setFixedWidth(30)
        self.btn_oct_up.setFixedWidth(30)
        self.btn_oct_down.clicked.connect(self._on_oct_down)
        self.btn_oct_up.clicked.connect(self._on_oct_up)
        oct_row.addWidget(lbl_oct)
        oct_row.addStretch()
        oct_row.addWidget(self.btn_oct_down)
        oct_row.addWidget(self.lbl_oct_val)
        oct_row.addWidget(self.btn_oct_up)
        layout.addLayout(oct_row)

        # Speed control
        spd_row = QHBoxLayout()
        lbl_spd = QLabel(tr("speed", self.lang) + ":")
        self.btn_spd_down = QPushButton("▼")
        self.lbl_spd_val = QLabel("1.0x")
        self.lbl_spd_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_spd_val.setFixedWidth(50)
        self.btn_spd_up = QPushButton("▲")
        self.btn_spd_down.setFixedWidth(30)
        self.btn_spd_up.setFixedWidth(30)
        self.btn_spd_down.clicked.connect(self._on_spd_down)
        self.btn_spd_up.clicked.connect(self._on_spd_up)
        spd_row.addWidget(lbl_spd)
        spd_row.addStretch()
        spd_row.addWidget(self.btn_spd_down)
        spd_row.addWidget(self.lbl_spd_val)
        spd_row.addWidget(self.btn_spd_up)
        layout.addLayout(spd_row)

        # Octave range mode (auto/manual)
        range_mode_row = QHBoxLayout()
        self.lbl_range_mode = QLabel(tr("octave_range_mode", self.lang) + ":")
        self.chk_range_auto = QCheckBox(tr("octave_range_auto", self.lang))
        self.chk_range_auto.stateChanged.connect(self._on_octave_range_mode_changed)
        range_mode_row.addWidget(self.lbl_range_mode)
        range_mode_row.addStretch()
        range_mode_row.addWidget(self.chk_range_auto)
        layout.addLayout(range_mode_row)

        # Octave range
        range_row = QHBoxLayout()
        self.lbl_range = QLabel(tr("octave_range", self.lang) + ":")
        self.sp_range_min = QSpinBox()
        self.sp_range_min.setRange(0, 127)
        self.sp_range_max = QSpinBox()
        self.sp_range_max.setRange(0, 127)
        self.lbl_range_to = QLabel(tr("range_to", self.lang))
        self.sp_range_min.valueChanged.connect(self._on_octave_range_min_changed)
        self.sp_range_max.valueChanged.connect(self._on_octave_range_max_changed)
        range_row.addWidget(self.lbl_range)
        range_row.addWidget(self.sp_range_min)
        range_row.addWidget(self.lbl_range_to)
        range_row.addWidget(self.sp_range_max)
        layout.addLayout(range_row)

        # Input style selector
        style_row = QHBoxLayout()
        lbl_style = QLabel(tr("input_style", self.lang) + ":")
        self.cmb_style = QComboBox()
        for style_name, style in INPUT_STYLES.items():
            desc = style.description_zh if self.lang == LANG_ZH else style.description_en
            self.cmb_style.addItem(f"{tr('style_' + style_name, self.lang)} - {desc}", style_name)
        self.cmb_style.currentIndexChanged.connect(self._on_style_changed)
        style_row.addWidget(lbl_style)
        style_row.addWidget(self.cmb_style, 1)
        layout.addLayout(style_row)

        # Error simulation toggle row
        err_row = QHBoxLayout()
        lbl_err = QLabel(tr("errors", self.lang) + ":")
        self.chk_error = QCheckBox()
        self.chk_error.setStyleSheet("QCheckBox { background: transparent; }")
        self.cmb_error_freq = QComboBox()
        for i in range(1, 6):
            self.cmb_error_freq.addItem(f"{i}/8bars", i)
        self.cmb_error_freq.setFixedWidth(80)
        self.chk_error.stateChanged.connect(self._on_error_toggled)
        self.cmb_error_freq.currentIndexChanged.connect(self._on_error_freq_changed)
        err_row.addWidget(lbl_err)
        err_row.addWidget(self.chk_error)
        err_row.addStretch()
        err_row.addWidget(self.cmb_error_freq)
        layout.addLayout(err_row)

        # 8-Bar Style toggle row
        eight_bar_row = QHBoxLayout()
        lbl_8bar = QLabel(tr("eight_bar_style", self.lang) + ":")
        self.chk_eight_bar = QCheckBox()
        self.chk_eight_bar.setStyleSheet("QCheckBox { background: transparent; }")
        self.chk_eight_bar.stateChanged.connect(self._on_eight_bar_toggled)
        eight_bar_row.addWidget(lbl_8bar)
        eight_bar_row.addWidget(self.chk_eight_bar)
        eight_bar_row.addStretch()
        layout.addLayout(eight_bar_row)

        # Sync with main window values
        self._sync_from_main()

    def _sync_from_main(self):
        """Sync floating controller values from main window."""
        # Octave
        oct_val = self.main.cmb_octave.currentData() or 0
        self.lbl_oct_val.setText(f"{oct_val:+d}" if oct_val != 0 else "0")
        # Speed
        spd_val = self.main.sp_speed.value()
        self.lbl_spd_val.setText(f"{spd_val:.2f}x")
        # Style - find current style in combo
        current_style = getattr(self.main, '_current_input_style', 'mechanical')
        for i in range(self.cmb_style.count()):
            if self.cmb_style.itemData(i) == current_style:
                self.cmb_style.blockSignals(True)
                self.cmb_style.setCurrentIndex(i)
                self.cmb_style.blockSignals(False)
                break
        # Error settings
        err_enabled = getattr(self.main, '_error_enabled', False)
        err_freq = getattr(self.main, '_error_freq', 1)
        self.sync_error_settings(err_enabled, err_freq)
        # 8-bar style enabled
        if hasattr(self.main, 'chk_eight_bar_enabled'):
            self.sync_eight_bar_enabled(self.main.chk_eight_bar_enabled.isChecked())
        # Octave range
        if hasattr(self.main, 'sp_octave_min') and hasattr(self.main, 'sp_octave_max'):
            self.sync_octave_range(self.main.sp_octave_min.value(), self.main.sp_octave_max.value())
        if hasattr(self.main, 'chk_octave_range_auto'):
            self.sync_octave_range_mode(self.main.chk_octave_range_auto.isChecked())

    def sync_speed(self, value: float):
        """Sync floating speed display to the given value."""
        self.lbl_spd_val.setText(f"{value:.2f}x")

    def sync_octave_range(self, min_note: int, max_note: int):
        """Sync octave range values from main window."""
        self.sp_range_min.blockSignals(True)
        self.sp_range_max.blockSignals(True)
        self.sp_range_min.setValue(min_note)
        self.sp_range_max.setValue(max_note)
        self.sp_range_min.blockSignals(False)
        self.sp_range_max.blockSignals(False)

    def sync_octave_range_mode(self, auto_enabled: bool):
        """Sync octave range mode from main window."""
        self.chk_range_auto.blockSignals(True)
        self.chk_range_auto.setChecked(auto_enabled)
        self.chk_range_auto.blockSignals(False)
        self.sp_range_min.setEnabled(not auto_enabled)
        self.sp_range_max.setEnabled(not auto_enabled)

    def _on_octave_range_mode_changed(self, state: int):
        auto_enabled = state == Qt.CheckState.Checked.value
        if hasattr(self.main, 'chk_octave_range_auto'):
            self.main.chk_octave_range_auto.blockSignals(True)
            self.main.chk_octave_range_auto.setChecked(auto_enabled)
            self.main.chk_octave_range_auto.blockSignals(False)
            self.main._on_octave_range_mode_changed(state)

    def _on_octave_range_min_changed(self, val: int):
        if hasattr(self.main, 'sp_octave_min'):
            self.main.sp_octave_min.blockSignals(True)
            self.main.sp_octave_min.setValue(val)
            self.main.sp_octave_min.blockSignals(False)
            self.main._on_octave_range_changed()

    def _on_octave_range_max_changed(self, val: int):
        if hasattr(self.main, 'sp_octave_max'):
            self.main.sp_octave_max.blockSignals(True)
            self.main.sp_octave_max.setValue(val)
            self.main.sp_octave_max.blockSignals(False)
            self.main._on_octave_range_changed()

    def _on_oct_down(self):
        self.main.on_octave_down()
        oct_val = self.main.cmb_octave.currentData() or 0
        self.lbl_oct_val.setText(f"{oct_val:+d}" if oct_val != 0 else "0")

    def _on_oct_up(self):
        self.main.on_octave_up()
        oct_val = self.main.cmb_octave.currentData() or 0
        self.lbl_oct_val.setText(f"{oct_val:+d}" if oct_val != 0 else "0")

    def _on_spd_down(self):
        self.main.on_speed_down()
        self.lbl_spd_val.setText(f"{self.main.sp_speed.value():.2f}x")

    def _on_spd_up(self):
        self.main.on_speed_up()
        self.lbl_spd_val.setText(f"{self.main.sp_speed.value():.2f}x")

    def _on_play_pause_toggle(self):
        """Toggle between play/pause states."""
        if not self._is_playing:
            # Not playing -> start playback
            self.main.on_start()
            # Check if actually started (has events)
            if self.main.thread and self.main.thread.isRunning():
                self._is_playing = True
                self._update_play_pause_button()
        else:
            # Playing -> check current state and toggle
            if self.main.thread:
                if self.main.thread.is_paused():
                    # Currently paused -> resume
                    self.main.on_pause()
                    self._update_play_pause_button(is_paused=False, is_pending=False)
                elif self.main.thread.is_pause_pending():
                    # Pause pending -> cancel (resume call will cancel)
                    self.main.on_pause()
                    self._update_play_pause_button(is_paused=False, is_pending=False)
                else:
                    # Playing -> request pause (will happen at bar end)
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
            # Not playing: show play icon (green/normal)
            self.btn_play_pause.setText("▶")
            self.btn_play_pause.setToolTip(tr("start", self.lang))
            self.btn_play_pause.setStyleSheet("")  # Reset to default
        elif is_paused:
            # Paused: show play icon to resume
            self.btn_play_pause.setText("▶")
            self.btn_play_pause.setToolTip(tr("resume", self.lang))
            self.btn_play_pause.setStyleSheet("")  # Reset to default
        elif is_pending:
            # Pause pending (waiting for bar end): show orange/yellow pause icon
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
            # Playing: show red pause icon
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

    def _on_style_changed(self, index: int):
        style_name = self.cmb_style.itemData(index)
        self.main._current_input_style = style_name

        # Sync main window combos
        self.main._select_style_in_combo(self.main.cmb_input_style, style_name)
        self.main._select_style_in_combo(self.main.cmb_style_tab, style_name)
        self.main._update_style_params_display(style_name)

        style = INPUT_STYLES.get(style_name)
        if style:
            desc = style.description_zh if self.lang == LANG_ZH else style.description_en
            self.main.append_log(f"Input style: {style_name} ({desc})")

    def sync_style(self, style_name: str):
        """Sync floating controller style combo to the given style (called from main window)."""
        self.cmb_style.blockSignals(True)
        for i in range(self.cmb_style.count()):
            if self.cmb_style.itemData(i) == style_name:
                self.cmb_style.setCurrentIndex(i)
                break
        self.cmb_style.blockSignals(False)

    def rebuild_style_combo(self, current_style: str = None):
        """Rebuild style combo with current INPUT_STYLES."""
        if current_style is None:
            current_style = self.cmb_style.currentData() or 'mechanical'
        self.cmb_style.blockSignals(True)
        self.cmb_style.clear()
        for style_name, style in INPUT_STYLES.items():
            desc = style.description_zh if self.lang == LANG_ZH else style.description_en
            self.cmb_style.addItem(f"{tr('style_' + style_name, self.lang)} - {desc}", style_name)
        # Restore selection
        for i in range(self.cmb_style.count()):
            if self.cmb_style.itemData(i) == current_style:
                self.cmb_style.setCurrentIndex(i)
                break
        self.cmb_style.blockSignals(False)

    def update_language(self, lang: str):
        """Update floating controller language."""
        self.lang = lang
        self.lbl_title.setText(f"🎹 {tr('floating_title', lang)}")
        self.lbl_range_mode.setText(tr("octave_range_mode", self.lang) + ":")
        self.chk_range_auto.setText(tr("octave_range_auto", self.lang))
        self.lbl_range.setText(tr("octave_range", self.lang) + ":")
        self.lbl_range_to.setText(tr("range_to", self.lang))
        # Rebuild style combo using the shared method
        self.rebuild_style_combo()

    def _on_error_toggled(self, state: int):
        """Toggle error simulation on/off."""
        enabled = state == Qt.CheckState.Checked.value
        self.main._error_enabled = enabled
        if hasattr(self.main, 'chk_error_enabled'):
            self.main.chk_error_enabled.blockSignals(True)
            self.main.chk_error_enabled.setChecked(enabled)
            self.main.chk_error_enabled.blockSignals(False)
        self.main.append_log(f"Error simulation: {'ON' if enabled else 'OFF'}")

    def _on_error_freq_changed(self, index: int):
        """Change error frequency (per 8 bars)."""
        freq = self.cmb_error_freq.itemData(index)
        self.main._error_freq = freq
        if hasattr(self.main, 'sp_error_freq'):
            self.main.sp_error_freq.blockSignals(True)
            self.main.sp_error_freq.setValue(freq)
            self.main.sp_error_freq.blockSignals(False)

    def sync_error_settings(self, enabled: bool, freq: int):
        """Sync error settings from main window."""
        self.chk_error.blockSignals(True)
        self.chk_error.setChecked(enabled)
        self.chk_error.blockSignals(False)
        self.cmb_error_freq.blockSignals(True)
        for i in range(self.cmb_error_freq.count()):
            if self.cmb_error_freq.itemData(i) == freq:
                self.cmb_error_freq.setCurrentIndex(i)
                break
        self.cmb_error_freq.blockSignals(False)

    def _on_eight_bar_toggled(self, state: int):
        """Toggle 8-bar style variation on/off from floating controller."""
        enabled = state == Qt.CheckState.Checked.value
        # Sync to main window checkboxes
        if hasattr(self.main, 'chk_eight_bar_enabled'):
            self.main.chk_eight_bar_enabled.blockSignals(True)
            self.main.chk_eight_bar_enabled.setChecked(enabled)
            self.main.chk_eight_bar_enabled.blockSignals(False)
        if hasattr(self.main, 'chk_quick_eight_bar'):
            self.main.chk_quick_eight_bar.blockSignals(True)
            self.main.chk_quick_eight_bar.setChecked(enabled)
            self.main.chk_quick_eight_bar.blockSignals(False)
        self.main.append_log(f"8-Bar variation: {'ON' if enabled else 'OFF'}")

    def sync_eight_bar_enabled(self, enabled: bool):
        """Sync 8-bar enabled state from main window."""
        self.chk_eight_bar.blockSignals(True)
        self.chk_eight_bar.setChecked(enabled)
        self.chk_eight_bar.blockSignals(False)

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
