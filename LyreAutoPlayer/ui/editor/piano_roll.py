"""
PianoRollWidget - 钢琴卷帘主视图
"""
from typing import List, Optional
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem
from PyQt6.QtGui import QPen, QColor, QWheelEvent
from PyQt6.QtCore import Qt, pyqtSignal
import mido

from .note_item import NoteItem


class PianoRollWidget(QGraphicsView):
    """钢琴卷帘主视图 - 显示 MIDI 音符"""

    sig_note_selected = pyqtSignal(list)       # 选中的音符列表
    sig_playback_position = pyqtSignal(float)  # 播放位置 (秒)
    sig_zoom_changed = pyqtSignal(float)       # 水平缩放变化 (pixels_per_second)

    # 常量
    NOTE_RANGE = (21, 108)  # A0 to C8 (标准 88 键)
    GRID_COLOR_LIGHT = QColor(60, 60, 60)
    GRID_COLOR_DARK = QColor(45, 45, 45)
    PLAYHEAD_COLOR = QColor(255, 0, 0)
    BG_COLOR = QColor(30, 30, 30)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 场景
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(self.BG_COLOR)

        # 缩放参数
        self.pixels_per_second = 100.0  # 水平缩放
        self.pixels_per_note = 12.0     # 垂直缩放 (每个半音高度)

        # 音符项列表
        self.notes: List[NoteItem] = []

        # 播放头
        self.playhead: Optional[QGraphicsLineItem] = None
        self._playhead_time = 0.0

        # MIDI 数据
        self.midi_file: Optional[mido.MidiFile] = None
        self.total_duration = 0.0

        # 视图设置
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        # 关闭抗锯齿以提高性能
        from PyQt6.QtGui import QPainter
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def load_midi(self, midi_file: mido.MidiFile):
        """加载 MIDI 文件并创建音符图形项"""
        self.midi_file = midi_file
        self.scene.clear()
        self.notes.clear()

        # 解析 MIDI
        notes_data = self._parse_midi(midi_file)

        # 计算总时长
        if notes_data:
            self.total_duration = max(n["start"] + n["duration"] for n in notes_data)
        else:
            self.total_duration = 0.0

        # 创建音符图形项
        note_max = self.NOTE_RANGE[1]
        for nd in notes_data:
            item = NoteItem(
                note=nd["note"],
                start_time=nd["start"],
                duration=nd["duration"],
                velocity=nd["velocity"],
                track=nd.get("track", 0)
            )
            item.update_geometry(self.pixels_per_second, self.pixels_per_note, note_max)
            self.scene.addItem(item)
            self.notes.append(item)

        # 绘制网格
        self._draw_grid()

        # 创建播放头
        self._create_playhead()

        # 设置场景大小
        scene_width = self.total_duration * self.pixels_per_second + 100
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        self.scene.setSceneRect(0, 0, scene_width, scene_height)

    def _parse_midi(self, midi_file: mido.MidiFile) -> List[dict]:
        """解析 MIDI 文件，提取音符信息

        使用 tempo map 正确处理速度变化，支持同音高重叠音符
        """
        notes = []
        ticks_per_beat = midi_file.ticks_per_beat

        # 1. 首先收集所有轨道的 tempo 事件构建 tempo map
        tempo_map = []  # [(abs_tick, tempo), ...]
        for track in midi_file.tracks:
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                if msg.type == "set_tempo":
                    tempo_map.append((abs_tick, msg.tempo))

        # 按 tick 排序，确保正确顺序
        tempo_map.sort(key=lambda x: x[0])

        # 如果没有 tempo 事件，使用默认 120 BPM
        if not tempo_map:
            tempo_map = [(0, 500000)]
        elif tempo_map[0][0] > 0:
            tempo_map.insert(0, (0, 500000))

        def tick_to_second(tick: int) -> float:
            """使用 tempo map 将 tick 转换为秒"""
            time_sec = 0.0
            prev_tick = 0
            prev_tempo = tempo_map[0][1]

            for map_tick, map_tempo in tempo_map:
                if map_tick >= tick:
                    break
                # 累加前一段的时间
                time_sec += mido.tick2second(map_tick - prev_tick, ticks_per_beat, prev_tempo)
                prev_tick = map_tick
                prev_tempo = map_tempo

            # 加上最后一段
            time_sec += mido.tick2second(tick - prev_tick, ticks_per_beat, prev_tempo)
            return time_sec

        # 2. 解析每个轨道的音符
        for track_idx, track in enumerate(midi_file.tracks):
            abs_tick = 0
            # 使用 (note, channel) -> list of (start_tick, velocity) 支持重叠音符
            active_notes = {}

            for msg in track:
                abs_tick += msg.time

                if not hasattr(msg, 'note'):
                    continue

                channel = getattr(msg, 'channel', 0)
                key = (msg.note, channel)

                # 音符开始
                if msg.type == "note_on" and msg.velocity > 0:
                    if key not in active_notes:
                        active_notes[key] = []
                    active_notes[key].append((abs_tick, msg.velocity))

                # 音符结束
                elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                    if key in active_notes and active_notes[key]:
                        # 取最早的 note_on (FIFO)
                        start_tick, velocity = active_notes[key].pop(0)
                        start_sec = tick_to_second(start_tick)
                        end_sec = tick_to_second(abs_tick)
                        duration = end_sec - start_sec
                        if duration > 0:
                            notes.append({
                                "note": msg.note,
                                "start": start_sec,
                                "duration": duration,
                                "velocity": velocity,
                                "track": track_idx,
                                "channel": channel
                            })

        return notes

    def _draw_grid(self):
        """绘制网格背景"""
        note_min, note_max = self.NOTE_RANGE
        scene_width = self.total_duration * self.pixels_per_second + 100

        # 水平线 (每个音高) - 使用 note_max 作为基准
        for note in range(note_min, note_max + 1):
            y = (note_max - note) * self.pixels_per_note
            # 黑键用深色
            is_black = note % 12 in [1, 3, 6, 8, 10]
            color = self.GRID_COLOR_DARK if is_black else self.GRID_COLOR_LIGHT
            pen = QPen(color, 0.5)
            self.scene.addLine(0, y, scene_width, y, pen)

    def _create_playhead(self):
        """创建播放头"""
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        pen = QPen(self.PLAYHEAD_COLOR, 2)
        self.playhead = self.scene.addLine(0, 0, 0, scene_height, pen)
        self.playhead.setZValue(100)  # 在最上层

    def set_playhead_position(self, time_sec: float):
        """更新播放头位置"""
        self._playhead_time = time_sec
        if self.playhead:
            x = time_sec * self.pixels_per_second
            self.playhead.setLine(x, 0, x, self.playhead.line().y2())

    def set_zoom(self, h_zoom: float, v_zoom: float):
        """设置缩放比例"""
        self.pixels_per_second = h_zoom
        self.pixels_per_note = v_zoom
        self._refresh_notes()

    def _refresh_notes(self):
        """刷新所有音符位置"""
        note_max = self.NOTE_RANGE[1]
        for item in self.notes:
            item.update_geometry(self.pixels_per_second, self.pixels_per_note, note_max)

        # 更新场景大小
        scene_width = self.total_duration * self.pixels_per_second + 100
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        self.scene.setSceneRect(0, 0, scene_width, scene_height)

    def wheelEvent(self, event: QWheelEvent):
        """Ctrl+滚轮缩放"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9

            # 水平缩放
            self.pixels_per_second = max(20, min(500, self.pixels_per_second * factor))
            self._refresh_notes()
            # 通知外部同步缩放
            self.sig_zoom_changed.emit(self.pixels_per_second)
        else:
            super().wheelEvent(event)

    def get_notes_data(self) -> List[dict]:
        """导出当前音符数据"""
        return [
            {
                "note": item.note,
                "start": item.start_time,
                "duration": item.duration,
                "velocity": item.velocity,
                "track": item.track
            }
            for item in self.notes
        ]
