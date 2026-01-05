"""
PianoRollWidget - 钢琴卷帘主视图

Phase 2: 支持选择、拖拽移动、删除、复制粘贴
"""
from typing import List, Optional, Tuple
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem, QGraphicsRectItem, QMessageBox
from PyQt6.QtGui import QPen, QColor, QBrush, QWheelEvent, QKeyEvent, QMouseEvent, QResizeEvent, QUndoStack
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
import mido

from .note_item import NoteItem
from .undo_commands import (
    AddNoteCommand, DeleteNotesCommand, MoveNotesCommand,
    TransposeCommand, QuantizeCommand, AutoTransposeCommand,
    HumanizeCommand, ApplyJitterCommand, AdjustBarsDurationCommand
)


class PianoRollWidget(QGraphicsView):
    """钢琴卷帘主视图 - 显示 MIDI 音符"""

    sig_note_selected = pyqtSignal(list)       # 选中的音符列表
    sig_playback_position = pyqtSignal(float)  # 播放位置 (秒)
    sig_zoom_changed = pyqtSignal(float)       # 水平缩放变化 (pixels_per_second)
    sig_notes_changed = pyqtSignal()           # 音符数据变化 (编辑后)
    sig_row_height_changed = pyqtSignal(float) # 行高变化 (pixels_per_note)
    sig_bar_duration_changed = pyqtSignal(int, float)  # 小节时长变化 (bar_num, new_duration_sec)

    # 常量
    NOTE_RANGE = (21, 108)  # A0 to C8 (标准 88 键)
    # 网格颜色 - 按八度循环的“绿/黑/灰”规则
    GRID_COLOR_GRAY = QColor(70, 70, 70)       # 灰色行 - 更明显
    GRID_COLOR_BLACK = QColor(32, 32, 32)      # 黑色行 - 更暗
    GRID_COLOR_C = QColor(80, 140, 80)         # C 音行 - 绿色（八度起点）
    GRID_LINE_NORMAL = QColor(50, 50, 50)      # 普通分隔线
    GRID_LINE_C = QColor(140, 220, 140)        # C 音分隔线 - 鲜亮绿加粗（B-C边界）
    GRID_LINE_EF = QColor(220, 120, 120)       # E-F 边界分隔线 - 鲜亮红加粗
    GRID_LINE_C_SECONDARY = QColor(90, 150, 90)    # C 音双线副线
    GRID_LINE_EF_SECONDARY = QColor(150, 80, 80)   # E-F 双线副线
    GRID_BAR_LINE = QColor(255, 255, 255, 120)     # 小节竖线（半透明白）
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

        # 网格图元列表 (用于重绘时清理)
        self._grid_items: List = []

        # 播放头
        self.playhead: Optional[QGraphicsLineItem] = None
        self._playhead_time = 0.0

        # MIDI 数据
        self.midi_file: Optional[mido.MidiFile] = None
        self.total_duration = 0.0
        self._bar_duration_sec = 0.0
        # 可变小节边界时间: [(bar_number, start_time_sec), ...]
        self._bar_times: List[Tuple[int, float]] = []

        # 剪贴板 (复制粘贴用)
        self._clipboard: List[dict] = []

        # 撤销/重做栈
        self.undo_stack = QUndoStack(self)

        # 拖拽前的位置快照 (用于 Undo)
        self._drag_snapshot: List[dict] = []

        # 拖拽创建音符相关
        self._is_creating_note: bool = False
        self._create_start_pos: Optional[QPointF] = None
        self._create_start_note: int = 0
        self._create_preview_item: Optional[QGraphicsRectItem] = None
        self._min_note_duration: float = 0.0625  # 最小时值 1/16 拍 @120BPM

        # 量化分辨率 (秒)
        self._quantize_grid_size: float = 0.25  # 默认 1/4 拍 @120BPM

        # Bar selection state (从 timeline 同步)
        self._selected_bars: List[int] = []

        # Drag boundary state (黄色竖线)
        self._drag_boundary_start: float = 0.0  # 秒
        self._drag_boundary_end: float = 0.0    # 秒
        self._drag_boundary_active: bool = False

        # Bar selection overlay items
        self._bar_overlay_items: List = []
        self._drag_line_items: List = []

        # 视图设置
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        # 默认使用橡皮筋框选模式
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # 设置工具提示 (显示快捷键帮助)
        self.setToolTip(
            "Piano Roll\n"
            "• Click+Drag: Select notes\n"
            "• Alt+Click/Drag: Create note\n"
            "• T: Auto transpose (selection)\n"
            "• Space (hold): Pan mode\n"
            "• See Help > Keyboard Shortcuts"
        )
        # 关闭抗锯齿以提高性能
        from PyQt6.QtGui import QPainter
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        # 允许接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def load_midi(self, midi_file: mido.MidiFile):
        """加载 MIDI 文件并创建音符图形项"""
        self.midi_file = midi_file
        self.scene.clear()
        self.notes.clear()
        self._grid_items.clear()  # scene.clear() 已删除图元，清空列表

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
                track=nd.get("track", 0),
                channel=nd.get("channel", 0)
            )
            item.update_geometry(self.pixels_per_second, self.pixels_per_note, note_max)
            self.scene.addItem(item)
            self.notes.append(item)

        # 绘制网格
        self._draw_grid()

        # 创建播放头
        self._create_playhead()

        # 设置场景大小
        scene_width = self._calc_scene_width()
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        self._clamp_scrollbar()

    def _parse_midi(self, midi_file: mido.MidiFile) -> List[dict]:
        """解析 MIDI 文件，提取音符信息

        使用 tempo map 正确处理速度变化，支持同音高重叠音符
        """
        notes = []
        ticks_per_beat = midi_file.ticks_per_beat

        # 1. 首先收集所有轨道的 tempo 事件构建 tempo map
        tempo_map = []  # [(abs_tick, tempo), ...]
        time_sig_map = []  # [(abs_tick, numerator, denominator), ...]
        for track in midi_file.tracks:
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                if msg.type == "set_tempo":
                    tempo_map.append((abs_tick, msg.tempo))
                elif msg.type == "time_signature":
                    time_sig_map.append((abs_tick, msg.numerator, msg.denominator))

        # 按 tick 排序，确保正确顺序
        tempo_map.sort(key=lambda x: x[0])

        # 如果没有 tempo 事件，使用默认 120 BPM
        if not tempo_map:
            tempo_map = [(0, 500000)]
        elif tempo_map[0][0] > 0:
            tempo_map.insert(0, (0, 500000))

        # 如果没有 time signature 事件，使用默认 4/4 拍
        time_sig_map.sort(key=lambda x: x[0])
        if not time_sig_map:
            time_sig_map = [(0, 4, 4)]
        elif time_sig_map[0][0] > 0:
            time_sig_map.insert(0, (0, 4, 4))

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

        def second_to_tick(time_sec: float) -> int:
            """使用 tempo map 将秒转换为 tick"""
            if time_sec <= 0:
                return 0

            current_tick = 0
            current_sec = 0.0
            prev_tempo = tempo_map[0][1]

            for map_tick, map_tempo in tempo_map:
                tick_sec = tick_to_second(map_tick)
                if tick_sec >= time_sec:
                    break
                current_tick = map_tick
                current_sec = tick_sec
                prev_tempo = map_tempo

            remaining_sec = time_sec - current_sec
            if remaining_sec > 0:
                additional_ticks = int(mido.second2tick(remaining_sec, ticks_per_beat, prev_tempo))
                current_tick += additional_ticks

            return current_tick

        def ticks_per_bar_at(tick: int) -> int:
            """获取指定 tick 位置的每小节 tick 数"""
            numerator = 4
            denominator = 4
            for sig_tick, num, denom in time_sig_map:
                if sig_tick > tick:
                    break
                numerator = num
                denominator = denom
            if denominator <= 0:
                return 0
            beat_ticks = ticks_per_beat * 4 // denominator
            return beat_ticks * numerator

        def append_note(note: int, start_tick: int, end_tick: int, velocity: int,
                        track_idx: int, channel: int):
            """根据 tick 创建音符记录"""
            if end_tick <= start_tick:
                return
            start_sec = tick_to_second(start_tick)
            end_sec = tick_to_second(end_tick)
            duration = end_sec - start_sec
            if duration <= 0:
                return
            notes.append({
                "note": note,
                "start": start_sec,
                "duration": duration,
                "velocity": velocity,
                "track": track_idx,
                "channel": channel
            })

        # 2. 解析每个轨道的音符
        for track_idx, track in enumerate(midi_file.tracks):
            abs_tick = 0
            # 使用 (note, channel) -> list of (start_tick, velocity) 支持重叠音符
            active_notes = {}
            # sustain 延迟释放: (note, channel) -> list of (start_tick, velocity)
            sustained_notes = {}
            sustain_on = {}

            for msg in track:
                abs_tick += msg.time

                # 处理延音踏板 (CC64)
                if msg.type == "control_change" and msg.control == 64:
                    channel = getattr(msg, 'channel', 0)
                    is_on = msg.value >= 64
                    prev_on = sustain_on.get(channel, False)
                    sustain_on[channel] = is_on

                    # 踏板抬起：统一结束延音的音符
                    if prev_on and not is_on:
                        for key in list(sustained_notes.keys()):
                            if key[1] != channel:
                                continue
                            for start_tick, velocity in sustained_notes[key]:
                                append_note(key[0], start_tick, abs_tick, velocity, track_idx, channel)
                            del sustained_notes[key]
                    continue

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
                        if sustain_on.get(channel, False):
                            sustained_notes.setdefault(key, []).append((start_tick, velocity))
                        else:
                            append_note(msg.note, start_tick, abs_tick, velocity, track_idx, channel)

            # 轨道结束：为未关闭的音符补 note_off
            track_end_tick = abs_tick
            gap_sec = 0.1
            max_bars = 4

            # 合并 active 与 sustained
            remaining_notes = {}
            for key, items in active_notes.items():
                remaining_notes.setdefault(key, []).extend(items)
            for key, items in sustained_notes.items():
                remaining_notes.setdefault(key, []).extend(items)

            for key, items in remaining_notes.items():
                # 按 start_tick 排序，便于找下一个同音
                items.sort(key=lambda x: x[0])
                for idx, (start_tick, velocity) in enumerate(items):
                    next_start_tick = items[idx + 1][0] if idx + 1 < len(items) else None
                    end_tick = track_end_tick

                    if next_start_tick is not None:
                        next_start_sec = tick_to_second(next_start_tick)
                        end_tick = min(end_tick, second_to_tick(max(0.0, next_start_sec - gap_sec)))

                    # 限制最长不超过 4 小节
                    bar_ticks = ticks_per_bar_at(start_tick)
                    if bar_ticks > 0:
                        end_tick = min(end_tick, start_tick + bar_ticks * max_bars)

                    if end_tick <= start_tick:
                        end_tick = start_tick + 1

                    append_note(key[0], start_tick, end_tick, velocity, track_idx, key[1])

        return notes

    def _clear_grid(self):
        """清理网格图元"""
        for item in self._grid_items:
            self.scene.removeItem(item)
        self._grid_items.clear()

    def _calc_scene_width(self) -> float:
        """计算场景宽度 (内容宽度与视口宽度取大)"""
        content_width = self.total_duration * self.pixels_per_second + 100
        viewport_width = self.viewport().width()
        return max(content_width, viewport_width)

    def _clamp_scrollbar(self):
        """确保滚动条值不超出最大范围"""
        hbar = self.horizontalScrollBar()
        hbar.setValue(min(hbar.value(), hbar.maximum()))

    def resizeEvent(self, event: QResizeEvent):
        """窗口大小变化时更新网格/场景"""
        super().resizeEvent(event)
        # 如果已有音符数据，更新网格以覆盖新视口
        if self.notes or self.total_duration > 0:
            self._redraw_all()

    def set_bar_duration(self, seconds_per_bar: float):
        """设置每小节时长（用于绘制竖线）"""
        seconds_per_bar = max(0.0, float(seconds_per_bar))
        if abs(self._bar_duration_sec - seconds_per_bar) < 1e-6:
            return
        self._bar_duration_sec = seconds_per_bar
        if self.notes or self.total_duration > 0:
            self._redraw_all()

    def _draw_grid(self):
        """绘制网格背景 - 增强对比度版

        E-F 边界（半音）和 B-C 边界（半音）使用更明显的颜色和线条：
        - C 音行：绿色调背景 + 绿色加粗分隔线（B-C 边界上方）
        - B 音行：略带绿背景（B-C 边界下方）
        - F 音行：红色调背景 + 红色加粗分隔线（E-F 边界上方）
        - E 音行：略带红背景（E-F 边界下方）
        - 其他白键：标准灰色背景
        - 黑键行：更暗背景
        """
        from PyQt6.QtWidgets import QGraphicsRectItem
        from PyQt6.QtGui import QBrush

        note_min, note_max = self.NOTE_RANGE
        scene_width = self._calc_scene_width()
        h = self.pixels_per_note

        for note in range(note_min, note_max + 1):
            y = (note_max - note) * self.pixels_per_note
            note_in_octave = note % 12
            # 每个八度循环颜色:
            # C(0)=绿, C#(1)=黑, D(2)=灰, D#(3)=黑, E(4)=灰, F(5)=黑,
            # F#(6)=灰, G(7)=黑, G#(8)=灰, A(9)=黑, A#(10)=灰, B(11)=黑
            is_c = (note_in_octave == 0)   # C 音 (B-C 边界上)
            is_f = (note_in_octave == 5)   # F 音 (E-F 边界上)
            is_gray = note_in_octave in [2, 4, 6, 8, 10]

            # 1. 绘制行背景色
            if is_c:
                bg_color = self.GRID_COLOR_C
            elif is_gray:
                bg_color = self.GRID_COLOR_GRAY
            else:
                bg_color = self.GRID_COLOR_BLACK

            bg_rect = QGraphicsRectItem(0, y, scene_width, h)
            bg_rect.setBrush(QBrush(bg_color))
            bg_rect.setPen(QPen(Qt.PenStyle.NoPen))
            bg_rect.setZValue(-10)  # 在音符下方
            # 禁用鼠标交互，避免干扰音符选择
            bg_rect.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.scene.addItem(bg_rect)
            self._grid_items.append(bg_rect)

            # 2. 绘制分隔线（在行顶部，即上方边界）
            if is_c:
                # C 音顶部：绿色双线 (B-C 边界) - 主线 + 副线
                pen_main = QPen(self.GRID_LINE_C, 3.0)
                line_main = self.scene.addLine(0, y, scene_width, y, pen_main)
                line_main.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._grid_items.append(line_main)
                # 副线（偏移 3px）
                pen_secondary = QPen(self.GRID_LINE_C_SECONDARY, 1.5)
                line_secondary = self.scene.addLine(0, y + 3, scene_width, y + 3, pen_secondary)
                line_secondary.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._grid_items.append(line_secondary)
            elif is_f:
                # F 音顶部：红色双线 (E-F 边界) - 主线 + 副线
                pen_main = QPen(self.GRID_LINE_EF, 3.0)
                line_main = self.scene.addLine(0, y, scene_width, y, pen_main)
                line_main.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._grid_items.append(line_main)
                # 副线（偏移 3px）
                pen_secondary = QPen(self.GRID_LINE_EF_SECONDARY, 1.5)
                line_secondary = self.scene.addLine(0, y + 3, scene_width, y + 3, pen_secondary)
                line_secondary.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._grid_items.append(line_secondary)
            else:
                pen = QPen(self.GRID_LINE_NORMAL, 0.5)
                line = self.scene.addLine(0, y, scene_width, y, pen)
                line.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._grid_items.append(line)

        # 3. 绘制小节竖线
        scene_height = (note_max - note_min + 1) * self.pixels_per_note
        pen = QPen(self.GRID_BAR_LINE, 1.0)
        if self._bar_times:
            # 使用可变小节边界绘制
            for bar_idx, bar_time in self._bar_times:
                x = bar_time * self.pixels_per_second
                line = self.scene.addLine(x, 0, x, scene_height, pen)
                line.setZValue(-9)
                line.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._grid_items.append(line)
            # 添加最后一条线（总时长位置）
            if self._bar_times:
                x = self.total_duration * self.pixels_per_second
                line = self.scene.addLine(x, 0, x, scene_height, pen)
                line.setZValue(-9)
                line.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._grid_items.append(line)
        elif self._bar_duration_sec > 1e-6:
            # 兜底：固定间隔
            t = 0.0
            max_t = self.total_duration + self._bar_duration_sec
            while t <= max_t:
                x = t * self.pixels_per_second
                line = self.scene.addLine(x, 0, x, scene_height, pen)
                line.setZValue(-9)
                line.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._grid_items.append(line)
                t += self._bar_duration_sec

    def _create_playhead(self):
        """创建播放头"""
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        pen = QPen(self.PLAYHEAD_COLOR, 2)
        self.playhead = self.scene.addLine(0, 0, 0, scene_height, pen)
        self.playhead.setZValue(100)  # 在最上层

    def set_playhead_position(self, time_sec: float, auto_scroll: bool = True):
        """更新播放头位置

        Args:
            time_sec: 播放时间（秒）
            auto_scroll: 是否自动滚动（当 playhead 超出可视区域时）
        """
        self._playhead_time = time_sec
        if self.playhead:
            x = time_sec * self.pixels_per_second
            self.playhead.setLine(x, 0, x, self.playhead.line().y2())

            # 自动滚动：当 playhead 超出视口右侧 80% 时，滚动到 30% 位置
            if auto_scroll:
                viewport_width = self.viewport().width()
                scroll_offset = self.horizontalScrollBar().value()
                playhead_viewport_x = x - scroll_offset

                if playhead_viewport_x > viewport_width * 0.8:
                    # 滚动使 playhead 位于视口 30% 位置
                    new_scroll = int(x - viewport_width * 0.3)
                    new_scroll = max(0, new_scroll)
                    self.horizontalScrollBar().setValue(new_scroll)

    def set_zoom(self, h_zoom: float, v_zoom: float):
        """设置缩放比例"""
        self.pixels_per_second = h_zoom
        self.pixels_per_note = v_zoom
        self._redraw_all()  # 重绘网格+音符+播放头

    def _refresh_notes(self):
        """刷新所有音符位置"""
        note_max = self.NOTE_RANGE[1]
        for item in self.notes:
            # 重置位置偏移 (拖拽会改变 pos)
            item.setPos(0, 0)
            item.update_geometry(self.pixels_per_second, self.pixels_per_note, note_max)

        # 更新场景大小
        scene_width = self._calc_scene_width()
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        self._clamp_scrollbar()

    def _adjust_row_height(self, delta: float):
        """调整行高 (pixels_per_note)

        Args:
            delta: 变化量 (正=增加, 负=减少)
        """
        # 限制范围: 6-30 像素
        ROW_HEIGHT_MIN = 6.0
        ROW_HEIGHT_MAX = 30.0

        new_height = max(ROW_HEIGHT_MIN, min(ROW_HEIGHT_MAX, self.pixels_per_note + delta))
        if new_height == self.pixels_per_note:
            return

        self.pixels_per_note = new_height

        # 重绘网格和音符
        self._redraw_all()

        # 通知外部同步 (键盘高度)
        self.sig_row_height_changed.emit(new_height)

    def _redraw_all(self):
        """完全重绘场景 (网格 + 音符 + 播放头)

        注意: 不使用 scene.clear()，而是分别清理网格和播放头，
        以保留 self.notes 中的 NoteItem 对象不被销毁。
        """
        # 保存播放头位置
        playhead_time = self._playhead_time

        # 清理网格图元 (不影响音符)
        self._clear_grid()

        # 清理旧播放头
        if self.playhead:
            self.scene.removeItem(self.playhead)
            self.playhead = None

        # 重绘网格
        self._draw_grid()

        # 更新音符位置 (不重新添加到场景，只更新几何属性)
        note_max = self.NOTE_RANGE[1]
        for item in self.notes:
            item.setPos(0, 0)
            item.update_geometry(self.pixels_per_second, self.pixels_per_note, note_max)

        # 重建播放头
        self._create_playhead()
        self.set_playhead_position(playhead_time)

        # 更新场景大小
        scene_width = self._calc_scene_width()
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        self._clamp_scrollbar()

    def wheelEvent(self, event: QWheelEvent):
        """Ctrl+滚轮缩放"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9

            # 水平缩放
            self.pixels_per_second = max(20, min(500, self.pixels_per_second * factor))
            self._redraw_all()  # 重绘网格+音符+播放头
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

    # ============== Phase 2: 编辑功能 ==============

    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件处理"""
        key = event.key()
        modifiers = event.modifiers()

        # Ctrl+A: 全选
        if key == Qt.Key.Key_A and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.select_all()
            return

        # Delete / Backspace: 删除选中
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            return

        # Ctrl+C: 复制
        if key == Qt.Key.Key_C and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.copy_selected()
            return

        # Ctrl+V: 粘贴
        if key == Qt.Key.Key_V and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.paste_at_playhead()
            return

        # Escape: 取消选择
        if key == Qt.Key.Key_Escape:
            self.scene.clearSelection()
            return

        # Space: 临时切换到拖拽平移模式
        if key == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            return

        # Ctrl+Up/Down 或 [ / ]: 调整行高
        if key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._adjust_row_height(2)  # 增加 2px
            return
        if key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._adjust_row_height(-2)  # 减少 2px
            return
        if key == Qt.Key.Key_BracketRight:  # ]
            self._adjust_row_height(2)
            return
        if key == Qt.Key.Key_BracketLeft:  # [
            self._adjust_row_height(-2)
            return

        # 移调快捷键 (需要有选中的音符)
        # Shift+Up: 升半音, Shift+Down: 降半音
        # Shift+Ctrl+Up: 升八度, Shift+Ctrl+Down: 降八度
        if key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.transpose_selected(1)
            return
        if key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.transpose_selected(-1)
            return
        if key == Qt.Key.Key_Up and modifiers == (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
            self.transpose_selected(12)
            return
        if key == Qt.Key.Key_Down and modifiers == (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
            self.transpose_selected(-12)
            return

        # Q: 量化到当前网格大小
        if key == Qt.Key.Key_Q and modifiers == Qt.KeyboardModifier.NoModifier:
            self.quantize_selected(self._quantize_grid_size)
            return

        # Ctrl+Z: 撤销
        if key == Qt.Key.Key_Z and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.undo_stack.undo()
            return

        # Ctrl+Y 或 Ctrl+Shift+Z: 重做
        if key == Qt.Key.Key_Y and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.undo_stack.redo()
            return
        if key == Qt.Key.Key_Z and modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            self.undo_stack.redo()
            return

        # H: 人性化抖动 (自然: 20ms/10), Shift+H: 轻微 (10ms/5), Ctrl+H: 强 (40ms/20)
        if key == Qt.Key.Key_H:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.humanize_selected(20.0, 10.0, 0.05)  # 自然
                return
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.humanize_selected(10.0, 5.0, 0.02)   # 轻微
                return
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.humanize_selected(40.0, 20.0, 0.10)  # 强
                return

        # T/Shift+T: 自动移调 - 已移至 Edit 菜单 (editor_window._setup_menus)
        # 菜单快捷键在窗口级别处理，无需在此重复

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        """键盘释放事件"""
        # Space 释放: 恢复框选模式
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            return

        super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件 - 中键平移，Alt+左键创建音符，左键框选/拖拽"""
        # 右键取消正在进行的创建
        if event.button() == Qt.MouseButton.RightButton and self._is_creating_note:
            self._cancel_note_create()
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            # 模拟左键按下以启动拖拽
            fake_event = QMouseEvent(
                event.type(),
                event.position(),
                event.globalPosition(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                event.modifiers()
            )
            super().mousePressEvent(fake_event)
            return

        # Alt+左键：空白处开始拖拽创建音符
        # 不按 Alt 时左键保留 RubberBand 框选功能
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            if modifiers & Qt.KeyboardModifier.AltModifier:
                scene_pos = self.mapToScene(event.pos())
                # 检查点击位置是否有音符
                item_at_pos = self._get_item_at_pos(scene_pos)
                if item_at_pos is None:
                    # 空白处 + Alt：开始创建音符
                    self._start_note_create(scene_pos)
                    return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放后同步拖拽结果到数据模型"""
        # 中键释放: 发送假左键释放以正确结束 ScrollHandDrag，然后恢复框选模式
        if event.button() == Qt.MouseButton.MiddleButton:
            # 模拟左键释放以正确结束拖拽状态（与 mousePressEvent 中的假左键按下对应）
            fake_event = QMouseEvent(
                event.type(),
                event.position(),
                event.globalPosition(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.NoButton,  # 释放后无按钮处于按下状态
                event.modifiers()
            )
            super().mouseReleaseEvent(fake_event)
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            return

        # 左键释放: 完成拖拽创建音符
        if event.button() == Qt.MouseButton.LeftButton and self._is_creating_note:
            scene_pos = self.mapToScene(event.pos())
            self._finish_note_create(scene_pos)
            return

        super().mouseReleaseEvent(event)

        # 检查是否有选中的音符被移动了
        selected = [item for item in self.notes if item.isSelected()]
        if selected:
            self._sync_notes_from_graphics()

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件 - 更新拖拽创建预览"""
        # 如果正在创建音符，更新预览矩形
        if self._is_creating_note and self._create_preview_item and self._create_start_pos:
            scene_pos = self.mapToScene(event.pos())

            # 计算预览矩形的位置和大小
            start_x = self._create_start_pos.x()
            current_x = scene_pos.x()

            # 确保从左到右
            if current_x < start_x:
                left_x = current_x
                width = start_x - current_x
            else:
                left_x = start_x
                width = current_x - start_x

            # 强制最小宽度
            min_width = self._min_note_duration * self.pixels_per_second
            width = max(min_width, width)

            # 更新预览矩形
            rect = self._create_preview_item.rect()
            self._create_preview_item.setRect(left_x, rect.y(), width, rect.height())

        super().mouseMoveEvent(event)

    def _sync_notes_from_graphics(self):
        """从图形位置同步回数据模型"""
        note_max = self.NOTE_RANGE[1]
        changed = False

        for item in self.notes:
            # 从当前图形位置计算时间和音高
            rect = item.rect()
            pos = item.pos()

            # 计算新的起始时间
            new_x = pos.x() + rect.x()
            new_start_time = max(0.0, new_x / self.pixels_per_second)

            # 计算新的音高
            new_y = pos.y() + rect.y()
            new_note = note_max - int(new_y / self.pixels_per_note)
            new_note = max(self.NOTE_RANGE[0], min(self.NOTE_RANGE[1], new_note))

            # 检查是否变化
            if abs(new_start_time - item.start_time) > 0.001 or new_note != item.note:
                item.start_time = new_start_time
                item.note = new_note
                changed = True

        if changed:
            # 重置位置并重绘
            self._refresh_notes()
            # 更新总时长
            if self.notes:
                self.total_duration = max(n.start_time + n.duration for n in self.notes)
            # 发出变化信号
            self.sig_notes_changed.emit()

    def select_all(self):
        """全选所有音符"""
        for item in self.notes:
            item.setSelected(True)
        self.sig_note_selected.emit(self.notes)

    def delete_selected(self):
        """删除选中的音符 (支持撤销)"""
        selected = [item for item in self.notes if item.isSelected()]
        if not selected:
            return

        # 收集要删除的音符数据
        notes_data = [
            {
                "note": item.note,
                "start": item.start_time,
                "duration": item.duration,
                "velocity": item.velocity,
                "track": item.track,
                "channel": getattr(item, 'channel', 0)
            }
            for item in selected
        ]

        # 使用 Undo 命令
        cmd = DeleteNotesCommand(self, notes_data)
        self.undo_stack.push(cmd)

        self.sig_notes_changed.emit()

    def copy_selected(self):
        """复制选中的音符到剪贴板"""
        selected = [item for item in self.notes if item.isSelected()]
        if not selected:
            return

        # 找到选中音符的最小起始时间作为基准
        min_start = min(item.start_time for item in selected)

        self._clipboard = [
            {
                "note": item.note,
                "start": item.start_time - min_start,  # 相对时间
                "duration": item.duration,
                "velocity": item.velocity,
                "track": item.track,
                "channel": getattr(item, 'channel', 0)  # 保留 channel
            }
            for item in selected
        ]

    def paste_at_playhead(self):
        """在播放头位置粘贴剪贴板内容"""
        if not self._clipboard:
            return

        # 取消当前选择
        self.scene.clearSelection()

        note_max = self.NOTE_RANGE[1]
        paste_time = self._playhead_time

        # 创建新音符
        for nd in self._clipboard:
            item = NoteItem(
                note=nd["note"],
                start_time=paste_time + nd["start"],
                duration=nd["duration"],
                velocity=nd["velocity"],
                track=nd["track"],
                channel=nd.get("channel", 0)  # 保留 channel
            )
            item.update_geometry(self.pixels_per_second, self.pixels_per_note, note_max)
            self.scene.addItem(item)
            self.notes.append(item)
            # 选中新粘贴的音符
            item.setSelected(True)

        # 更新总时长
        self.total_duration = max(n.start_time + n.duration for n in self.notes)

        # 扩展场景大小
        scene_width = self._calc_scene_width()
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        self._clamp_scrollbar()

        self.sig_notes_changed.emit()

    def get_selected_notes(self) -> List[NoteItem]:
        """获取当前选中的音符"""
        return [item for item in self.notes if item.isSelected()]

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """双击添加音符 (支持撤销)"""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return

        # 转换到场景坐标
        scene_pos = self.mapToScene(event.pos())
        note_max = self.NOTE_RANGE[1]
        note_min = self.NOTE_RANGE[0]

        # 计算时间和音高
        time_sec = max(0.0, scene_pos.x() / self.pixels_per_second)
        note_pitch = note_max - int(scene_pos.y() / self.pixels_per_note)

        # 限制音高在有效范围内
        note_pitch = max(note_min, min(note_max, note_pitch))

        # 构造音符数据
        note_data = {
            "note": note_pitch,
            "start": time_sec,
            "duration": 0.25,
            "velocity": 100,
            "track": 0,
            "channel": 0
        }

        # 使用 Undo 命令添加音符
        cmd = AddNoteCommand(self, note_data)
        self.undo_stack.push(cmd)

        # 选中新创建的音符 (最后一个)
        self.scene.clearSelection()
        if self.notes:
            self.notes[-1].setSelected(True)

        # 扩展场景大小
        scene_width = self._calc_scene_width()
        scene_height = (note_max - note_min + 1) * self.pixels_per_note
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        self._clamp_scrollbar()

        self.sig_notes_changed.emit()

    # ============== Phase 3: 高级编辑功能 ==============

    def transpose_selected(self, semitones: int):
        """批量移调选中的音符 (支持撤销)

        Args:
            semitones: 移调半音数 (正=升调, 负=降调)
        """
        selected = [item for item in self.notes if item.isSelected()]
        if not selected:
            return

        # 收集选中音符数据
        notes_data = [
            {
                "note": item.note,
                "start": item.start_time,
                "duration": item.duration,
                "velocity": item.velocity,
                "track": item.track,
                "channel": getattr(item, 'channel', 0)
            }
            for item in selected
        ]

        # 使用 Undo 命令
        cmd = TransposeCommand(self, notes_data, semitones)
        self.undo_stack.push(cmd)

        self.sig_notes_changed.emit()

    def quantize_selected(self, grid_size: float = 0.25):
        """批量量化选中的音符起始时间 (支持撤销)

        Args:
            grid_size: 网格大小 (秒)，默认 0.25s (@120BPM 约为四分音符)
        """
        selected = [item for item in self.notes if item.isSelected()]
        if not selected or grid_size <= 0:
            return

        # 收集旧时间和新时间
        old_times = []
        new_times = []

        for item in selected:
            old_data = {
                "note": item.note,
                "start": item.start_time,
                "duration": item.duration
            }
            new_start = round(item.start_time / grid_size) * grid_size
            new_data = {
                "note": item.note,
                "start": new_start,
                "duration": item.duration
            }
            old_times.append(old_data)
            new_times.append(new_data)

        # 检查是否有变化
        has_change = any(
            abs(old["start"] - new["start"]) > 0.001
            for old, new in zip(old_times, new_times)
        )

        if has_change:
            cmd = QuantizeCommand(self, old_times, new_times)
            self.undo_stack.push(cmd)
            self.sig_notes_changed.emit()

    def auto_transpose_octave(self, target_low: int, target_high: int):
        """自动移调选中的音符到目标音域 (八度策略)

        只允许 ±12 或 ±24 半音移调。超出目标音域的音符会被标记为 out_of_range。

        Args:
            target_low: 目标音域最低音 (MIDI note number)
            target_high: 目标音域最高音 (MIDI note number)
        """
        selected = [item for item in self.notes if item.isSelected()]
        if not selected:
            return

        # 计算选中音符的音高范围
        min_note = min(item.note for item in selected)
        max_note = max(item.note for item in selected)

        # 计算需要的移调量 (只允许 ±12 或 ±24)
        # 策略: 尽量使音符落入目标音域，优先使用较小的移调量
        best_semitones = 0
        best_score = -1

        for semitones in [0, 12, -12, 24, -24]:
            new_min = min_note + semitones
            new_max = max_note + semitones

            # 计算有多少音符会落在目标音域内
            in_range_count = 0
            for item in selected:
                new_note = item.note + semitones
                if target_low <= new_note <= target_high:
                    in_range_count += 1

            # 选择落入目标范围最多的移调方案
            # 如果相同，选择移调量绝对值较小的
            if in_range_count > best_score or (in_range_count == best_score and abs(semitones) < abs(best_semitones)):
                best_score = in_range_count
                best_semitones = semitones

        # 如果最佳方案也是 0 移调且没有音符超出范围，可能不需要操作
        # 但仍然执行以更新 out_of_range 标记

        # 收集选中音符数据
        notes_data = [
            {
                "note": item.note,
                "start": item.start_time,
                "duration": item.duration,
                "velocity": item.velocity,
                "track": item.track,
                "channel": getattr(item, 'channel', 0)
            }
            for item in selected
        ]

        # 使用 AutoTransposeCommand
        cmd = AutoTransposeCommand(self, notes_data, best_semitones, target_low, target_high)
        self.undo_stack.push(cmd)

        self.sig_notes_changed.emit()

    def humanize_selected(self, timing_ms: float = 20.0, velocity_var: float = 10.0,
                          duration_pct: float = 0.05):
        """对选中音符应用人性化抖动

        使用高斯分布随机偏移音符的起始时间、力度和时值，
        使演奏听起来更自然。

        Args:
            timing_ms: 起始时间偏移标准差 (毫秒)
            velocity_var: 力度偏移标准差 (0-127 范围内)
            duration_pct: 时值偏移比例标准差 (如 0.05 = ±5%)

        预设:
            轻微: (10ms, 5, 0.02)
            自然: (20ms, 10, 0.05)
            强:   (40ms, 20, 0.10)
        """
        selected = [item for item in self.notes if item.isSelected()]
        if not selected:
            return

        # 收集选中音符数据
        notes_data = [
            {
                "note": item.note,
                "start": item.start_time,
                "duration": item.duration,
                "velocity": item.velocity,
                "track": item.track,
                "channel": getattr(item, 'channel', 0)
            }
            for item in selected
        ]

        # 使用 HumanizeCommand
        cmd = HumanizeCommand(self, notes_data, timing_ms, velocity_var, duration_pct)
        self.undo_stack.push(cmd)

        self.sig_notes_changed.emit()

    # ============== 批量选择方法 ==============

    def select_by_filter(self,
                         time_range: Optional[Tuple[float, float]] = None,
                         pitch_range: Optional[Tuple[int, int]] = None):
        """按时间范围和/或音域范围选择音符

        Args:
            time_range: (start_time, end_time) 时间范围 (秒)，None 表示不限
            pitch_range: (low_note, high_note) 音高范围 (MIDI)，None 表示不限

        时间范围和音域范围是 AND 关系，音符必须同时满足两个条件才会被选中。
        """
        self.scene.clearSelection()

        for item in self.notes:
            # 默认满足条件
            in_time_range = True
            in_pitch_range = True

            # 检查时间范围
            if time_range is not None:
                start, end = time_range
                note_start = item.start_time
                note_end = item.start_time + item.duration
                # 音符与时间范围有重叠
                in_time_range = (note_end > start and note_start < end)

            # 检查音高范围
            if pitch_range is not None:
                low, high = pitch_range
                in_pitch_range = (low <= item.note <= high)

            # 两个条件都满足才选中
            if in_time_range and in_pitch_range:
                item.setSelected(True)

        # 发出选择变化信号
        selected = [item for item in self.notes if item.isSelected()]
        self.sig_note_selected.emit(selected)

    def get_selection_time_range(self) -> Optional[Tuple[float, float]]:
        """获取当前选中音符的时间范围

        Returns:
            (start_time, end_time) 或 None 如果无选中音符
        """
        selected = [item for item in self.notes if item.isSelected()]
        if not selected:
            return None

        start = min(item.start_time for item in selected)
        end = max(item.start_time + item.duration for item in selected)
        return (start, end)

    def adjust_selected_duration(self, delta_sec: float):
        """调整选中音符的时值

        Args:
            delta_sec: 时值增量（秒，可正可负）
        """
        from .undo_commands import AdjustDurationCommand

        selected = [item for item in self.notes if item.isSelected()]
        if not selected:
            return

        notes_data = [{
            "note": item.note,
            "start": item.start_time,
            "duration": item.duration
        } for item in selected]

        cmd = AdjustDurationCommand(self, notes_data, delta_sec)
        self.undo_stack.push(cmd)
        self.sig_notes_changed.emit()

    def select_by_pitch_range(self, low_note: int, high_note: int):
        """按音域范围选择音符（保留现有时间范围过滤）

        Args:
            low_note: 最低音 (MIDI)
            high_note: 最高音 (MIDI)
        """
        # 获取当前选中的时间范围（如果有的话用作过滤条件）
        time_range = self.get_selection_time_range()
        self.select_by_filter(time_range=time_range, pitch_range=(low_note, high_note))

    def set_quantize_grid_size(self, grid_size: float):
        """设置量化网格大小

        Args:
            grid_size: 网格大小 (秒)
        """
        self._quantize_grid_size = grid_size

    def get_quantize_grid_size(self) -> float:
        """获取当前量化网格大小

        Returns:
            网格大小 (秒)
        """
        return self._quantize_grid_size

    # ============== 拖拽创建音符辅助方法 ==============

    def _get_item_at_pos(self, scene_pos: QPointF) -> Optional[NoteItem]:
        """检查场景位置是否有 NoteItem

        Args:
            scene_pos: 场景坐标

        Returns:
            NoteItem 如果存在，否则 None
        """
        items = self.scene.items(scene_pos)
        for item in items:
            if isinstance(item, NoteItem):
                return item
        return None

    def _start_note_create(self, scene_pos: QPointF):
        """开始拖拽创建音符

        Args:
            scene_pos: 鼠标按下时的场景坐标
        """
        note_max = self.NOTE_RANGE[1]
        note_min = self.NOTE_RANGE[0]

        # 计算音高
        note_pitch = note_max - int(scene_pos.y() / self.pixels_per_note)
        note_pitch = max(note_min, min(note_max, note_pitch))

        # 保存状态
        self._is_creating_note = True
        self._create_start_pos = scene_pos
        self._create_start_note = note_pitch

        # 创建预览矩形
        y = (note_max - note_pitch) * self.pixels_per_note
        min_width = self._min_note_duration * self.pixels_per_second
        h = self.pixels_per_note - 1

        preview = QGraphicsRectItem(scene_pos.x(), y, min_width, h)
        preview.setBrush(QBrush(QColor(100, 149, 237, 128)))  # 半透明蓝色
        preview.setPen(QPen(QColor(255, 255, 255), 1))
        preview.setZValue(50)  # 在音符上方，播放头下方
        self.scene.addItem(preview)
        self._create_preview_item = preview

    def _cancel_note_create(self):
        """取消正在进行的拖拽创建"""
        if self._create_preview_item:
            self.scene.removeItem(self._create_preview_item)
            self._create_preview_item = None
        self._is_creating_note = False
        self._create_start_pos = None
        self._create_start_note = 0

    def _finish_note_create(self, scene_pos: QPointF):
        """完成拖拽创建，添加音符

        Args:
            scene_pos: 鼠标释放时的场景坐标
        """
        if not self._is_creating_note or not self._create_start_pos:
            return

        # 计算时值
        start_x = self._create_start_pos.x()
        end_x = scene_pos.x()

        # 确保从左到右
        if end_x < start_x:
            start_x, end_x = end_x, start_x

        start_time = max(0.0, start_x / self.pixels_per_second)
        duration = (end_x - start_x) / self.pixels_per_second

        # 强制最小时值
        duration = max(self._min_note_duration, duration)

        # 构造音符数据
        note_data = {
            "note": self._create_start_note,
            "start": start_time,
            "duration": duration,
            "velocity": 100,
            "track": 0,
            "channel": 0
        }

        # 清理预览
        self._cancel_note_create()

        # 使用 Undo 命令添加音符
        cmd = AddNoteCommand(self, note_data)
        self.undo_stack.push(cmd)

        # 选中新创建的音符
        self.scene.clearSelection()
        if self.notes:
            self.notes[-1].setSelected(True)

        # 扩展场景大小
        scene_width = self._calc_scene_width()
        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        self._clamp_scrollbar()

        self.sig_notes_changed.emit()

    # ============== Bar Selection & Duration Adjustment ==============

    def set_selected_bars(self, bar_numbers: List[int]):
        """设置选中的小节并绘制覆盖层

        Args:
            bar_numbers: 选中的小节号列表 (1-based, 从 1 开始, 与 timeline 显示一致)
        """
        self._selected_bars = bar_numbers[:]
        self._update_bar_overlay()

    def get_selected_bars(self) -> List[int]:
        """获取当前选中的小节列表"""
        return self._selected_bars[:]

    def clear_selected_bars(self):
        """清除小节选择"""
        self._selected_bars.clear()
        self._clear_bar_overlay()

    def set_bar_times(self, bar_times: List[Tuple[int, float]]):
        """设置可变小节边界时间

        Args:
            bar_times: [(bar_number, start_time_sec), ...] - bar_number 从 1 开始
        """
        self._bar_times = bar_times[:]
        self._update_bar_overlay()  # 重绘覆盖层
        # 触发网格重绘以更新小节竖线
        self._clear_grid()
        self._draw_grid()

    def get_bar_times(self) -> List[Tuple[int, float]]:
        """获取小节边界时间列表"""
        return self._bar_times[:]

    def _get_bar_time_range(self, bar_num: int) -> Tuple[float, float]:
        """获取指定小节的时间范围 (使用可变小节边界)

        Args:
            bar_num: 小节编号 (1-based)

        Returns:
            (start_time_sec, end_time_sec)
        """
        if self._bar_times:
            # 使用可变小节边界
            for i, (bn, bt) in enumerate(self._bar_times):
                if bn == bar_num:
                    start_time = bt
                    # 下一个小节的开始时间作为结束
                    if i + 1 < len(self._bar_times):
                        end_time = self._bar_times[i + 1][1]
                    else:
                        end_time = self.total_duration
                    return start_time, end_time
            return 0.0, self.total_duration
        else:
            # 回退到固定小节时长
            start_time = (bar_num - 1) * self._bar_duration_sec
            end_time = bar_num * self._bar_duration_sec
            return start_time, end_time

    def set_drag_boundary(self, start_sec: float, end_sec: float, active: bool):
        """设置拖拽边界线 (黄色竖线)

        Args:
            start_sec: 起始时间 (秒)
            end_sec: 结束时间 (秒)
            active: 是否激活显示
        """
        self._drag_boundary_start = start_sec
        self._drag_boundary_end = end_sec
        self._drag_boundary_active = active
        self._update_drag_lines()

    def _clear_bar_overlay(self):
        """清除小节选择覆盖层"""
        for item in self._bar_overlay_items:
            self.scene.removeItem(item)
        self._bar_overlay_items.clear()

    def _update_bar_overlay(self):
        """更新小节选择覆盖层

        使用可变小节边界 (_bar_times) 或固定小节时长 (_bar_duration_sec)
        bar_num 从 timeline 传入，是 1-based (小节 1, 2, 3, ...)
        """
        self._clear_bar_overlay()

        if not self._selected_bars:
            return

        # 检查是否有可用的小节时长信息
        if not self._bar_times and self._bar_duration_sec <= 0:
            return

        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        overlay_color = QColor(255, 255, 0, 40)  # 半透明黄色

        for bar_num in sorted(self._selected_bars):
            # 使用可变小节边界获取时间范围
            bar_start, bar_end = self._get_bar_time_range(bar_num)
            x_start = bar_start * self.pixels_per_second
            width = (bar_end - bar_start) * self.pixels_per_second

            rect = QGraphicsRectItem(x_start, 0, width, scene_height)
            rect.setBrush(QBrush(overlay_color))
            rect.setPen(QPen(Qt.PenStyle.NoPen))
            rect.setZValue(-5)  # 在网格之上，音符之下
            rect.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.scene.addItem(rect)
            self._bar_overlay_items.append(rect)

    def _clear_drag_lines(self):
        """清除拖拽边界线"""
        for item in self._drag_line_items:
            self.scene.removeItem(item)
        self._drag_line_items.clear()

    def _update_drag_lines(self):
        """更新拖拽边界线 (黄色竖线)"""
        self._clear_drag_lines()

        if not self._drag_boundary_active:
            return

        scene_height = (self.NOTE_RANGE[1] - self.NOTE_RANGE[0] + 1) * self.pixels_per_note
        pen = QPen(QColor(255, 255, 0), 2)  # 黄色 2px

        # 起始线
        x1 = self._drag_boundary_start * self.pixels_per_second
        line1 = self.scene.addLine(x1, 0, x1, scene_height, pen)
        line1.setZValue(90)  # 在音符之上，播放头之下
        line1.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._drag_line_items.append(line1)

        # 结束线
        x2 = self._drag_boundary_end * self.pixels_per_second
        line2 = self.scene.addLine(x2, 0, x2, scene_height, pen)
        line2.setZValue(90)
        line2.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._drag_line_items.append(line2)

    def adjust_selected_bars_duration(self, delta_ms: int):
        """调整选中小节内音符的时值，并平移后续音符

        时间拉伸/压缩语义：
        - 选中的小节按连续区间分组（如 [1,2] 和 [5,6] 是两个区间）
        - 每个区间内的音符按比例拉伸/压缩
        - 后续区间和音符累计平移
        - delta 按小节数量累计：total_delta = delta_sec * bar_count

        音符归属判定（起点命中策略）：
        - 仅当音符的 start_time 落在选中小节区间内时，才对该音符进行拉伸
        - 跨区间的长音符（起点在区间外，尾部延伸入区间）不会被拉伸，仅随前置区间平移
        - 这确保未选中小节内的音符不会被意外拉伸
        - 注意：起点在选中区间内但尾部跨出的长音符仍会整体拉伸，
          其尾部可能延伸到未选中小节（影响幅度取决于拉伸比例）

        Args:
            delta_ms: 每小节时值增量 (毫秒，正=拉伸，负=压缩)

        注意: bar_num 是 1-based (小节 1, 2, 3, ...)
        """
        if not self._selected_bars:
            return

        # 检查是否有可用的小节时长信息
        if not self._bar_times and self._bar_duration_sec <= 0:
            return

        delta_sec_per_bar = delta_ms / 1000.0

        # 将选中小节分组为连续区间
        # 例如 [1, 2, 5, 6, 7] -> [[1, 2], [5, 6, 7]]
        sorted_bars = sorted(self._selected_bars)
        intervals = []  # [(first_bar, last_bar), ...]
        if sorted_bars:
            interval_start = sorted_bars[0]
            interval_end = sorted_bars[0]
            for bar in sorted_bars[1:]:
                if bar == interval_end + 1:
                    # 连续，扩展当前区间
                    interval_end = bar
                else:
                    # 不连续，保存当前区间，开始新区间
                    intervals.append((interval_start, interval_end))
                    interval_start = bar
                    interval_end = bar
            intervals.append((interval_start, interval_end))

        if not intervals:
            return

        # 按起始时间排序音符（用于处理后续平移）
        notes_by_start = sorted(self.notes, key=lambda n: n.start_time)

        # 计算每个音符的新位置
        # 使用字典存储：note_item -> new_data
        note_updates = {}
        cumulative_shift = 0.0  # 累计平移量

        # 记录修改的小节时长 [(bar_num, duration), ...]
        old_bar_durations = []  # 原始小节时长 (用于 undo)
        new_bar_durations = []  # 新小节时长 (用于 redo)

        for interval_idx, (first_bar, last_bar) in enumerate(intervals):
            # 使用可变小节边界计算区间时间范围
            first_bar_start, _ = self._get_bar_time_range(first_bar)
            _, last_bar_end = self._get_bar_time_range(last_bar)
            interval_start_sec = first_bar_start
            interval_end_sec = last_bar_end

            # 此区间包含的小节数
            bar_count = last_bar - first_bar + 1

            # 此区间的 delta
            total_delta = delta_sec_per_bar * bar_count

            # 原始时长和新时长
            original_duration = interval_end_sec - interval_start_sec
            new_duration = max(0.01, original_duration + total_delta)
            scale = new_duration / original_duration if original_duration > 0 else 1.0

            # 应用累计平移到此区间的起点
            shifted_interval_start = interval_start_sec + cumulative_shift

            # 找出起点落在此区间内的音符（起点命中策略）
            for item in notes_by_start:
                note_start = item.start_time

                # 跳过已处理的音符
                if item in note_updates:
                    continue

                # 起点命中策略：仅当音符的 start_time 落在区间 [interval_start, interval_end) 内
                # 这确保跨区间的长音符（起点在区间外）不会被拉伸，只会随前置区间平移
                if interval_start_sec <= note_start < interval_end_sec:
                    # 起点命中，进行拉伸
                    rel_start = note_start - interval_start_sec
                    rel_end = rel_start + item.duration

                    new_rel_start = rel_start * scale
                    new_rel_end = rel_end * scale

                    note_updates[item] = {
                        "note": item.note,
                        "start": shifted_interval_start + new_rel_start,
                        "duration": max(0.01, new_rel_end - new_rel_start),
                        "velocity": item.velocity,
                        "track": item.track,
                        "channel": getattr(item, 'channel', 0)
                    }

            # 记录每个小节的旧/新时长（用于 undo/redo 同步到 timeline）
            for bar_num in range(first_bar, last_bar + 1):
                old_bar_start, old_bar_end = self._get_bar_time_range(bar_num)
                old_bar_duration = old_bar_end - old_bar_start
                new_bar_duration = max(0.01, old_bar_duration + delta_sec_per_bar)
                old_bar_durations.append((bar_num, old_bar_duration))
                new_bar_durations.append((bar_num, new_bar_duration))

            # 更新累计平移量
            cumulative_shift += (new_duration - original_duration)

        # 处理未被任何区间覆盖的音符（在所有选中区间之后的音符需要平移）
        _, last_interval_end = self._get_bar_time_range(intervals[-1][1])
        for item in notes_by_start:
            if item in note_updates:
                continue

            note_start = item.start_time

            # 判断音符是否在所有选中区间之后
            if note_start >= last_interval_end:
                # 在最后一个区间之后，应用累计平移
                note_updates[item] = {
                    "note": item.note,
                    "start": note_start + cumulative_shift,
                    "duration": item.duration,
                    "velocity": item.velocity,
                    "track": item.track,
                    "channel": getattr(item, 'channel', 0)
                }
            else:
                # 在区间之间或之前，检查是否需要部分平移
                # 计算此音符应该受到的累计平移量
                temp_shift = 0.0
                for first_bar, last_bar in intervals:
                    # 使用可变小节边界
                    int_start, _ = self._get_bar_time_range(first_bar)
                    _, int_end = self._get_bar_time_range(last_bar)
                    bar_count = last_bar - first_bar + 1
                    total_delta = delta_sec_per_bar * bar_count
                    original_dur = int_end - int_start
                    new_dur = max(0.01, original_dur + total_delta)

                    if note_start >= int_end:
                        # 音符在此区间之后，累加此区间的平移
                        temp_shift += (new_dur - original_dur)

                if temp_shift != 0:
                    note_updates[item] = {
                        "note": item.note,
                        "start": note_start + temp_shift,
                        "duration": item.duration,
                        "velocity": item.velocity,
                        "track": item.track,
                        "channel": getattr(item, 'channel', 0)
                    }

        if not note_updates:
            return

        # 构建 old 和 new 数据用于 undo 命令
        old_notes_data = []
        new_notes_data = []
        for item, new_data in note_updates.items():
            old_notes_data.append({
                "note": item.note,
                "start": item.start_time,
                "duration": item.duration,
                "velocity": item.velocity,
                "track": item.track,
                "channel": getattr(item, 'channel', 0)
            })
            new_notes_data.append(new_data)

        # 使用 undo 命令 (包含小节时长以支持完整 undo/redo)
        cmd = AdjustBarsDurationCommand(
            self, old_notes_data, new_notes_data,
            old_bar_durations=old_bar_durations,
            new_bar_durations=new_bar_durations
        )
        self.undo_stack.push(cmd)
        self.sig_notes_changed.emit()
        # 注意: 小节时长信号现在由 AdjustBarsDurationCommand.redo() 发送
