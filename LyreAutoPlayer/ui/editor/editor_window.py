"""
EditorWindow - MIDI 编辑器主窗口
"""
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QSlider, QLabel, QFileDialog, QMessageBox,
    QSplitter, QScrollBar, QComboBox
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QTimer
import mido

from .piano_roll import PianoRollWidget
from .timeline import TimelineWidget
from .keyboard import KeyboardWidget
from i18n import tr, LANG_ZH


class EditorWindow(QMainWindow):
    """MIDI 编辑器主窗口"""

    # 编辑风格选项
    EDIT_STYLES = ["custom", "simplified", "transposed", "extended", "practice"]

    def __init__(self, midi_path: Optional[str] = None, parent=None):
        super().__init__(parent)

        # 计算 EDITS_DIR：基于此文件所在的 LyreAutoPlayer 根目录
        self._app_root = Path(__file__).parent.parent.parent  # ui/editor -> ui -> LyreAutoPlayer
        self._edits_dir = self._app_root / "midi-change"

        self.midi_path = midi_path
        self.midi_file: Optional[mido.MidiFile] = None
        self.is_playing = False
        self.playback_time = 0.0
        self.edit_style = "custom"  # 编辑风格标签

        self._setup_ui()
        self._setup_toolbar()
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

        # 左上角占位
        corner = QWidget()
        corner.setFixedSize(60, 30)
        corner.setStyleSheet("background-color: #282828;")
        timeline_row.addWidget(corner)

        self.timeline = TimelineWidget()
        timeline_row.addWidget(self.timeline)

        main_layout.addLayout(timeline_row)

        # 键盘 + 卷帘
        content_row = QHBoxLayout()
        content_row.setSpacing(0)

        self.keyboard = KeyboardWidget()
        content_row.addWidget(self.keyboard)

        self.piano_roll = PianoRollWidget()
        content_row.addWidget(self.piano_roll)

        main_layout.addLayout(content_row)

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

        toolbar.addSeparator()

        # 缩放
        toolbar.addWidget(QLabel(" Zoom: "))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(20, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)
        toolbar.addWidget(self.zoom_slider)

        # 时间显示
        toolbar.addWidget(QLabel("  "))
        self.lbl_time = QLabel("0:00.0 / 0:00.0")
        toolbar.addWidget(self.lbl_time)

        toolbar.addSeparator()

        # 编辑风格选择
        toolbar.addWidget(QLabel(" Style: "))
        self.cmb_edit_style = QComboBox()
        self.cmb_edit_style.addItems(self.EDIT_STYLES)
        self.cmb_edit_style.setCurrentText(self.edit_style)
        self.cmb_edit_style.setFixedWidth(100)
        toolbar.addWidget(self.cmb_edit_style)

    def _setup_connections(self):
        """连接信号槽"""
        self.act_open.triggered.connect(self.on_open)
        self.act_save.triggered.connect(self.on_save)
        self.act_save_as.triggered.connect(self.on_save_as)
        self.act_play.triggered.connect(self.on_play_pause)
        self.act_stop.triggered.connect(self.on_stop)

        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.playback_timer.timeout.connect(self._update_playback)
        self.timeline.sig_seek.connect(self.on_seek)
        self.cmb_edit_style.currentTextChanged.connect(self._on_edit_style_changed)

        # 同步滚动
        self.piano_roll.horizontalScrollBar().valueChanged.connect(
            lambda v: self.timeline.set_scroll_offset(v)
        )
        self.piano_roll.verticalScrollBar().valueChanged.connect(
            lambda v: self.keyboard.set_scroll_offset(v)
        )

        # 同步缩放 (Ctrl+滚轮 → 时间轴 + 滑条)
        self.piano_roll.sig_zoom_changed.connect(self._on_piano_roll_zoom)

    def load_midi(self, path: str):
        """加载 MIDI 文件"""
        try:
            self.midi_file = mido.MidiFile(path)
            self.midi_path = path
            self.piano_roll.load_midi(self.midi_file)

            # 更新时间轴
            self.timeline.set_duration(self.piano_roll.total_duration)
            self.timeline.set_scale(self.piano_roll.pixels_per_second)

            # 更新窗口标题
            filename = os.path.basename(path)
            self.setWindowTitle(f"MIDI Editor - {filename}")

            # 重置播放
            self.playback_time = 0.0
            self._update_time_label()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load MIDI:\n{e}")

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
        versions = self.get_edited_versions(path)

        # 过滤 saved_path 不存在的版本
        versions = [v for v in versions if os.path.exists(v.get("saved_path", ""))]

        if not versions:
            # 无已编辑版本，直接打开原始文件
            self.load_midi(path)
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
            self.load_midi(versions[0].get("saved_path", path))
            return

        if choice == items[-1]:
            # 选择原始文件
            self.load_midi(path)
        else:
            # 选择已编辑版本
            idx = items.index(choice)
            saved_path = versions[idx].get("saved_path", path)
            self.load_midi(saved_path)

    def on_save(self):
        """保存 (到默认路径)"""
        if not self.midi_path:
            self.on_save_as()
            return
        self._save_to_edits()

    def _on_edit_style_changed(self, text: str):
        """编辑风格变化"""
        self.edit_style = text

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
        """保存 MIDI 文件并更新索引"""
        try:
            # TODO: 从 piano_roll 重建 MIDI (Phase 2)
            # 目前直接保存原始文件
            self.midi_file.save(path)

            # 更新索引
            self._update_index(path)

            QMessageBox.information(self, "Saved", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    def _update_index(self, saved_path: str):
        """更新编辑文件索引"""
        index_path = self._edits_dir / "index.json"

        # 读取现有索引
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {"files": []}

        # 添加/更新记录
        entry = {
            "source_path": self.midi_path,
            "saved_path": str(saved_path),
            "display_name": Path(saved_path).stem,
            "edit_style": self.edit_style,
            "last_modified": datetime.now().isoformat()
        }

        # 更新或追加
        found = False
        for i, e in enumerate(index["files"]):
            if e.get("saved_path") == str(saved_path):
                index["files"][i] = entry
                found = True
                break
        if not found:
            index["files"].append(entry)

        # 写入
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def on_play_pause(self):
        """播放/暂停"""
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            self.act_play.setText("Play")
        else:
            self.is_playing = True
            self.playback_timer.start()
            self.act_play.setText("Pause")

    def on_stop(self):
        """停止播放"""
        self.is_playing = False
        self.playback_timer.stop()
        self.playback_time = 0.0
        self.piano_roll.set_playhead_position(0.0)
        self.timeline.set_playhead(0.0)
        self.act_play.setText("Play")
        self._update_time_label()

    def on_seek(self, time_sec: float):
        """跳转到指定时间"""
        self.playback_time = time_sec
        self.piano_roll.set_playhead_position(time_sec)
        self.timeline.set_playhead(time_sec)
        self._update_time_label()

    def on_zoom_changed(self, value: int):
        """缩放变化 (来自滑条)"""
        self.piano_roll.pixels_per_second = float(value)
        self.piano_roll._refresh_notes()
        self.timeline.set_scale(float(value))

    def _on_piano_roll_zoom(self, pixels_per_second: float):
        """缩放变化 (来自 Ctrl+滚轮)"""
        # 同步时间轴
        self.timeline.set_scale(pixels_per_second)
        # 同步滑条 (避免循环触发)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(pixels_per_second))
        self.zoom_slider.blockSignals(False)

    def _update_playback(self):
        """更新播放位置"""
        if not self.is_playing:
            return

        self.playback_time += 0.016  # ~16ms

        # 检查是否结束
        if self.playback_time >= self.piano_roll.total_duration:
            self.on_stop()
            return

        self.piano_roll.set_playhead_position(self.playback_time)
        self.timeline.set_playhead(self.playback_time)
        self._update_time_label()

    def _update_time_label(self):
        """更新时间显示"""
        current = self.playback_time
        total = self.piano_roll.total_duration

        def fmt(t):
            m = int(t // 60)
            s = t % 60
            return f"{m}:{s:04.1f}"

        self.lbl_time.setText(f"{fmt(current)} / {fmt(total)}")

    @classmethod
    def get_edited_versions(cls, source_path: str) -> list:
        """获取指定 MIDI 的已编辑版本列表（按 last_modified 逆序）"""
        # 计算 edits_dir：基于此文件所在的 LyreAutoPlayer 根目录
        app_root = Path(__file__).parent.parent.parent
        edits_dir = app_root / "midi-change"
        index_path = edits_dir / "index.json"

        if not index_path.exists():
            return []

        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

        # 过滤出当前源文件的版本
        versions = [
            e for e in index.get("files", [])
            if e.get("source_path") == source_path
        ]

        # 按 last_modified 逆序排序（最新在前）
        versions.sort(key=lambda x: x.get("last_modified", ""), reverse=True)

        return versions
