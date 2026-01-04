"""
KeyListWidget - 底部按键进度窗

显示按键序列进度，支持:
- 行=按键（来自 keyboard_layout）
- 列=时间
- 水平条形显示按下→松开
- 与 PianoRollWidget 水平滚动同步
- 播放头同步
"""
from typing import List, Dict, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QFont, QColor, QPen, QBrush, QPainter, QWheelEvent, QResizeEvent
)

from keyboard_layout import (
    KeyboardLayout, LAYOUT_21KEY, LAYOUT_36KEY, KEYBOARD_LAYOUTS
)


# MIDI 音符名称映射
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_to_note_name(midi_note: int) -> str:
    """将 MIDI 音符号转换为音符名 (如 60 -> C4)"""
    octave = (midi_note // 12) - 1
    note = NOTE_NAMES[midi_note % 12]
    return f"{note}{octave}"


class KeyNoteBar(QGraphicsRectItem):
    """单个按键音符条形"""

    # 颜色配置
    COLOR_NORMAL = QColor(100, 180, 100)       # 绿色
    COLOR_CURRENT = QColor(80, 200, 255)       # 亮蓝色
    COLOR_PLAYED = QColor(80, 80, 80)          # 深灰色
    COLOR_BORDER = QColor(255, 255, 255, 80)   # 半透明白边

    def __init__(self, note: int, key: str, start_time: float, duration: float,
                 row_index: int):
        super().__init__()
        self.note = note
        self.key = key
        self.start_time = start_time
        self.duration = duration
        self.row_index = row_index
        self._is_current = False
        self._is_played = False

        self._update_appearance()

    def _update_appearance(self):
        """更新外观"""
        if self._is_current:
            self.setBrush(QBrush(self.COLOR_CURRENT))
            self.setPen(QPen(QColor(255, 255, 255), 2))
        elif self._is_played:
            self.setBrush(QBrush(self.COLOR_PLAYED))
            self.setPen(QPen(QColor(60, 60, 60), 1))
        else:
            self.setBrush(QBrush(self.COLOR_NORMAL))
            self.setPen(QPen(self.COLOR_BORDER, 1))

    def set_current(self, current: bool):
        """设置为当前播放音符"""
        self._is_current = current
        self._update_appearance()

    def set_played(self, played: bool):
        """设置为已播放"""
        self._is_played = played
        self._update_appearance()

    def update_geometry(self, pixels_per_second: float, row_height: float):
        """更新几何位置"""
        x = self.start_time * pixels_per_second
        y = self.row_index * row_height + 1  # 1px 间距
        w = max(self.duration * pixels_per_second, 4)  # 最小 4px 宽度
        h = row_height - 2  # 2px 间距
        self.setRect(x, y, w, h)


class KeyProgressWidget(QGraphicsView):
    """按键进度视图 - 显示按键时间线"""

    # 信号
    sig_scroll_changed = pyqtSignal(int)  # 水平滚动位置变化

    # 常量
    ROW_HEIGHT = 20.0       # 每行高度
    KEY_LABEL_WIDTH = 40    # 左侧按键标签宽度
    PLAYHEAD_COLOR = QColor(255, 0, 0)
    BG_COLOR = QColor(30, 30, 30)
    GRID_COLOR = QColor(50, 50, 50)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 场景
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setBackgroundBrush(self.BG_COLOR)

        # 数据
        self._events: List[Dict] = []
        self._key_bars: List[KeyNoteBar] = []
        self._key_rows: List[Tuple[str, int]] = []  # (key_char, midi_offset)

        # 布局参数
        self._root_note = 60  # C4
        self._layout: KeyboardLayout = LAYOUT_21KEY
        self.pixels_per_second = 100.0
        self.row_height = self.ROW_HEIGHT

        # 播放头
        self._playhead: Optional[QGraphicsLineItem] = None
        self._playhead_time = 0.0
        self._current_bar_index = -1

        # 视图设置
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # 样式
        self.setStyleSheet("""
            QGraphicsView {
                border: none;
                background-color: #1E1E1E;
            }
            QScrollBar:horizontal {
                background-color: #2D2D2D;
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background-color: #555;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar:vertical {
                background-color: #2D2D2D;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 6px;
                min-height: 20px;
            }
        """)

        # 连接滚动信号
        self.horizontalScrollBar().valueChanged.connect(self._on_hscroll)

    def _on_hscroll(self, value: int):
        """水平滚动变化"""
        self.sig_scroll_changed.emit(value)

    def set_scroll_offset(self, offset: int):
        """设置水平滚动位置（从 PianoRollWidget 同步）"""
        self.horizontalScrollBar().blockSignals(True)
        self.horizontalScrollBar().setValue(offset)
        self.horizontalScrollBar().blockSignals(False)

    def set_layout(self, layout_name: str):
        """设置键盘布局"""
        layout = KEYBOARD_LAYOUTS.get(layout_name)
        if layout:
            self._layout = layout
            self._rebuild_key_rows()
            self._rebuild_bars()

    def set_root_note(self, root: int):
        """设置根音"""
        self._root_note = root
        self._rebuild_key_rows()
        self._rebuild_bars()

    def set_scale(self, pixels_per_second: float):
        """设置水平缩放"""
        self.pixels_per_second = pixels_per_second
        self._update_all_geometry()

    def set_row_height(self, height: float):
        """设置行高"""
        self.row_height = height
        self._update_all_geometry()

    def _rebuild_key_rows(self):
        """重建按键行列表"""
        self._key_rows.clear()

        # 获取所有按键（按音符顺序）
        sorted_items = sorted(self._layout.note_to_key.items(), key=lambda x: x[0])

        for offset, key_char in sorted_items:
            self._key_rows.append((key_char.lower(), offset))

    def _get_row_index(self, midi_note: int) -> int:
        """获取 MIDI 音符对应的行索引"""
        offset = midi_note - self._root_note
        for i, (_, row_offset) in enumerate(self._key_rows):
            if row_offset == offset:
                return i
        return -1  # 不在布局范围内

    def set_events(self, events: List[Dict]):
        """设置事件列表

        Args:
            events: 事件列表 [{"time": float, "note": int, "duration": float}, ...]
        """
        self._events = sorted(events, key=lambda e: e["time"])
        self._rebuild_key_rows()
        self._rebuild_bars()

    def _rebuild_bars(self):
        """重建音符条形"""
        # 清除现有条形
        for bar in self._key_bars:
            self.scene.removeItem(bar)
        self._key_bars.clear()

        # 清除播放头
        if self._playhead:
            self.scene.removeItem(self._playhead)
            self._playhead = None

        # 创建新条形
        for event in self._events:
            midi_note = event["note"]
            row_index = self._get_row_index(midi_note)

            if row_index < 0:
                # 尝试八度移位
                for shift in [-12, 12, -24, 24]:
                    shifted = midi_note + shift
                    row_index = self._get_row_index(shifted)
                    if row_index >= 0:
                        break

            if row_index < 0:
                continue  # 无法映射

            key_char = self._key_rows[row_index][0]
            bar = KeyNoteBar(
                note=midi_note,
                key=key_char,
                start_time=event["time"],
                duration=event.get("duration", 0.1),
                row_index=row_index
            )
            bar.update_geometry(self.pixels_per_second, self.row_height)
            self.scene.addItem(bar)
            self._key_bars.append(bar)

        # 绘制网格线
        self._draw_grid()

        # 创建播放头
        self._create_playhead()

        # 更新场景大小
        self._update_scene_size()

    def _draw_grid(self):
        """绘制网格线"""
        if not self._key_rows:
            return

        # 计算场景宽度
        if self._events:
            max_time = max(e["time"] + e.get("duration", 0.1) for e in self._events)
        else:
            max_time = 10.0
        scene_width = max(max_time * self.pixels_per_second + 200, 800)

        pen = QPen(self.GRID_COLOR, 1)

        # 水平网格线（行分隔）
        for i in range(len(self._key_rows) + 1):
            y = i * self.row_height
            line = self.scene.addLine(0, y, scene_width, y, pen)
            line.setZValue(-1)

    def _create_playhead(self):
        """创建播放头"""
        if not self._key_rows:
            return

        height = len(self._key_rows) * self.row_height
        pen = QPen(self.PLAYHEAD_COLOR, 2)
        self._playhead = self.scene.addLine(0, 0, 0, height, pen)
        self._playhead.setZValue(100)

    def _update_scene_size(self):
        """更新场景大小（与 PianoRoll 保持一致的计算方式）"""
        if self._events:
            max_time = max(e["time"] + e.get("duration", 0.1) for e in self._events)
        else:
            max_time = 10.0

        # 使用与 PianoRoll 相同的计算方式：max(content_width, viewport_width)
        content_width = max_time * self.pixels_per_second + 100  # +100 与 piano_roll 一致
        viewport_width = self.viewport().width()
        scene_width = max(content_width, viewport_width)
        scene_height = max(len(self._key_rows) * self.row_height, 100)

        self.scene.setSceneRect(0, 0, scene_width, scene_height)

    def _update_all_geometry(self):
        """更新所有元素的几何位置"""
        for bar in self._key_bars:
            bar.update_geometry(self.pixels_per_second, self.row_height)

        if self._playhead:
            height = len(self._key_rows) * self.row_height
            self._playhead.setLine(
                self._playhead_time * self.pixels_per_second, 0,
                self._playhead_time * self.pixels_per_second, height
            )

        self._update_scene_size()

    def update_playback_time(self, current_time: float, auto_scroll: bool = True):
        """更新播放时间

        Args:
            current_time: 当前播放时间 (秒)
            auto_scroll: 是否自动滚动（当 playhead 超出可视区域时）
        """
        self._playhead_time = current_time

        # 更新播放头位置
        if self._playhead:
            height = len(self._key_rows) * self.row_height
            x = current_time * self.pixels_per_second
            self._playhead.setLine(x, 0, x, height)

            # 自动滚动：当 playhead 超出视口右侧 80% 时，滚动到 30% 位置
            if auto_scroll:
                viewport_width = self.viewport().width()
                scroll_offset = self.horizontalScrollBar().value()
                playhead_viewport_x = x - scroll_offset

                if playhead_viewport_x > viewport_width * 0.8:
                    new_scroll = int(x - viewport_width * 0.3)
                    new_scroll = max(0, new_scroll)
                    self.horizontalScrollBar().setValue(new_scroll)

        # 遍历所有音符条形，更新状态
        for bar in self._key_bars:
            bar_end = bar.start_time + bar.duration
            if bar_end <= current_time:
                # 已播放完毕
                bar.set_current(False)
                bar.set_played(True)
            elif bar.start_time <= current_time < bar_end:
                # 正在播放
                bar.set_current(True)
                bar.set_played(False)
            else:
                # 未播放
                bar.set_current(False)
                # 不清除 played 状态（允许 reset 时统一清除）

    def reset(self):
        """重置播放状态"""
        self._playhead_time = 0.0
        self._current_bar_index = -1

        for bar in self._key_bars:
            bar.set_current(False)
            bar.set_played(False)

        if self._playhead:
            height = len(self._key_rows) * self.row_height
            self._playhead.setLine(0, 0, 0, height)

        self.horizontalScrollBar().setValue(0)

    def resizeEvent(self, event):
        """处理窗口大小变化，更新场景大小以匹配 PianoRoll"""
        super().resizeEvent(event)
        self._update_scene_size()


class KeyLabelWidget(QWidget):
    """按键标签列（左侧固定列）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_rows: List[Tuple[str, int]] = []
        self._root_note = 60
        self._row_height = KeyProgressWidget.ROW_HEIGHT
        self._scroll_offset = 0  # 垂直滚动偏移

        self.setFixedWidth(80)  # Match KeyboardWidget (OCTAVE_LABEL_WIDTH + KEYBOARD_WIDTH)
        self.setStyleSheet("background-color: #282828;")

    def set_key_rows(self, key_rows: List[Tuple[str, int]], root_note: int):
        """设置按键行"""
        self._key_rows = key_rows
        self._root_note = root_note
        self.update()

    def set_row_height(self, height: float):
        """设置行高"""
        self._row_height = height
        self.setMinimumHeight(int(len(self._key_rows) * height))
        self.update()

    def set_scroll_offset(self, offset: int):
        """设置垂直滚动偏移"""
        if self._scroll_offset != offset:
            self._scroll_offset = offset
            self.update()

    def paintEvent(self, event):
        """绘制按键标签"""
        from PyQt6.QtGui import QPainter

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont("Consolas", 9)
        font.setBold(True)
        painter.setFont(font)

        for i, (key_char, note_offset) in enumerate(self._key_rows):
            y = int(i * self._row_height - self._scroll_offset)
            h = int(self._row_height)

            # 跳过不可见行 (性能优化)
            if y + h < 0 or y > self.height():
                continue

            # 背景色（交替）
            if i % 2 == 0:
                painter.fillRect(0, y, self.width(), h, QColor(40, 40, 40))
            else:
                painter.fillRect(0, y, self.width(), h, QColor(35, 35, 35))

            # 按键字符
            painter.setPen(QColor(200, 200, 200))
            text = key_char.upper()
            rect = QRectF(0, y, self.width() - 5, h)
            painter.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)

        painter.end()


class KeyListWidget(QWidget):
    """按键列表进度窗口 - 组合视图"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._root_note = 60
        self._layout_name = "21-key"

        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        self.setMinimumHeight(100)
        self.setStyleSheet("background-color: #1E1E1E;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧按键标签
        self.key_labels = KeyLabelWidget()
        layout.addWidget(self.key_labels)

        # 右侧进度视图
        self.progress_view = KeyProgressWidget()
        layout.addWidget(self.progress_view)

        # 垂直滚动同步
        self.progress_view.verticalScrollBar().valueChanged.connect(
            self.key_labels.set_scroll_offset
        )

    def set_events(self, events: List[Dict]):
        """设置事件列表"""
        self.progress_view.set_events(events)

        # 更新按键标签
        self.key_labels.set_key_rows(
            self.progress_view._key_rows,
            self.progress_view._root_note
        )
        self.key_labels.set_row_height(self.progress_view.row_height)

    def set_layout(self, layout_name: str):
        """设置键盘布局"""
        self._layout_name = layout_name
        self.progress_view.set_layout(layout_name)
        self.key_labels.set_key_rows(
            self.progress_view._key_rows,
            self.progress_view._root_note
        )

    def set_root_note(self, root: int):
        """设置根音"""
        self._root_note = root
        self.progress_view.set_root_note(root)
        self.key_labels.set_key_rows(
            self.progress_view._key_rows,
            self.progress_view._root_note
        )

    def set_scale(self, pixels_per_second: float):
        """设置水平缩放（与 PianoRollWidget 同步）"""
        self.progress_view.set_scale(pixels_per_second)

    def set_row_height(self, height: float):
        """设置行高"""
        self.progress_view.set_row_height(height)
        self.key_labels.set_row_height(height)

    def set_scroll_offset(self, offset: int):
        """设置水平滚动位置"""
        self.progress_view.set_scroll_offset(offset)

    def update_playback_time(self, current_time: float, auto_scroll: bool = False):
        """更新播放时间

        Args:
            current_time: 当前播放时间 (秒)
            auto_scroll: 是否自动滚动（默认 False，由 PianoRoll 统一控制）
        """
        self.progress_view.update_playback_time(current_time, auto_scroll)

    def reset(self):
        """重置播放状态"""
        self.progress_view.reset()

    def set_auto_scroll(self, enabled: bool):
        """设置自动滚动（兼容旧接口）"""
        pass

    def set_title(self, title: str):
        """设置标题（兼容旧接口，不再使用）"""
        pass

    # 信号转发
    @property
    def sig_scroll_changed(self):
        """水平滚动信号"""
        return self.progress_view.sig_scroll_changed
