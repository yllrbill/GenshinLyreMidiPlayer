"""
EditorWindow - MIDI 编辑器主窗口

Features:
- MIDI 可视化 (钢琴卷帘)
- 播放预览 (FluidSynth)
- 保存/版本管理
"""
import os
import sys
import json
import random
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QSlider, QLabel, QFileDialog, QMessageBox,
    QSplitter, QScrollBar, QComboBox, QSpinBox, QCheckBox,
    QPushButton
)
from PyQt6.QtGui import QAction, QIcon, QShortcut, QKeySequence
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import mido

# FluidSynth (optional)
try:
    import fluidsynth
    HAS_FLUIDSYNTH = True
except ImportError:
    HAS_FLUIDSYNTH = False

from .piano_roll import PianoRollWidget
from .timeline import TimelineWidget
from .keyboard import KeyboardWidget
from .countdown_overlay import CountdownOverlay
from .key_list_widget import KeyListWidget
from .undo_commands import ApplyJitterCommand
from i18n import tr, LANG_ZH
from style_manager import get_style_names, INPUT_STYLES


class EditorWindow(QMainWindow):
    """MIDI 编辑器主窗口"""

    # Signal: emitted when MIDI is loaded (path, events_list)
    # events_list is a list of dicts: [{"time": float, "note": int, "duration": float}, ...]
    midi_loaded = pyqtSignal(str, list)

    # Signal: emitted when BPM changes (for main window sync)
    bpm_changed = pyqtSignal(int)

    # Signal: emitted when audio checkbox changes (for main window sync)
    audio_changed = pyqtSignal(bool)

    # 编辑风格选项
    EDIT_STYLES = ["custom", "simplified", "transposed", "extended", "practice"]

    def __init__(self, midi_path: Optional[str] = None, parent=None):
        super().__init__(parent)

        # 计算 EDITS_DIR：基于此文件所在的 LyreAutoPlayer 根目录
        self._app_root = Path(__file__).parent.parent.parent  # ui/editor -> ui -> LyreAutoPlayer
        self._edits_dir = self._app_root / "midi-change"

        self.midi_path = midi_path
        self._source_path: Optional[str] = None  # 原始文件路径 (用于索引)
        self.midi_file: Optional[mido.MidiFile] = None
        self.is_playing = False
        self.playback_time = 0.0
        self._base_bpm = 120  # Base BPM for preview speed scaling
        self.edit_style = "custom"  # 编辑风格标签

        # FluidSynth 相关
        self._fs = None  # fluidsynth.Synth instance
        self._sfid = -1  # SoundFont ID
        self._chan = 0   # MIDI channel
        self._active_notes: Dict[int, int] = {}  # 音符 -> 发声计数

        # Unified playback: follow mode state
        self._follow_mode = False  # Following PlayerThread (not local timer)
        self._main_window = None   # Reference to main window
        self._audio_was_enabled = True  # Remember audio state before follow mode

        # Octave shift: track previous value for delta calculation
        self._prev_octave_shift = 0

        self._setup_ui()
        self._setup_toolbar()
        self._setup_menus()
        self._setup_connections()

        if midi_path:
            self.load_midi(midi_path)

    def _setup_ui(self):
        """设置 UI 布局"""
        self.setWindowTitle("MIDI Editor")
        self.setMinimumSize(800, 600)

        # 中央 widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 时间轴 (顶部)
        timeline_row = QHBoxLayout()
        timeline_row.setSpacing(0)

        # 左上角占位 (与 keyboard 宽度匹配: OCTAVE_LABEL_WIDTH + KEYBOARD_WIDTH = 80)
        # 高度与 TimelineWidget.HEIGHT 同步
        self._corner = QWidget()
        self._corner.setFixedSize(80, TimelineWidget.HEIGHT)
        self._corner.setStyleSheet("background-color: #282828;")
        timeline_row.addWidget(self._corner)

        self.timeline = TimelineWidget()
        timeline_row.addWidget(self.timeline)

        main_layout.addLayout(timeline_row)

        # 纵向 Splitter: 上=键盘+卷帘，下=按键进度窗
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setStyleSheet("QSplitter::handle { background-color: #444; height: 4px; }")

        # 上部: 键盘 + 卷帘
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.keyboard = KeyboardWidget()
        top_layout.addWidget(self.keyboard)

        self.piano_roll = PianoRollWidget()
        top_layout.addWidget(self.piano_roll)

        self.main_splitter.addWidget(top_widget)

        # 下部: 按键进度窗
        self.key_list = KeyListWidget()
        self.main_splitter.addWidget(self.key_list)

        # 设置 splitter 比例 (默认按键进度窗隐藏)
        self.main_splitter.setSizes([500, 0])
        self.main_splitter.setCollapsible(0, False)  # 上部不可折叠
        self.main_splitter.setCollapsible(1, True)   # 下部可折叠

        main_layout.addWidget(self.main_splitter)

        # Countdown overlay (displayed during auto-pause countdown)
        self._countdown_overlay = CountdownOverlay(self.piano_roll)
        self._countdown_overlay.setGeometry(self.piano_roll.rect())

        # 播放计时器
        self.playback_timer = QTimer()
        self.playback_timer.setInterval(16)  # ~60 FPS

    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 打开
        self.act_open = QAction("Open", self)
        self.act_open.setShortcut("Ctrl+O")
        toolbar.addAction(self.act_open)

        # 保存
        self.act_save = QAction("Save", self)
        self.act_save.setShortcut("Ctrl+S")
        toolbar.addAction(self.act_save)

        # 另存为
        self.act_save_as = QAction("Save As...", self)
        self.act_save_as.setShortcut("Ctrl+Shift+S")
        toolbar.addAction(self.act_save_as)

        toolbar.addSeparator()

        # 播放/暂停
        self.act_play = QAction("Play", self)
        self.act_play.setShortcut("Space")
        toolbar.addAction(self.act_play)

        # 停止
        self.act_stop = QAction("Stop", self)
        toolbar.addAction(self.act_stop)

        # 音频开关
        self.chk_enable_audio = QCheckBox("Audio")
        self.chk_enable_audio.setChecked(True)
        self.chk_enable_audio.setToolTip("Enable audio playback (F5 to toggle play)")
        self.chk_enable_audio.stateChanged.connect(
            lambda state: self.audio_changed.emit(state == Qt.CheckState.Checked.value)
        )
        toolbar.addWidget(self.chk_enable_audio)

        toolbar.addSeparator()

        # 水平缩放 (X)
        toolbar.addWidget(QLabel(" Zoom X: "))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(20, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(100)
        toolbar.addWidget(self.zoom_slider)

        # 垂直缩放 (Y) - 行高
        toolbar.addWidget(QLabel(" Zoom Y: "))
        self.zoom_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_y_slider.setRange(6, 30)
        self.zoom_y_slider.setValue(12)  # 默认 12px
        self.zoom_y_slider.setFixedWidth(80)
        toolbar.addWidget(self.zoom_y_slider)

        # 时间显示
        toolbar.addWidget(QLabel("  "))
        self.lbl_time = QLabel("0:00.0 / 0:00.0")
        toolbar.addWidget(self.lbl_time)

        toolbar.addSeparator()

        # 量化分辨率选择
        toolbar.addWidget(QLabel(" Quantize: "))
        self.cmb_quantize = QComboBox()
        self.cmb_quantize.addItems(["1/4", "1/8", "1/16", "1/32"])
        self.cmb_quantize.setCurrentText("1/8")  # 默认 1/8
        self.cmb_quantize.setFixedWidth(60)
        toolbar.addWidget(self.cmb_quantize)

        toolbar.addSeparator()

        # BPM 控制 (影响网格显示、导出与预览速度)
        toolbar.addWidget(QLabel(" BPM: "))
        self.sp_bpm = QSpinBox()
        self.sp_bpm.setRange(20, 300)
        self.sp_bpm.setValue(120)  # 默认 120 BPM
        self.sp_bpm.setFixedWidth(80)
        self.sp_bpm.setToolTip(
            "Global BPM (Tempo)\n"
            "• Scales all note times when changed\n"
            "• Affects timeline grid display\n"
            "• Affects exported MIDI tempo"
        )
        toolbar.addWidget(self.sp_bpm)

        # ─── 第二行工具栏 ───
        self.addToolBarBreak()
        toolbar2 = QToolBar("Secondary Toolbar")
        toolbar2.setMovable(False)
        self.addToolBar(toolbar2)

        # Auto-pause interval (每 N 小节暂停)
        toolbar2.addWidget(QLabel(" Pause: "))
        self.cmb_pause_bars = QComboBox()
        self.cmb_pause_bars.addItem("Off", 0)
        self.cmb_pause_bars.addItem("1 bar", 1)
        self.cmb_pause_bars.addItem("2 bars", 2)
        self.cmb_pause_bars.addItem("4 bars", 4)
        self.cmb_pause_bars.addItem("8 bars", 8)
        self.cmb_pause_bars.setCurrentIndex(0)
        self.cmb_pause_bars.setFixedWidth(70)
        self.cmb_pause_bars.setToolTip("Auto-pause every N bars for practice")
        toolbar2.addWidget(self.cmb_pause_bars)

        # Auto-resume countdown
        toolbar2.addWidget(QLabel(" Resume: "))
        self.sp_auto_resume = QSpinBox()
        self.sp_auto_resume.setRange(1, 10)
        self.sp_auto_resume.setValue(3)
        self.sp_auto_resume.setSuffix("s")
        self.sp_auto_resume.setFixedWidth(50)
        self.sp_auto_resume.setToolTip("Countdown seconds before auto-resume")
        toolbar2.addWidget(self.sp_auto_resume)

        toolbar2.addSeparator()

        # Overall octave shift (-2 to +2)
        toolbar2.addWidget(QLabel(" Octave: "))
        self.sp_octave_shift = QSpinBox()
        self.sp_octave_shift.setRange(-2, 2)
        self.sp_octave_shift.setValue(0)
        self.sp_octave_shift.setFixedWidth(50)
        self.sp_octave_shift.setToolTip("Transpose all notes by octaves (±12 semitones)")
        toolbar2.addWidget(self.sp_octave_shift)

        toolbar2.addSeparator()

        # Input style for playback (输入风格)
        toolbar2.addWidget(QLabel(" Input: "))
        self.cmb_input_style = QComboBox()
        self._populate_input_styles()
        self.cmb_input_style.setFixedWidth(100)
        self.cmb_input_style.setToolTip("Input style affects timing variations during playback")
        toolbar2.addWidget(self.cmb_input_style)

        toolbar2.addSeparator()

        # 时值调整控件
        toolbar2.addWidget(QLabel(tr("duration_label")))
        self.spin_duration_delta = QSpinBox()
        self.spin_duration_delta.setRange(-5000, 5000)
        self.spin_duration_delta.setSingleStep(50)
        self.spin_duration_delta.setValue(0)
        self.spin_duration_delta.setSuffix(" ms")
        self.spin_duration_delta.setFixedWidth(90)
        self.spin_duration_delta.setToolTip(tr("duration_tooltip"))
        toolbar2.addWidget(self.spin_duration_delta)

        self.btn_apply_duration = QPushButton(tr("apply_duration"))
        self.btn_apply_duration.setToolTip(tr("apply_duration_tooltip"))
        self.btn_apply_duration.clicked.connect(self._apply_duration_delta)
        toolbar2.addWidget(self.btn_apply_duration)

        toolbar2.addSeparator()

        # 小节时值调整 (Bar Duration Adjust)
        toolbar2.addWidget(QLabel(tr("bar_duration_label")))
        self.spin_bar_duration_delta = QSpinBox()
        self.spin_bar_duration_delta.setRange(-5000, 5000)
        self.spin_bar_duration_delta.setSingleStep(50)
        self.spin_bar_duration_delta.setValue(0)
        self.spin_bar_duration_delta.setSuffix(" ms")
        self.spin_bar_duration_delta.setFixedWidth(90)
        self.spin_bar_duration_delta.setToolTip(tr("bar_duration_tooltip"))
        toolbar2.addWidget(self.spin_bar_duration_delta)

        self.btn_apply_bar_duration = QPushButton(tr("apply_bar_duration"))
        self.btn_apply_bar_duration.setToolTip(tr("apply_bar_duration_tooltip"))
        self.btn_apply_bar_duration.clicked.connect(self._apply_bar_duration_delta)
        toolbar2.addWidget(self.btn_apply_bar_duration)

        toolbar2.addSeparator()

        # 编辑风格选择
        toolbar2.addWidget(QLabel(" Style: "))
        self.cmb_edit_style = QComboBox()
        self.cmb_edit_style.addItems(self.EDIT_STYLES)
        self.cmb_edit_style.setCurrentText(self.edit_style)
        self.cmb_edit_style.setFixedWidth(100)
        toolbar2.addWidget(self.cmb_edit_style)

        toolbar2.addSeparator()

        # 按键列表开关
        self.chk_key_list = QCheckBox("Key List")
        self.chk_key_list.setToolTip("Show/hide the key sequence list")
        self.chk_key_list.setChecked(False)
        toolbar2.addWidget(self.chk_key_list)

    def _setup_menus(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # Edit 菜单
        edit_menu = menubar.addMenu("Edit")

        # 音符操作
        act_transpose_lyre = edit_menu.addAction("Auto Transpose to Lyre Range (C3-C6)")
        act_transpose_lyre.setShortcut("T")
        act_transpose_lyre.setToolTip("Move selected notes to fit within Lyre range (C3-C6, 3 octaves)")
        act_transpose_lyre.triggered.connect(lambda: self._do_transpose(48, 84))

        act_transpose_ext = edit_menu.addAction("Auto Transpose to Extended Range (C4-C7)")
        act_transpose_ext.setShortcut("Shift+T")
        act_transpose_ext.setToolTip("Move selected notes to fit within extended range (C4-C7, 3 octaves)")
        act_transpose_ext.triggered.connect(lambda: self._do_transpose(60, 96))

        edit_menu.addSeparator()

        # Apply input style (humanization)
        act_apply_style = edit_menu.addAction(tr("apply_jitter"))
        act_apply_style.setShortcut("H")
        act_apply_style.setToolTip(tr("apply_jitter_tooltip"))
        act_apply_style.triggered.connect(self._apply_input_style_jitter)

        edit_menu.addSeparator()

        # 帮助提示
        act_create_hint = edit_menu.addAction("Note Creation: Alt+Click/Drag")
        act_create_hint.setEnabled(False)  # 仅作为提示，不可点击
        act_create_hint.setToolTip("Hold Alt and click/drag on empty area to create a note")

        act_select_hint = edit_menu.addAction("Selection: Click+Drag (RubberBand)")
        act_select_hint.setEnabled(False)
        act_select_hint.setToolTip("Click and drag to select multiple notes")

        # Help 菜单
        help_menu = menubar.addMenu("Help")
        act_shortcuts = help_menu.addAction("Keyboard Shortcuts...")
        act_shortcuts.triggered.connect(self._show_shortcuts_help)

    def _do_transpose(self, target_low: int, target_high: int):
        """执行自动移调"""
        selected = [item for item in self.piano_roll.notes if item.isSelected()]
        if not selected:
            QMessageBox.information(
                self, "Auto Transpose",
                "No notes selected.\nSelect notes first, then use Edit menu or press T."
            )
            return
        self.piano_roll.auto_transpose_octave(target_low, target_high)

    def _show_shortcuts_help(self):
        """显示快捷键帮助"""
        shortcuts = """
<h3>Keyboard Shortcuts</h3>

<b>File:</b>
<ul>
<li>Ctrl+O - Open MIDI file</li>
<li>Ctrl+S - Save</li>
<li>Ctrl+Shift+S - Save As</li>
</ul>

<b>Playback:</b>
<ul>
<li>Space / F5 - Play/Pause</li>
</ul>

<b>Selection:</b>
<ul>
<li>Ctrl+A - Select all notes</li>
<li>Escape - Deselect all</li>
<li>Delete / Backspace - Delete selected</li>
<li>Ctrl+C - Copy selected</li>
<li>Ctrl+V - Paste at playhead</li>
</ul>

<b>Edit (requires selection):</b>
<ul>
<li>Ctrl+Z - Undo</li>
<li>Ctrl+Y / Ctrl+Shift+Z - Redo</li>
<li>Q - Quantize to grid</li>
<li>H - Humanize (natural: 20ms)</li>
<li>Shift+H - Humanize (light: 10ms)</li>
<li>Ctrl+H - Humanize (strong: 40ms)</li>
</ul>

<b>Transpose (requires selection):</b>
<ul>
<li>Shift+↑ / Shift+↓ - Transpose ±1 semitone</li>
<li>Ctrl+Shift+↑ / Ctrl+Shift+↓ - Transpose ±1 octave</li>
<li>T - Auto transpose to Lyre range (C3-C6)</li>
<li>Shift+T - Auto transpose to extended range (C4-C7)</li>
</ul>

<b>View:</b>
<ul>
<li>Ctrl+Wheel - Zoom</li>
<li>Ctrl+↑ / Ctrl+↓ - Adjust row height</li>
<li>[ / ] - Adjust row height</li>
<li>Space (hold) - Pan mode (piano roll focus only)</li>
</ul>

<b>Mouse (in piano roll):</b>
<ul>
<li>Click+Drag - RubberBand selection</li>
<li>Alt+Click/Drag - Create note (drag to set duration)</li>
<li>Drag note edge - Resize note</li>
<li>Drag note body - Move note</li>
</ul>

<p><i>Note: Space for pan requires piano roll focus; otherwise Space triggers Play/Pause.</i></p>
"""
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts)

    def _setup_connections(self):
        """连接信号槽"""
        self.act_open.triggered.connect(self.on_open)
        self.act_save.triggered.connect(self.on_save)
        self.act_save_as.triggered.connect(self.on_save_as)
        self.act_play.triggered.connect(self.on_play_pause)
        self.act_stop.triggered.connect(self.on_stop)

        # F5 快捷键播放/暂停
        self.shortcut_f5 = QShortcut(QKeySequence(Qt.Key.Key_F5), self)
        self.shortcut_f5.activated.connect(self.on_play_pause)

        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.zoom_y_slider.valueChanged.connect(self._on_zoom_y_changed)
        self.playback_timer.timeout.connect(self._update_playback)
        self.timeline.sig_seek.connect(self.on_seek)
        self.cmb_edit_style.currentTextChanged.connect(self._on_edit_style_changed)
        self.cmb_input_style.currentTextChanged.connect(self._on_input_style_changed)
        self.cmb_quantize.currentTextChanged.connect(self._on_quantize_changed)
        self.sp_bpm.valueChanged.connect(self._on_bpm_changed)
        self.timeline.sig_bpm_changed.connect(self._on_timeline_bpm_changed)
        self.timeline.sig_select_range.connect(self._on_timeline_select_range)
        self.sp_octave_shift.valueChanged.connect(self._on_octave_shift_changed)

        # 同步滚动
        self.piano_roll.horizontalScrollBar().valueChanged.connect(
            lambda v: self.timeline.set_scroll_offset(v)
        )
        self.piano_roll.verticalScrollBar().valueChanged.connect(
            lambda v: self.keyboard.set_scroll_offset(v)
        )
        # 按键进度窗水平滚动同步（单向：piano_roll → key_list）
        self.piano_roll.horizontalScrollBar().valueChanged.connect(
            lambda v: self.key_list.set_scroll_offset(v)
        )

        # 同步缩放 (Ctrl+滚轮 → 时间轴 + 滑条 + 按键进度窗)
        self.piano_roll.sig_zoom_changed.connect(self._on_piano_roll_zoom)

        # 同步行高变化 (Ctrl+Up/Down / [ ] → 键盘)
        self.piano_roll.sig_row_height_changed.connect(self._on_row_height_changed)

        # 键盘拖拽选择音域 → 钢琴卷帘批量选择
        self.keyboard.sig_range_selected.connect(self.piano_roll.select_by_pitch_range)

        # Bar selection: timeline → piano_roll
        self.timeline.sig_bar_selection_changed.connect(self.piano_roll.set_selected_bars)
        self.timeline.sig_drag_range.connect(self.piano_roll.set_drag_boundary)

        # 可变小节时长同步: timeline ↔ piano_roll
        self.timeline.sig_bar_times_changed.connect(self.piano_roll.set_bar_times)
        self.piano_roll.sig_bar_duration_changed.connect(self.timeline.update_bar_duration)

        # Notes changed → refresh key_list and timeline
        self.piano_roll.sig_notes_changed.connect(self._on_notes_changed_refresh)

        # 按键列表开关
        self.chk_key_list.toggled.connect(self._on_key_list_toggled)

    def _on_key_list_toggled(self, checked: bool):
        """切换按键进度窗显示"""
        if checked:
            # 显示按键进度窗 (设置合适的高度)
            sizes = self.main_splitter.sizes()
            total = sum(sizes)
            # 底部按键窗占 30% 高度
            key_list_height = min(200, total // 3)
            self.main_splitter.setSizes([total - key_list_height, key_list_height])
            # 更新按键列表内容
            events = self.export_events()
            self.key_list.set_events(events)
            self.key_list.set_total_duration(self.piano_roll.total_duration)
            # 同步缩放
            self.key_list.set_scale(self.piano_roll.pixels_per_second)
        else:
            # 隐藏按键进度窗
            sizes = self.main_splitter.sizes()
            total = sum(sizes)
            self.main_splitter.setSizes([total, 0])

    def set_keyboard_config(self, root_note: int, layout_name: str):
        """设置键盘配置 (同步到 KeyListWidget)

        Args:
            root_note: 根音 MIDI 编号 (如 60 = C4)
            layout_name: 布局名称 (如 "21-key" 或 "36-key")
        """
        self.key_list.set_root_note(root_note)
        self.key_list.set_layout(layout_name)

    def load_midi(self, path: str, source_path: Optional[str] = None):
        """加载 MIDI 文件

        Args:
            path: 要加载的 MIDI 文件路径
            source_path: 原始文件路径 (用于索引)。若为 None，则尝试从 index.json 反查
        """
        try:
            self.midi_file = mido.MidiFile(path)
            self.midi_path = path

            # 确定原始文件路径
            if source_path:
                self._source_path = self._normalize_path(source_path)
            else:
                # 尝试从 index.json 反查
                self._source_path = self._lookup_source_path(path)
                if not self._source_path:
                    # 没有找到，说明这是原始文件
                    self._source_path = self._normalize_path(path)

            self.piano_roll.load_midi(self.midi_file)

            # 解析 tempo 和 time signature 传递给时间轴
            tempo_events, time_sig_events = self._extract_tempo_and_time_sig()
            self.timeline.set_tempo_info(
                self.midi_file.ticks_per_beat,
                tempo_events,
                time_sig_events
            )

            # 缓存 tempo 信息，供 BPM 变更时重建 timeline
            self._ticks_per_beat = self.midi_file.ticks_per_beat
            self._time_sig_events_tick = time_sig_events

            # 更新时间轴
            self.timeline.set_duration(self.piano_roll.total_duration)
            self.timeline.set_scale(self.piano_roll.pixels_per_second)

            # 更新窗口标题
            filename = os.path.basename(path)
            self.setWindowTitle(f"MIDI Editor - {filename}")

            # 更新键盘可用音域范围（基于 MIDI 文件中的实际音符）
            self._update_keyboard_range()

            # 更新 BPM spinbox（从 MIDI 文件读取）
            midi_bpm = int(self._get_current_bpm())
            self._base_bpm = max(1, midi_bpm)
            self.sp_bpm.blockSignals(True)
            self.sp_bpm.setValue(midi_bpm)
            self.sp_bpm.blockSignals(False)

            # 重置八度平移
            self._prev_octave_shift = 0
            self.sp_octave_shift.blockSignals(True)
            self.sp_octave_shift.setValue(0)
            self.sp_octave_shift.blockSignals(False)

            # 同步时间轴为单一 BPM，确保与钢琴卷帘小节线对齐
            self._sync_timeline_tempo(midi_bpm)

            # 更新量化网格（使用新 MIDI 的 BPM）
            self._on_quantize_changed(self.cmb_quantize.currentText())
            self._update_bar_lines()

            # 重置播放
            self.playback_time = 0.0
            self._update_time_label()

            # 设置焦点到钢琴卷帘，确保快捷键立即生效
            self.piano_roll.setFocus()

            # Emit signal for main window sync
            # Convert NoteItem list to event list format expected by PlayerThread
            events_list = []
            for item in self.piano_roll.notes:
                events_list.append({
                    "time": item.start_time,
                    "note": item.note,
                    "duration": item.duration
                })
            self.midi_loaded.emit(path, events_list)

            # 更新按键列表
            self.key_list.set_events(events_list)
            self.key_list.set_total_duration(self.piano_roll.total_duration)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load MIDI:\n{e}")

    @staticmethod
    def _normalize_path(path: str) -> str:
        """规范化路径 (统一大小写和斜杠)

        使用 Path.resolve() 解析符号链接和 .. 等，
        然后用 os.path.normcase() 在 Windows 上统一大小写。
        """
        resolved = str(Path(path).resolve())
        return os.path.normcase(resolved)

    @staticmethod
    def _count_midi_notes(midi_path: str) -> int:
        """计算 MIDI 文件中的音符数量

        Returns:
            音符数量，失败时返回 0
        """
        try:
            midi_file = mido.MidiFile(midi_path)
            count = 0
            for track in midi_file.tracks:
                for msg in track:
                    if msg.type == 'note_on' and msg.velocity > 0:
                        count += 1
            return count
        except Exception:
            return 0

    def _lookup_source_path(self, saved_path: str) -> Optional[str]:
        """从 index.json 反查 saved_path 对应的 source_path

        返回规范化后的 source_path，以便后续比较时一致。
        """
        index_path = self._edits_dir / "index.json"
        if not index_path.exists():
            print(f"[EditorWindow] _lookup_source_path: index.json not found")
            return None

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)

            normalized_saved = self._normalize_path(saved_path)
            for entry in index.get("files", []):
                entry_saved = entry.get("saved_path", "")
                if self._normalize_path(entry_saved) == normalized_saved:
                    source = entry.get("source_path", "")
                    # 返回规范化后的路径
                    return self._normalize_path(source) if source else None

            print(f"[EditorWindow] _lookup_source_path: no match for {saved_path}")
        except Exception as e:
            print(f"[EditorWindow] _lookup_source_path error: {e}")

        return None

    def _update_keyboard_range(self):
        """根据当前 MIDI 文件更新键盘可用音域范围"""
        if not self.piano_roll.notes:
            # 无音符时使用默认范围
            self.keyboard.set_available_range(*self.keyboard.NOTE_RANGE)
            return

        # 计算 MIDI 文件中的音符范围
        notes = [item.note for item in self.piano_roll.notes]
        note_min = min(notes)
        note_max = max(notes)

        # 扩展到完整八度边界 (C-B)
        octave_min = (note_min // 12) * 12  # 向下取整到 C
        octave_max = ((note_max // 12) + 1) * 12 - 1  # 向上取整到 B

        # 限制在 88 键范围内
        kbd_min, kbd_max = self.keyboard.NOTE_RANGE
        range_low = max(octave_min, kbd_min)
        range_high = min(octave_max, kbd_max)

        self.keyboard.set_available_range(range_low, range_high)

    def on_open(self):
        """打开 MIDI 文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open MIDI File", "",
            "MIDI Files (*.mid *.midi);;All Files (*)"
        )
        if path:
            self._open_with_version_check(path)

    def _open_with_version_check(self, path: str):
        """打开文件，检查是否有已编辑版本（与主界面逻辑一致）"""
        versions, stats = self.get_edited_versions(path, return_stats=True)

        # 显示索引维护结果（迁移/清理）
        self.show_index_maintenance_result(stats, parent=self)

        # 过滤 saved_path 不存在的版本（理论上 auto_cleanup 已处理，但双重保险）
        versions = [v for v in versions if os.path.exists(v.get("saved_path", ""))]

        if not versions:
            # 无已编辑版本，直接打开原始文件
            self.load_midi(path, source_path=path)
            return

        # 有已编辑版本（已按 last_modified 逆序排列，最新在前）
        # 构建选项列表：最新版本在第一位，原始文件在最后
        lang = getattr(self.parent(), "lang", LANG_ZH)
        items = []
        for v in versions:
            items.append(f"{v.get('display_name', 'Unknown')} ({v.get('edit_style', '?')})")
        items.append(tr("original_file", lang))

        from PyQt6.QtWidgets import QInputDialog
        choice, ok = QInputDialog.getItem(
            self, tr("select_version", lang), tr("select_version_prompt", lang),
            items, 0, False  # 默认选中第一项（最新版本）
        )

        if not ok:
            # 用户取消选择：自动加载最新保存版本
            # 传递 source_path=path 确保后续保存时使用正确的原始路径
            self.load_midi(versions[0].get("saved_path", path), source_path=path)
            return

        if choice == items[-1]:
            # 选择原始文件
            self.load_midi(path, source_path=path)
        else:
            # 选择已编辑版本
            idx = items.index(choice)
            saved_path = versions[idx].get("saved_path", path)
            # 传递 source_path=path 确保后续保存时使用正确的原始路径
            self.load_midi(saved_path, source_path=path)

    def on_save(self):
        """保存 (到默认路径)"""
        if not self.midi_path:
            self.on_save_as()
            return
        self._save_to_edits()

    def _on_edit_style_changed(self, text: str):
        """编辑风格变化"""
        self.edit_style = text

    def _on_input_style_changed(self, text: str):
        """输入风格变化 → 自动应用 jitter（仅当有选中音符时）"""
        selected = [item for item in self.piano_roll.notes if item.isSelected()]
        if selected:
            self._apply_input_style_jitter()

    def _on_quantize_changed(self, text: str):
        """量化分辨率变化

        Args:
            text: 分辨率文本 ("1/4", "1/8", "1/16", "1/32")
        """
        # 获取当前 BPM (从 spinbox)
        bpm = self.sp_bpm.value()

        # 解析分辨率
        resolution_map = {"1/4": 4, "1/8": 8, "1/16": 16, "1/32": 32}
        subdivision = resolution_map.get(text, 8)

        # 计算网格大小: (60 / bpm) * (4 / subdivision)
        # 例如 @120BPM, 1/8 = 0.25s, 1/16 = 0.125s
        grid_size = (60.0 / bpm) * (4.0 / subdivision)
        self.piano_roll.set_quantize_grid_size(grid_size)

    def _on_bpm_changed(self, value: int):
        """BPM 变化 (来自 spinbox)

        Performs true BPM scaling: scales all note times and updates display.
        """
        # Apply global BPM scaling (scales note times)
        # 注: _apply_global_bpm() 内部调用 _sync_timeline_tempo() 更新时间轴
        self._apply_global_bpm(value)

        # 重新计算量化网格（使用新 BPM）
        self._on_quantize_changed(self.cmb_quantize.currentText())
        self._update_bar_lines()

        # Notify main window of BPM change
        self.bpm_changed.emit(value)

    def _on_timeline_bpm_changed(self, bpm: int):
        """BPM 变化 (来自时间轴右键菜单)

        Performs true BPM scaling and syncs spinbox value.
        """
        # Apply global BPM scaling (scales note times)
        self._apply_global_bpm(bpm)

        # 更新 spinbox (阻止循环信号)
        self.sp_bpm.blockSignals(True)
        self.sp_bpm.setValue(bpm)
        self.sp_bpm.blockSignals(False)

        # 重新计算量化网格（使用新 BPM）
        self._on_quantize_changed(self.cmb_quantize.currentText())
        self._update_bar_lines()

        # Notify main window of BPM change
        self.bpm_changed.emit(bpm)

    def _on_timeline_select_range(self, start: float, end: float):
        """时间轴拖动选区 → 批量选中音符"""
        self.piano_roll.select_by_filter(time_range=(start, end))

    def _on_octave_shift_changed(self, value: int):
        """八度平移变化 - 实际修改音符数据

        When octave shift changes, actually transpose all notes by the delta.
        This modifies the underlying MIDI data, not just playback mapping.
        """
        delta = value - self._prev_octave_shift
        if delta == 0:
            return

        # Calculate semitone shift (octave = 12 semitones)
        semitone_shift = delta * 12

        # Transpose all notes
        for note_item in self.piano_roll.notes:
            note_item.note = max(0, min(127, note_item.note + semitone_shift))

        # Update previous value
        self._prev_octave_shift = value

        # Refresh display
        self.piano_roll._refresh_notes()

        # Update key list if visible
        if self.chk_key_list.isChecked():
            events = self.export_events()
            self.key_list.set_events(events)
            self.key_list.set_total_duration(self.piano_roll.total_duration)

        # Log the change
        self.statusBar().showMessage(
            f"Transposed all notes by {delta:+d} octave(s) ({semitone_shift:+d} semitones)", 3000
        )

    def _apply_input_style_jitter(self):
        """Apply input style timing jitter to notes (humanization).

        Gets the selected input style and applies random timing offset
        to selected notes (or all notes if none selected).
        Also applies duration variation based on the style.
        Uses QUndoCommand for proper undo/redo support.
        """
        # Get selected input style
        style_name = self.cmb_input_style.currentText()
        style = INPUT_STYLES.get(style_name)

        if style is None:
            QMessageBox.warning(
                self, tr("input_style"),
                tr("style_not_found_msg").format(name=style_name)
            )
            return

        # Check if style has any variation
        min_offset, max_offset = style.timing_offset_ms
        duration_var = style.duration_variation

        if min_offset == 0 and max_offset == 0 and duration_var == 0.0:
            QMessageBox.information(
                self, tr("input_style"),
                tr("style_no_variation").format(name=style_name)
            )
            return

        # Get target notes (selected or all)
        selected = [item for item in self.piano_roll.notes if item.isSelected()]
        if selected:
            target_notes = selected
        else:
            target_notes = list(self.piano_roll.notes)

        if not target_notes:
            QMessageBox.information(
                self, tr("input_style"),
                tr("no_notes_to_jitter")
            )
            return

        # Prepare note data for undo command
        notes_data = []
        for item in target_notes:
            notes_data.append({
                "note": item.note,
                "start": item.start_time,
                "duration": item.duration,
                "velocity": item.velocity
            })

        # Create and execute undo command
        cmd = ApplyJitterCommand(
            self.piano_roll,
            notes_data,
            timing_offset_ms=style.timing_offset_ms,
            duration_variation=duration_var,
            style_name=style_name
        )
        self.piano_roll.undo_stack.push(cmd)

        # Update key list if visible
        if self.chk_key_list.isChecked():
            events = self.export_events()
            self.key_list.set_events(events)
            self.key_list.set_total_duration(self.piano_roll.total_duration)

        # Emit notes changed for tracking
        self.piano_roll.sig_notes_changed.emit()

        # Log the change
        scope = tr("scope_selected") if selected else tr("scope_all")
        self.statusBar().showMessage(
            tr("jitter_applied").format(
                style=style_name,
                count=len(target_notes),
                scope=scope,
                min_offset=min_offset,
                max_offset=max_offset,
                duration_pct=abs(duration_var) * 100
            ),
            5000
        )

    def _apply_duration_delta(self):
        """应用时值调整到选中音符"""
        delta_ms = self.spin_duration_delta.value()
        if delta_ms == 0:
            return
        delta_sec = delta_ms / 1000.0
        self.piano_roll.adjust_selected_duration(delta_sec)
        # 更新 key list
        if self.chk_key_list.isChecked():
            events = self.export_events()
            self.key_list.set_events(events)
            self.key_list.set_total_duration(self.piano_roll.total_duration)
        # 重置 spinbox
        self.spin_duration_delta.setValue(0)

    def _apply_bar_duration_delta(self):
        """应用小节时值调整到选中小节内的音符"""
        delta_ms = self.spin_bar_duration_delta.value()
        if delta_ms == 0:
            return
        selected_bars = self.piano_roll.get_selected_bars()
        if not selected_bars:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                tr("no_bars_selected_title"),
                tr("no_bars_selected_msg")
            )
            return
        self.piano_roll.adjust_selected_bars_duration(delta_ms)
        # 更新 key list
        if self.chk_key_list.isChecked():
            events = self.export_events()
            self.key_list.set_events(events)
            self.key_list.set_total_duration(self.piano_roll.total_duration)
        # 更新 timeline duration
        self.timeline.set_duration(self.piano_roll.total_duration)
        # 重置 spinbox
        self.spin_bar_duration_delta.setValue(0)

    def _on_notes_changed_refresh(self):
        """当音符变化时刷新 key_list 和 timeline"""
        # 更新 key list
        if self.chk_key_list.isChecked():
            events = self.export_events()
            self.key_list.set_events(events)
            self.key_list.set_total_duration(self.piano_roll.total_duration)
        # 更新 timeline duration
        self.timeline.set_duration(self.piano_roll.total_duration)

    def _update_bar_lines(self):
        """更新钢琴卷帘的小节分隔线"""
        bpm = max(1, int(self.sp_bpm.value()))
        beats_per_bar = getattr(self.timeline, "time_sig_numerator", 4)
        beat_unit = getattr(self.timeline, "time_sig_denominator", 4)
        if beat_unit <= 0:
            self.piano_roll.set_bar_duration(0.0)
            return
        seconds_per_beat = (60.0 / bpm) * (4.0 / beat_unit)
        seconds_per_bar = seconds_per_beat * beats_per_bar
        self.piano_roll.set_bar_duration(seconds_per_bar)

    def _apply_global_bpm(self, new_bpm: int):
        """Apply global BPM change by scaling all note times.

        This method performs true BPM scaling:
        - Scales all note start_time and duration by old_bpm / new_bpm
        - Updates playback_time accordingly
        - Updates total_duration
        - Triggers piano roll redraw

        Args:
            new_bpm: The new BPM value
        """
        old_bpm = self._base_bpm
        if old_bpm <= 0 or new_bpm <= 0:
            return

        # Skip if BPM hasn't actually changed
        if old_bpm == new_bpm:
            return

        # Calculate scale factor: old_bpm / new_bpm
        # Higher BPM = shorter times, lower BPM = longer times
        scale = float(old_bpm) / float(new_bpm)

        # Scale playback time
        self.playback_time *= scale

        # Scale all notes in piano roll
        for note_item in self.piano_roll.notes:
            note_item.start_time *= scale
            note_item.duration *= scale

        # Update total duration
        if self.piano_roll.notes:
            self.piano_roll.total_duration = max(
                n.start_time + n.duration for n in self.piano_roll.notes
            )
        else:
            self.piano_roll.total_duration *= scale

        # Update base BPM to new value
        self._base_bpm = new_bpm

        # Trigger piano roll redraw
        self.piano_roll._redraw_all()

        # Update timeline duration
        self.timeline.set_duration(self.piano_roll.total_duration)

        # Update playhead position
        self.piano_roll.set_playhead_position(self.playback_time)
        self.timeline.set_playhead(self.playback_time)

        # Update time label
        self._update_time_label()

        # 同步时间轴 tempo 信息以更新拍刻度
        self._sync_timeline_tempo(new_bpm)

        # Emit notes changed signal for undo tracking
        self.piano_roll.sig_notes_changed.emit()

    def _get_current_bpm(self) -> float:
        """获取当前 BPM (从 MIDI 文件或默认 120)"""
        if self.midi_file:
            for track in self.midi_file.tracks:
                for msg in track:
                    if msg.type == "set_tempo":
                        return mido.tempo2bpm(msg.tempo)
        return 120.0

    def _sync_timeline_tempo(self, new_bpm: int):
        """同步时间轴的 tempo 信息以更新拍刻度。

        当 BPM 变更时调用此方法，重建 tempo_events 并刷新时间轴。

        Args:
            new_bpm: 新的 BPM 值
        """
        if not hasattr(self, '_ticks_per_beat') or self._ticks_per_beat is None:
            return
        if not hasattr(self, '_time_sig_events_tick'):
            self._time_sig_events_tick = [(0, 4, 4)]  # 默认 4/4

        # 用新 BPM 构建 tempo_events (tick 0 处设置新速度)
        tempo_events = [(0, mido.bpm2tempo(new_bpm))]
        self.timeline.set_tempo_info(
            self._ticks_per_beat,
            tempo_events,
            self._time_sig_events_tick
        )

    def on_save_as(self):
        """另存为"""
        if not self.midi_file:
            return

        # 默认文件名
        if self.midi_path:
            base = Path(self.midi_path).stem
            default_name = f"{base}_{self.edit_style}.mid"
        else:
            default_name = f"untitled_{self.edit_style}.mid"

        # 保存目录
        self._edits_dir.mkdir(parents=True, exist_ok=True)

        path, _ = QFileDialog.getSaveFileName(
            self, "Save MIDI As", str(self._edits_dir / default_name),
            "MIDI Files (*.mid *.midi)"
        )
        if path:
            self._save_midi(path)

    def _save_to_edits(self):
        """保存到 edits 目录"""
        if not self.midi_file or not self.midi_path:
            return

        self._edits_dir.mkdir(parents=True, exist_ok=True)

        base = Path(self.midi_path).stem
        save_path = self._edits_dir / f"{base}_{self.edit_style}.mid"

        self._save_midi(str(save_path))

    def _save_midi(self, path: str):
        """保存 MIDI 文件并更新索引

        从 piano_roll.notes 重建 MIDI 文件，而非直接保存原始文件。
        这样才能保存用户的编辑（移动、删除、修改音符等）。
        """
        try:
            # 强制同步音符位置：确保拖拽后的 start_time/note 已写回数据模型
            self.piano_roll._sync_notes_from_graphics()

            # 从 piano_roll.notes 重建 MIDI
            new_midi = self._rebuild_midi_from_notes()
            new_midi.save(path)

            # 更新索引
            self._update_index(path)

            # 提示保存成功（说明简化格式）
            QMessageBox.information(
                self, "Saved",
                f"Saved to:\n{path}\n\n"
                f"Format: Single track, {self.sp_bpm.value()} BPM\n"
                f"Note: Original tempo map and multi-track structure not preserved."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    def _rebuild_midi_from_notes(self) -> mido.MidiFile:
        """从 piano_roll.notes 重建 MIDI 文件

        使用用户设定的 BPM (来自工具栏 spinbox)，使用原始 channel。
        当前为简化单轨输出（多轨合并为单轨）。

        支持可变小节时长：如果 timeline 有 bar_durations，则为每个不同时长的小节
        生成对应的 tempo 事件。公式：microseconds_per_beat = bar_duration_sec / beats_per_bar * 1_000_000

        WARNING: 此方法会丢失原始 MIDI 的以下信息：
        - 原始 tempo map (多个速度变化事件) → 替换为单一用户 BPM 或可变小节时长
        - 多轨道结构 → 合并为单轨
        - 控制器事件、弯音、歌词等 → 仅保留音符

        如需保留原始 tempo map，应使用原始文件并仅应用音符编辑。

        Returns:
            mido.MidiFile: 重建的 MIDI 文件 (简化版，支持可变小节时长)
        """
        # 使用原始 ticks_per_beat，默认 480
        ticks_per_beat = 480
        if self.midi_file:
            ticks_per_beat = self.midi_file.ticks_per_beat

        # 获取节拍信息
        beats_per_bar = getattr(self.timeline, "time_sig_numerator", 4)
        beat_unit = getattr(self.timeline, "time_sig_denominator", 4)  # 拍号分母 (4=四分音符, 8=八分音符)

        # 检查是否有可变小节时长
        bar_durations = self.timeline.get_bar_durations()
        bar_times = self.timeline.get_bar_times()

        if bar_durations and bar_times:
            # 使用可变小节时长生成 tempo 事件
            # MIDI tempo 始终以"微秒/四分音符"计量，需要根据拍号分母调整
            # 公式: seconds_per_quarter = bar_duration_sec / beats_per_bar * 4 / beat_unit
            tempo_events = []
            prev_tempo = None
            for i, (bar_num, bar_start_sec) in enumerate(bar_times):
                if bar_num <= len(bar_durations):
                    bar_duration_sec = bar_durations[bar_num - 1]
                else:
                    # 超出定义范围，使用默认 BPM
                    bar_duration_sec = 60.0 / self.sp_bpm.value() * beats_per_bar * 4 / beat_unit

                # 计算此小节的 tempo (MIDI tempo = 微秒/四分音符)
                # 对于 4/4 拍: seconds_per_quarter = bar_duration / 4
                # 对于 3/8 拍: seconds_per_quarter = bar_duration / 3 * 4 / 8 = bar_duration / 3 * 0.5
                seconds_per_quarter = bar_duration_sec / beats_per_bar * 4 / beat_unit
                tempo = int(seconds_per_quarter * 1_000_000)  # 微秒/四分音符

                # 仅在 tempo 变化时添加事件（避免冗余）
                if tempo != prev_tempo:
                    # 转换小节起始时间为 ticks（相对于已有的 tempo_events）
                    start_tick = self._second_to_tick(bar_start_sec, tempo_events if tempo_events else [(0, tempo)], ticks_per_beat)
                    tempo_events.append((start_tick, tempo))
                    prev_tempo = tempo

            # 如果没有任何 tempo 事件，使用默认 BPM
            if not tempo_events:
                user_bpm = self.sp_bpm.value()
                user_tempo = mido.bpm2tempo(user_bpm)
                tempo_events = [(0, user_tempo)]
        else:
            # 使用用户设定的 BPM (来自工具栏 spinbox) 而非原始 MIDI tempo
            user_bpm = self.sp_bpm.value()
            user_tempo = mido.bpm2tempo(user_bpm)  # 转换为微秒/拍
            tempo_events = [(0, user_tempo)]  # 单一全局 tempo

        new_midi = mido.MidiFile(ticks_per_beat=ticks_per_beat)

        # 创建单轨道（简化输出，保留 channel 信息）
        track = mido.MidiTrack()
        new_midi.tracks.append(track)

        # 收集所有事件（tempo + 音符）
        events = []

        # 添加 tempo 事件
        for abs_tick, tempo in tempo_events:
            events.append((abs_tick, 'set_tempo', tempo, 0, 0))  # (tick, type, tempo, 0, 0)

        # 收集所有音符事件
        for note_item in self.piano_roll.notes:
            # 考虑拖拽偏移：pos() 返回相对于原始位置的偏移
            pos = note_item.pos()
            offset_time = pos.x() / self.piano_roll.pixels_per_second
            offset_note = -int(round(pos.y() / self.piano_roll.pixels_per_note))

            # 计算最终的时间和音高
            start_sec = note_item.start_time + offset_time
            end_sec = start_sec + note_item.duration
            note_pitch = note_item.note + offset_note

            # 确保有效范围
            start_sec = max(0.0, start_sec)
            note_pitch = max(0, min(127, note_pitch))
            velocity = max(1, min(127, note_item.velocity))
            channel = max(0, min(15, getattr(note_item, 'channel', 0)))

            # 使用 tempo map 转换时间到 ticks
            start_tick = self._second_to_tick(start_sec, tempo_events, ticks_per_beat)
            end_tick = self._second_to_tick(end_sec, tempo_events, ticks_per_beat)

            events.append((start_tick, 'note_on', note_pitch, velocity, channel))
            events.append((end_tick, 'note_off', note_pitch, 0, channel))

        # 按时间排序：tempo 优先，然后 note_off 优先于 note_on
        def sort_key(e):
            tick, msg_type = e[0], e[1]
            if msg_type == 'set_tempo':
                return (tick, 0)  # tempo 最先
            elif msg_type == 'note_off':
                return (tick, 1)  # note_off 次之
            else:
                return (tick, 2)  # note_on 最后

        events.sort(key=sort_key)

        # 转换为 delta time 并添加到轨道
        prev_tick = 0
        for event in events:
            abs_tick = event[0]
            msg_type = event[1]
            delta = abs_tick - prev_tick

            if msg_type == 'set_tempo':
                tempo = event[2]
                track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=delta))
            else:
                note_pitch = event[2]
                velocity = event[3]
                channel = event[4]
                track.append(mido.Message(msg_type, note=note_pitch, velocity=velocity,
                                          channel=channel, time=delta))
            prev_tick = abs_tick

        # 添加结束标记
        track.append(mido.MetaMessage('end_of_track', time=0))

        return new_midi

    def _extract_tempo_events(self) -> list:
        """从原始 MIDI 提取所有 tempo 事件

        Returns:
            list: [(abs_tick, tempo), ...] 按时间排序
        """
        tempo_events = []

        if self.midi_file:
            for track in self.midi_file.tracks:
                abs_tick = 0
                for msg in track:
                    abs_tick += msg.time
                    if msg.type == 'set_tempo':
                        tempo_events.append((abs_tick, msg.tempo))

        # 按 tick 排序
        tempo_events.sort(key=lambda x: x[0])

        # 如果没有 tempo 事件，添加默认 120 BPM
        if not tempo_events:
            tempo_events = [(0, 500000)]
        elif tempo_events[0][0] > 0:
            # 确保 tick 0 有 tempo
            tempo_events.insert(0, (0, 500000))

        return tempo_events

    def _extract_tempo_and_time_sig(self) -> tuple:
        """从原始 MIDI 提取 tempo 和 time signature 事件

        Returns:
            tuple: (tempo_events, time_sig_events)
                - tempo_events: [(abs_tick, tempo_microseconds), ...]
                - time_sig_events: [(abs_tick, numerator, denominator), ...]
        """
        tempo_events = []
        time_sig_events = []

        if self.midi_file:
            for track in self.midi_file.tracks:
                abs_tick = 0
                for msg in track:
                    abs_tick += msg.time
                    if msg.type == 'set_tempo':
                        tempo_events.append((abs_tick, msg.tempo))
                    elif msg.type == 'time_signature':
                        # mido time_signature: numerator, denominator
                        # mido 已将 denominator 转为实际值 (4, 8 等)
                        num = msg.numerator
                        denom = msg.denominator
                        time_sig_events.append((abs_tick, num, denom))

        # 按 tick 排序
        tempo_events.sort(key=lambda x: x[0])
        time_sig_events.sort(key=lambda x: x[0])

        # 确保有默认值
        if not tempo_events:
            tempo_events = [(0, 500000)]  # 120 BPM
        elif tempo_events[0][0] > 0:
            tempo_events.insert(0, (0, 500000))

        if not time_sig_events:
            time_sig_events = [(0, 4, 4)]  # 4/4 拍
        elif time_sig_events[0][0] > 0:
            time_sig_events.insert(0, (0, 4, 4))

        return tempo_events, time_sig_events

    def _second_to_tick(self, time_sec: float, tempo_events: list, ticks_per_beat: int) -> int:
        """使用 tempo map 将秒转换为 tick

        Args:
            time_sec: 时间（秒）
            tempo_events: [(abs_tick, tempo), ...] tempo 事件列表
            ticks_per_beat: MIDI ticks per beat

        Returns:
            int: 对应的 tick 值
        """
        if time_sec <= 0:
            return 0

        # 构建 tempo map: [(tick, tempo, cumulative_seconds), ...]
        tempo_map = []
        cumulative_sec = 0.0
        prev_tick = 0
        prev_tempo = tempo_events[0][1]

        for tick, tempo in tempo_events:
            if tick > prev_tick:
                # 计算这段的时间
                segment_sec = mido.tick2second(tick - prev_tick, ticks_per_beat, prev_tempo)
                cumulative_sec += segment_sec
            tempo_map.append((tick, tempo, cumulative_sec))
            prev_tick = tick
            prev_tempo = tempo

        # 找到 time_sec 落在哪个 tempo 段
        current_tick = 0
        current_sec = 0.0
        current_tempo = tempo_events[0][1]

        for i, (tick, tempo, cum_sec) in enumerate(tempo_map):
            if cum_sec >= time_sec:
                break
            current_tick = tick
            current_sec = cum_sec
            current_tempo = tempo

        # 计算剩余时间对应的 ticks
        remaining_sec = time_sec - current_sec
        remaining_ticks = int(mido.second2tick(remaining_sec, ticks_per_beat, current_tempo))

        return current_tick + remaining_ticks

    def _update_index(self, saved_path: str):
        """更新编辑文件索引

        写入元数据用于后续回退匹配验证:
        - source_file_size: 原始文件大小 (bytes)
        - source_note_count: 原始文件音符数量
        """
        index_path = self._edits_dir / "index.json"

        # 读取现有索引
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {"files": []}

        # 计算原始文件的元数据（基于 source_path，不是当前编辑状态）
        source_path = self._source_path or self._normalize_path(self.midi_path)
        source_file_size = 0
        source_note_count = 0

        try:
            # 从原始文件获取元数据
            resolved_source = Path(source_path).resolve()
            if resolved_source.exists():
                source_file_size = resolved_source.stat().st_size
                source_note_count = self._count_midi_notes(str(resolved_source))
        except Exception:
            pass

        # 添加/更新记录 - 使用 _source_path 而非 midi_path
        entry = {
            "source_path": source_path,
            "saved_path": self._normalize_path(saved_path),
            "display_name": Path(saved_path).stem,
            "edit_style": self.edit_style,
            "last_modified": datetime.now().isoformat(),
            # 元数据用于回退匹配验证
            "source_file_size": source_file_size,
            "source_note_count": source_note_count,
        }

        # 更新或追加 (使用规范化路径比较)
        normalized_saved = self._normalize_path(saved_path)
        found = False
        for i, e in enumerate(index["files"]):
            if self._normalize_path(e.get("saved_path", "")) == normalized_saved:
                index["files"][i] = entry
                found = True
                break
        if not found:
            index["files"].append(entry)

        # 写入
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def on_play_pause(self):
        """播放/暂停

        如果 Audio checkbox 被勾选，会尝试初始化音频引擎并播放声音。
        如果未勾选或音频初始化失败，仍然可以进行视觉预览（播放头移动）。
        """
        # In follow mode, delegate to main window (F5 toggle)
        if self._follow_mode:
            if self._main_window:
                self._main_window.on_toggle_play_pause()
            return

        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            self._release_all_notes()
            self.act_play.setText("Play")
        else:
            audio_enabled = self.chk_enable_audio.isChecked()

            # 仅在启用音频时尝试初始化 FluidSynth
            if audio_enabled:
                if not self._init_sound():
                    if not HAS_FLUIDSYNTH:
                        QMessageBox.warning(
                            self, "Audio Not Available",
                            "pyfluidsynth is not installed.\n"
                            "Please install it with: pip install pyfluidsynth\n\n"
                            "Visual playback will continue without audio."
                        )
                    else:
                        QMessageBox.warning(
                            self, "Audio Error",
                            "FluidSynth failed to initialize.\n"
                            "Possible causes:\n"
                            "- No audio driver available\n"
                            "- SoundFont file not found\n\n"
                            "Visual playback will continue without audio."
                        )
                    # 禁用音频复选框，允许视觉播放继续
                    self.chk_enable_audio.setChecked(False)

            self.is_playing = True
            # 从中间位置开始播放时，同步当前时刻的音符状态
            if self.chk_enable_audio.isChecked():
                self._sync_notes_at_time(self.playback_time)
            self.playback_timer.start()
            self.act_play.setText("Pause")

    def on_stop(self):
        """停止播放"""
        self.is_playing = False
        self.playback_timer.stop()
        self._release_all_notes()
        self.playback_time = 0.0
        self.piano_roll.set_playhead_position(0.0)
        self.timeline.set_playhead(0.0)
        self.act_play.setText("Play")
        self._update_time_label()
        # 重置按键列表
        self.key_list.reset()

    def on_seek(self, time_sec: float):
        """跳转到指定时间"""
        self.playback_time = time_sec
        self.piano_roll.set_playhead_position(time_sec)
        self.timeline.set_playhead(time_sec)
        self._update_time_label()
        # 更新按键列表进度
        if self.chk_key_list.isChecked():
            self.key_list.update_playback_time(time_sec)
        # 同步音符发声状态
        if self.is_playing:
            self._sync_notes_at_time(time_sec)

    def _sync_notes_at_time(self, time_sec: float):
        """同步指定时间点的音符发声状态

        计数差异补偿：正确处理重叠音符
        - new > old: 补发 (new-old) 次 noteon
        - new < old: 补发 (old-new) 次 noteoff
        - new == 0:  完全释放
        """
        if self._fs is None:
            self._active_notes.clear()
            return

        # 计算在 time_sec 时刻应该发声的音符及其计数
        new_active: Dict[int, int] = {}
        for note_item in self.piano_roll.notes:
            note = note_item.note
            start = note_item.start_time
            end = start + note_item.duration
            if start <= time_sec < end:
                new_active[note] = new_active.get(note, 0) + 1

        # 收集所有涉及的音符
        all_notes = set(self._active_notes.keys()) | set(new_active.keys())

        for note in all_notes:
            old_count = self._active_notes.get(note, 0)
            new_count = new_active.get(note, 0)

            if new_count > old_count:
                # 需要补发 noteon
                # 获取该音高的 velocity (取第一个匹配音符)
                velocity = 100
                for note_item in self.piano_roll.notes:
                    if note_item.note == note:
                        start = note_item.start_time
                        end = start + note_item.duration
                        if start <= time_sec < end:
                            velocity = note_item.velocity
                            break
                for _ in range(new_count - old_count):
                    self._fs.noteon(self._chan, note, velocity)
            elif new_count < old_count:
                # 需要补发 noteoff
                for _ in range(old_count - new_count):
                    self._fs.noteoff(self._chan, note)

        self._active_notes = new_active

    def on_zoom_changed(self, value: int):
        """缩放变化 (来自滑条)"""
        self.piano_roll.pixels_per_second = float(value)
        self.piano_roll._refresh_notes()
        self.timeline.set_scale(float(value))
        # 同步按键进度窗
        if self.chk_key_list.isChecked():
            self.key_list.set_scale(float(value))

    def _on_piano_roll_zoom(self, pixels_per_second: float):
        """缩放变化 (来自 Ctrl+滚轮)"""
        # 同步时间轴
        self.timeline.set_scale(pixels_per_second)
        # 同步滑条 (避免循环触发)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(pixels_per_second))
        self.zoom_slider.blockSignals(False)
        # 同步按键进度窗
        if self.chk_key_list.isChecked():
            self.key_list.set_scale(pixels_per_second)

    def _on_row_height_changed(self, pixels_per_note: float):
        """行高变化 (来自 Ctrl+Up/Down 或 [ ])"""
        # 同步键盘高度
        self.keyboard.set_scale(pixels_per_note)
        # 同步 Y 滑条 (避免循环触发)
        self.zoom_y_slider.blockSignals(True)
        self.zoom_y_slider.setValue(int(pixels_per_note))
        self.zoom_y_slider.blockSignals(False)

    def _on_zoom_y_changed(self, value: int):
        """Y 轴缩放滑条变化"""
        # 调用 piano_roll 的行高调整 (会触发 sig_row_height_changed → 同步键盘)
        delta = value - self.piano_roll.pixels_per_note
        if abs(delta) > 0.1:
            self.piano_roll._adjust_row_height(delta)

    def _update_playback(self):
        """更新播放位置"""
        if not self.is_playing:
            return

        prev_time = self.playback_time
        self.playback_time += 0.016  # ~16ms per tick (BPM scaling is applied to note times)

        # 检查是否结束
        if self.playback_time >= self.piano_roll.total_duration:
            self.on_stop()
            return

        # 触发音符发声 (仅在音频启用且初始化成功时)
        # 注：每个音符事件都发送 noteon/noteoff，即使同音高重叠。
        # FluidSynth 对同 channel+note 的多次 noteon 会产生叠加效果（重触发）。
        # 引用计数用于跟踪活跃数量，便于 seek 时同步状态。
        if self._fs is not None and self.chk_enable_audio.isChecked():
            for note_item in self.piano_roll.notes:
                note = note_item.note
                start = note_item.start_time
                end = start + note_item.duration

                # 进入音符区间 → note on (每次都触发，引用计数 +1)
                if prev_time < start <= self.playback_time:
                    self._fs.noteon(self._chan, note, note_item.velocity)
                    self._active_notes[note] = self._active_notes.get(note, 0) + 1

                # 离开音符区间 → note off (每次都触发，引用计数 -1)
                if prev_time < end <= self.playback_time:
                    self._fs.noteoff(self._chan, note)
                    if note in self._active_notes:
                        self._active_notes[note] -= 1
                        if self._active_notes[note] <= 0:
                            del self._active_notes[note]

        self.piano_roll.set_playhead_position(self.playback_time)
        self.timeline.set_playhead(self.playback_time)
        self._update_time_label()

        # 更新按键列表进度
        if self.chk_key_list.isChecked():
            self.key_list.update_playback_time(self.playback_time)

    def _update_time_label(self):
        """更新时间显示"""
        current = self.playback_time
        total = self.piano_roll.total_duration

        def fmt(t):
            m = int(t // 60)
            s = t % 60
            return f"{m}:{s:04.1f}"

        self.lbl_time.setText(f"{fmt(current)} / {fmt(total)}")

    # ─────────────────────────────────────────────────────────────────────────
    # FluidSynth 相关方法
    # ─────────────────────────────────────────────────────────────────────────

    def _init_sound(self) -> bool:
        """初始化 FluidSynth (懒加载)"""
        if self._fs is not None:
            return True

        if not HAS_FLUIDSYNTH:
            return False

        try:
            fs = fluidsynth.Synth(gain=0.8, samplerate=44100)
            fs.setting('audio.period-size', 1024)
            fs.setting('audio.periods', 4)

            # 尝试不同的音频驱动
            if sys.platform == 'win32':
                drivers = ['dsound', 'wasapi', 'portaudio']
            else:
                drivers = ['pulseaudio', 'alsa', 'coreaudio', 'portaudio']

            started = False
            for driver in drivers:
                try:
                    fs.start(driver=driver)
                    started = True
                    break
                except Exception:
                    continue

            if not started:
                fs.delete()
                return False

            # 加载 SoundFont
            sf_paths = [
                self._app_root / "assets" / "FluidR3_GM.sf2",
                self._app_root / "FluidR3_GM.sf2",
                Path("C:/soundfonts/FluidR3_GM.sf2"),
            ]

            sfid = -1
            for sf_path in sf_paths:
                if sf_path.exists():
                    sfid = fs.sfload(str(sf_path))
                    if sfid >= 0:
                        break

            if sfid < 0:
                fs.delete()
                return False

            fs.program_select(self._chan, sfid, 0, 0)  # Piano

            self._fs = fs
            self._sfid = sfid
            return True

        except Exception:
            return False

    def _release_all_notes(self):
        """释放所有正在发声的音符

        按计数发送 noteoff：每个重叠音符都需要单独释放
        """
        if self._fs is None:
            self._active_notes.clear()
            return
        for note, count in list(self._active_notes.items()):
            for _ in range(count):
                self._fs.noteoff(self._chan, note)
        self._active_notes.clear()

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self._release_all_notes()
        if self._fs is not None:
            self._fs.delete()
            self._fs = None
        super().closeEvent(event)

    @classmethod
    def get_edited_versions(
        cls,
        source_path: str,
        auto_cleanup: bool = True,
        return_stats: bool = False
    ):
        """获取指定 MIDI 的已编辑版本列表（按 last_modified 逆序）

        使用规范化路径比较，避免大小写/斜杠差异导致匹配失败。
        如果正向匹配为空，尝试多重回退策略进行反向匹配并自动迁移索引。

        回退策略（按优先级）:
        1. source_path 旧格式规范化后匹配（处理斜杠/大小写差异）
        2. 文件名 + edit_style + 元数据验证（file_size + note_count）
        3. 文件名前缀 + 有效 style 验证（兜底）

        Args:
            source_path: 原始 MIDI 文件路径
            auto_cleanup: 是否自动清理无效条目（saved_path 不存在）
            return_stats: 是否返回统计信息（用于 GUI 提示）

        Returns:
            如果 return_stats=False: list - 版本列表
            如果 return_stats=True: tuple(list, dict) - (版本列表, 统计信息)
                统计信息格式: {"migrated": int, "cleaned": int, "cleaned_paths": list}
        """
        stats = {"migrated": 0, "cleaned": 0, "cleaned_paths": []}

        # 计算 edits_dir：基于此文件所在的 LyreAutoPlayer 根目录
        app_root = Path(__file__).parent.parent.parent
        edits_dir = app_root / "midi-change"
        index_path = edits_dir / "index.json"

        if not index_path.exists():
            return ([], stats) if return_stats else []

        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

        # 规范化输入路径 (使用 _normalize_path 统一格式)
        normalized_source = cls._normalize_path(source_path)
        source_stem = Path(source_path).stem.lower()  # 文件名（无扩展名），小写

        # 获取源文件元数据用于回退验证
        source_file_size = 0
        source_note_count = 0
        try:
            resolved_source = Path(source_path).resolve()
            if resolved_source.exists():
                source_file_size = resolved_source.stat().st_size
                source_note_count = cls._count_midi_notes(str(resolved_source))
        except Exception:
            pass

        # 过滤出当前源文件的版本 (使用规范化路径比较)
        versions = []
        needs_migration = False
        invalid_entries = []  # 记录无效条目索引

        for idx, e in enumerate(index.get("files", [])):
            entry_source = e.get("source_path", "")
            saved_path = e.get("saved_path", "")

            # 检查 saved_path 是否存在
            if saved_path and not os.path.exists(saved_path):
                invalid_entries.append(idx)
                continue

            try:
                entry_normalized = cls._normalize_path(entry_source)
                if entry_normalized == normalized_source:
                    versions.append(e)
            except Exception:
                # 路径无效，跳过
                continue

        # 如果正向匹配为空，尝试多重回退策略
        if not versions:
            # 回退策略 1: 文件名 + edit_style + 元数据验证
            # saved_path 格式: "{source_stem}_{style}.mid"
            for e in index.get("files", []):
                saved_path = e.get("saved_path", "")
                edit_style = e.get("edit_style", "")
                if not saved_path or not edit_style:
                    continue

                # 检查文件是否存在
                if not os.path.exists(saved_path):
                    continue

                saved_stem = Path(saved_path).stem.lower()
                expected_stem = f"{source_stem}_{edit_style}".lower()

                if saved_stem == expected_stem:
                    # 元数据验证：file_size + note_count（双重校验）
                    if not cls._validate_metadata(e, source_file_size, source_note_count, saved_stem):
                        continue

                    # 精确匹配成功，迁移
                    e["source_path"] = cls._normalize_path(source_path)
                    versions.append(e)
                    needs_migration = True

            # 回退策略 2: 文件名前缀 + 有效 style 验证（兜底）
            # 仅当策略 1 没有找到任何匹配时才使用
            if not versions:
                for e in index.get("files", []):
                    saved_path = e.get("saved_path", "")
                    if not saved_path:
                        continue

                    if not os.path.exists(saved_path):
                        continue

                    saved_stem = Path(saved_path).stem.lower()

                    # 检查 saved_stem 是否以 source_stem 开头（后跟 _style）
                    if saved_stem.startswith(source_stem + "_"):
                        # 额外验证：saved_stem 去掉前缀后应该是有效的 edit_style
                        suffix = saved_stem[len(source_stem) + 1:]
                        if suffix in [s.lower() for s in cls.EDIT_STYLES]:
                            # 元数据验证
                            if not cls._validate_metadata(e, source_file_size, source_note_count, saved_stem):
                                continue

                            e["source_path"] = cls._normalize_path(source_path)
                            versions.append(e)
                            needs_migration = True

        # 自动清理无效条目（saved_path 不存在）
        index_modified = needs_migration
        if auto_cleanup and invalid_entries:
            # 从后往前删除，避免索引偏移
            for idx in sorted(invalid_entries, reverse=True):
                removed = index["files"].pop(idx)
                removed_path = removed.get('saved_path', '?')
                stats["cleaned_paths"].append(removed_path)
                print(f"[EditorWindow] Removed invalid entry: {removed_path}")
            stats["cleaned"] = len(invalid_entries)
            index_modified = True

        # 记录迁移数量
        if needs_migration:
            stats["migrated"] = len(versions)

        # 如果有修改，写回 index.json
        if index_modified:
            try:
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index, f, indent=2, ensure_ascii=False)
                if needs_migration:
                    print(f"[EditorWindow] Index migrated: {len(versions)} entries updated")
                if invalid_entries:
                    print(f"[EditorWindow] Index cleaned: {len(invalid_entries)} invalid entries removed")
            except Exception as ex:
                print(f"[EditorWindow] Index update failed: {ex}")

        # 按 last_modified 逆序排序（最新在前）
        versions.sort(key=lambda x: x.get("last_modified", ""), reverse=True)

        return (versions, stats) if return_stats else versions

    @classmethod
    def _validate_metadata(
        cls,
        entry: dict,
        source_file_size: int,
        source_note_count: int,
        saved_stem: str
    ) -> bool:
        """验证索引条目的元数据是否匹配源文件

        同时检查 file_size 和 note_count，任一不匹配则拒绝。
        允许 10% 误差（考虑到文件可能被轻微修改）。

        Returns:
            True: 元数据匹配或无法验证（无元数据）
            False: 元数据明确不匹配
        """
        entry_file_size = entry.get("source_file_size", 0)
        entry_note_count = entry.get("source_note_count", 0)

        # 验证 file_size
        if entry_file_size > 0 and source_file_size > 0:
            size_diff = abs(entry_file_size - source_file_size)
            if size_diff > source_file_size * 0.1:
                print(f"[EditorWindow] Metadata mismatch: {saved_stem} "
                      f"(size {entry_file_size} vs {source_file_size})")
                return False

        # 验证 note_count
        if entry_note_count > 0 and source_note_count > 0:
            count_diff = abs(entry_note_count - source_note_count)
            # 允许 10% 误差，但至少允许 5 个音符的差异（小文件容忍度）
            tolerance = max(source_note_count * 0.1, 5)
            if count_diff > tolerance:
                print(f"[EditorWindow] Metadata mismatch: {saved_stem} "
                      f"(note_count {entry_note_count} vs {source_note_count})")
                return False

        return True

    @classmethod
    def show_index_maintenance_result(cls, stats: dict, parent=None):
        """显示索引维护结果的 GUI 提示

        Args:
            stats: get_edited_versions 返回的统计信息
            parent: 父窗口（用于 QMessageBox）
        """
        migrated = stats.get("migrated", 0)
        cleaned = stats.get("cleaned", 0)

        if migrated == 0 and cleaned == 0:
            return  # 无需提示

        lines = []
        if migrated > 0:
            lines.append(f"• Migrated {migrated} index entries to new format")
        if cleaned > 0:
            lines.append(f"• Removed {cleaned} invalid entries (files no longer exist)")
            # 显示被清理的路径（最多 5 个）
            cleaned_paths = stats.get("cleaned_paths", [])
            if cleaned_paths:
                lines.append("")
                lines.append("Removed entries:")
                for p in cleaned_paths[:5]:
                    lines.append(f"  - {Path(p).name}")
                if len(cleaned_paths) > 5:
                    lines.append(f"  ... and {len(cleaned_paths) - 5} more")

        QMessageBox.information(
            parent,
            "Index Maintenance",
            "\n".join(lines)
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Unified Playback: Follow Mode Methods
    # ─────────────────────────────────────────────────────────────────────────

    def set_follow_mode(self, follow: bool):
        """Switch to follow mode (disable local playback + audio).

        In follow mode, the editor follows PlayerThread signals instead of
        using its internal QTimer-based playback.
        """
        self._follow_mode = follow
        if follow:
            # Stop local playback timer
            self.playback_timer.stop()
            self._release_all_notes()  # Stop FluidSynth

            # Save original audio state before disabling (Pitfall #5)
            self._audio_was_enabled = self.chk_enable_audio.isChecked()

            # Force disable audio checkbox (禁止双重发声)
            self.chk_enable_audio.setChecked(False)
            self.chk_enable_audio.setEnabled(False)

            self.is_playing = True  # Visual state
            self.act_play.setText("Pause")
        else:
            # Restore audio checkbox to original state (Pitfall #5)
            self.chk_enable_audio.setEnabled(True)
            if hasattr(self, '_audio_was_enabled'):
                self.chk_enable_audio.setChecked(self._audio_was_enabled)

            self.is_playing = False
            self.act_play.setText("Play")

    def export_events(self) -> list:
        """Export current piano_roll notes as event list for PlayerThread.

        Returns:
            List of note event dicts sorted by time.
        """
        # Sync drag offsets to notes data (Pitfall #1)
        self.piano_roll._sync_notes_from_graphics()

        events = []
        for note_item in self.piano_roll.notes:
            events.append({
                "time": note_item.start_time,
                "note": note_item.note,
                "duration": note_item.duration,
                "velocity": getattr(note_item, 'velocity', 80),
                "channel": getattr(note_item, 'channel', 0),
            })
        return sorted(events, key=lambda e: e["time"])

    def get_bar_duration(self) -> float:
        """Calculate bar duration from current editor BPM and time signature.

        Returns:
            Bar duration in seconds.
        """
        bpm = self.sp_bpm.value() if hasattr(self, 'sp_bpm') else 120
        # Get time signature from timeline
        numerator = self.timeline.time_sig_numerator if hasattr(self, 'timeline') else 4
        denominator = self.timeline.time_sig_denominator if hasattr(self, 'timeline') else 4
        # BPM is quarter-note based, adjust for denominator
        # E.g., 3/4: 3 quarter notes = 3 * (60/BPM)
        # E.g., 6/8: 6 eighth notes = 6 * (60/BPM) * (4/8) = 3 * (60/BPM)
        beats_per_bar = numerator * (4.0 / denominator)
        return 60.0 / bpm * beats_per_bar

    def get_pause_bars(self) -> int:
        """Get auto-pause interval (bars).

        Returns:
            Number of bars between auto-pauses (0 = disabled).
        """
        return self.cmb_pause_bars.currentData() if hasattr(self, 'cmb_pause_bars') else 0

    def get_auto_resume_countdown(self) -> int:
        """Get auto-resume countdown seconds.

        Returns:
            Countdown seconds before auto-resume.
        """
        return self.sp_auto_resume.value() if hasattr(self, 'sp_auto_resume') else 3

    def get_octave_shift(self) -> int:
        """Get overall octave shift.

        Returns:
            Octave shift (-2 to +2).
        """
        return self.sp_octave_shift.value() if hasattr(self, 'sp_octave_shift') else 0

    def get_input_style(self) -> str:
        """Get selected input style for playback.

        Returns:
            Input style name (e.g., 'mechanical', 'gentle').
        """
        if hasattr(self, 'cmb_input_style'):
            return self.cmb_input_style.currentText()
        return "mechanical"

    def _populate_input_styles(self):
        """Populate input style combo box from registry."""
        self.cmb_input_style.clear()
        styles = get_style_names()
        self.cmb_input_style.addItems(styles)
        # Default to 'mechanical' if available
        if "mechanical" in styles:
            self.cmb_input_style.setCurrentText("mechanical")

    def on_external_progress(self, current_time: float, total_duration: float):
        """Called by PlayerThread.progress signal.

        Updates playhead position in the editor without playing audio.
        """
        if not self._follow_mode:
            return

        self.playback_time = current_time
        self.piano_roll.set_playhead_position(current_time)
        self.timeline.set_playhead(current_time)
        self._update_time_label()
        # 更新按键列表进度
        if self.chk_key_list.isChecked():
            self.key_list.update_playback_time(current_time)
        # NO FluidSynth audio in follow mode (已禁用)

    def on_external_paused(self):
        """Called when PlayerThread pauses."""
        if self._follow_mode:
            self.act_play.setText("Play")

    def on_external_resumed(self):
        """Called when PlayerThread resumes (after pause or auto-pause countdown)."""
        if self._follow_mode:
            self.act_play.setText("Pause")
            # Clear countdown overlay when resumed
            self._countdown_overlay.hide_countdown()

    def on_external_stopped(self):
        """Called when PlayerThread finishes."""
        self.set_follow_mode(False)
        self.on_stop()

    def update_countdown(self, remaining: int):
        """Called by PlayerThread.countdown_tick signal.

        Args:
            remaining: Seconds remaining (0 = countdown finished)
        """
        if remaining > 0:
            # Update hint text with i18n (get lang from parent/main window)
            lang = getattr(self.parent(), "lang", LANG_ZH)
            self._countdown_overlay.update_hint_text(tr("press_f5_continue", lang))
            self._countdown_overlay.show_countdown(remaining)
        else:
            self._countdown_overlay.hide_countdown()

    def resizeEvent(self, event):
        """Handle resize to keep countdown overlay sized correctly."""
        super().resizeEvent(event)
        # Update overlay geometry to match piano_roll
        self._countdown_overlay.setGeometry(self.piano_roll.rect())
