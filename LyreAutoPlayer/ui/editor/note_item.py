"""
NoteItem - 单个音符的图形表示

Phase 2: 支持选择、拖拽移动
"""
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsItem
from PyQt6.QtGui import QBrush, QPen, QColor, QPainter, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QPointF


class NoteItem(QGraphicsRectItem):
    """单个 MIDI 音符的可视化图形项"""

    # 颜色常量
    COLOR_NORMAL = QColor(100, 149, 237)      # cornflower blue
    COLOR_SELECTED = QColor(255, 165, 0)      # orange
    COLOR_OUT_OF_RANGE = QColor(255, 99, 71)  # tomato
    COLOR_BORDER = QColor(50, 50, 50)

    # 音域范围 (与 PianoRoll 一致)
    NOTE_RANGE = (21, 108)  # A0 to C8

    def __init__(
        self,
        note: int,
        start_time: float,
        duration: float,
        velocity: int = 100,
        track: int = 0,
        channel: int = 0,
        parent=None
    ):
        super().__init__(parent)

        # MIDI 数据
        self.note = note              # MIDI 音高 (0-127)
        self.start_time = start_time  # 起始时间 (秒)
        self.duration = duration      # 时值 (秒)
        self.velocity = velocity      # 力度 (0-127)
        self.track = track            # 轨道号
        self.channel = channel        # MIDI 通道 (0-15)

        # 状态
        self.selected = False
        self.out_of_range = False

        # 拖拽相关
        self._drag_start_pos: QPointF = QPointF()
        self._drag_start_time: float = 0.0
        self._drag_start_note: int = 0

        # 缩放参数 (用于拖拽边界计算)
        self._pixels_per_second: float = 100.0
        self._pixels_per_note: float = 12.0

        # 外观
        self._update_appearance()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):
        """响应 QGraphicsItem 状态变化"""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self.selected = bool(value)
            self._update_appearance()
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # 拖拽时限制位置范围
            new_pos = value
            if isinstance(new_pos, QPointF):
                rect = self.rect()
                # 限制 X (时间不能为负，允许向左拖拽到 0)
                x_min = -rect.x()
                x = max(x_min, new_pos.x())
                # 限制 Y 在音域范围内 (允许向上拖拽到 0)
                note_min, note_max = self.NOTE_RANGE
                y_min = -rect.y()
                y_max = (note_max - note_min) * self._pixels_per_note - rect.y()
                y = max(y_min, min(y_max, new_pos.y()))
                return QPointF(x, y)
        return super().itemChange(change, value)

    def set_scale_params(self, pixels_per_second: float, pixels_per_note: float):
        """设置缩放参数 (用于拖拽时计算)"""
        self._pixels_per_second = pixels_per_second
        self._pixels_per_note = pixels_per_note

    def _update_appearance(self):
        """更新外观（颜色）"""
        if self.out_of_range:
            color = self.COLOR_OUT_OF_RANGE
        elif self.selected:
            color = self.COLOR_SELECTED
        else:
            color = self.COLOR_NORMAL

        self.setBrush(QBrush(color))
        self.setPen(QPen(self.COLOR_BORDER, 1))

    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.selected = selected
        self._update_appearance()

    def set_out_of_range(self, out_of_range: bool):
        """设置超音域状态"""
        self.out_of_range = out_of_range
        self._update_appearance()

    def update_geometry(self, pixels_per_second: float, pixels_per_note: float, note_max: int = 108):
        """根据缩放参数更新矩形几何

        Args:
            pixels_per_second: 水平缩放 (像素/秒)
            pixels_per_note: 垂直缩放 (像素/音高)
            note_max: 最高音 (NOTE_RANGE[1])，用于计算 Y 坐标
        """
        # 保存缩放参数供拖拽边界计算使用
        self._pixels_per_second = pixels_per_second
        self._pixels_per_note = pixels_per_note

        x = self.start_time * pixels_per_second
        # 使用 note_max 作为基准，确保坐标在 sceneRect 内
        y = (note_max - self.note) * pixels_per_note
        w = max(self.duration * pixels_per_second, 2)  # 最小宽度 2px
        h = pixels_per_note - 1  # 留 1px 间隙
        self.setRect(x, y, w, h)

    # 音名常量 (用于 paint 方法)
    NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')

    def _get_note_name(self) -> str:
        """根据 MIDI 音高返回音名 (如 C4, D#5)"""
        note_in_octave = self.note % 12
        octave = (self.note // 12) - 1  # MIDI 60 = C4
        return f"{self.NOTE_NAMES[note_in_octave]}{octave}"

    def paint(self, painter: QPainter, option, widget=None):
        """自定义绘制: 矩形 + 居中音高文字 (仅蓝色普通状态)"""
        # 先绘制默认矩形
        super().paint(painter, option, widget)

        # 仅在普通蓝色状态下绘制音高标签
        if self.selected or self.out_of_range:
            return

        rect = self.rect()
        w, h = rect.width(), rect.height()

        # 生成音高文本 (如 C4, D#5)
        text = self._get_note_name()

        # 字号自适应: 从高度估算起始字号
        font_size = int(h * 0.7)
        if font_size < 6:
            return

        # 用 QFontMetrics 检查文本宽度，必要时减小字号
        font = QFont("Consolas", font_size)
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)

        # 若文本超出矩形宽度，逐步减小字号
        while text_width > w - 2 and font_size > 6:
            font_size -= 1
            font = QFont("Consolas", font_size)
            fm = QFontMetrics(font)
            text_width = fm.horizontalAdvance(text)

        # 过小则不绘制
        if font_size < 6:
            return

        # 设置字体和颜色
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))  # 白色文字

        # 居中绘制
        text_height = fm.height()
        x = rect.x() + (w - text_width) / 2
        y = rect.y() + (h + text_height) / 2 - fm.descent()

        painter.drawText(int(x), int(y), text)

    def __repr__(self):
        return f"NoteItem(note={self.note}, start={self.start_time:.3f}, dur={self.duration:.3f})"
