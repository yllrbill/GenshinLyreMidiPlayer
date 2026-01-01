"""
NoteItem - 单个音符的图形表示
"""
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsItem
from PyQt6.QtGui import QBrush, QPen, QColor
from PyQt6.QtCore import Qt


class NoteItem(QGraphicsRectItem):
    """单个 MIDI 音符的可视化图形项"""

    # 颜色常量
    COLOR_NORMAL = QColor(100, 149, 237)      # cornflower blue
    COLOR_SELECTED = QColor(255, 165, 0)      # orange
    COLOR_OUT_OF_RANGE = QColor(255, 99, 71)  # tomato
    COLOR_BORDER = QColor(50, 50, 50)

    def __init__(
        self,
        note: int,
        start_time: float,
        duration: float,
        velocity: int = 100,
        track: int = 0,
        parent=None
    ):
        super().__init__(parent)

        # MIDI 数据
        self.note = note              # MIDI 音高 (0-127)
        self.start_time = start_time  # 起始时间 (秒)
        self.duration = duration      # 时值 (秒)
        self.velocity = velocity      # 力度 (0-127)
        self.track = track            # 轨道号

        # 状态
        self.selected = False
        self.out_of_range = False

        # 外观
        self._update_appearance()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)  # Phase 2 启用

    def itemChange(self, change, value):
        """响应 QGraphicsItem 选择状态变化"""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self.selected = bool(value)
            self._update_appearance()
        return super().itemChange(change, value)

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
        x = self.start_time * pixels_per_second
        # 使用 note_max 作为基准，确保坐标在 sceneRect 内
        y = (note_max - self.note) * pixels_per_note
        w = max(self.duration * pixels_per_second, 2)  # 最小宽度 2px
        h = pixels_per_note - 1  # 留 1px 间隙
        self.setRect(x, y, w, h)

    def __repr__(self):
        return f"NoteItem(note={self.note}, start={self.start_time:.3f}, dur={self.duration:.3f})"
