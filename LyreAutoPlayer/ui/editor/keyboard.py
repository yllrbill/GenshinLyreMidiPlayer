"""
KeyboardWidget - 左侧钢琴键盘
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtCore import Qt


class KeyboardWidget(QWidget):
    """左侧钢琴键盘，显示音符名"""

    # 常量
    NOTE_RANGE = (21, 108)  # A0 to C8
    WHITE_KEY_COLOR = QColor(240, 240, 240)
    BLACK_KEY_COLOR = QColor(40, 40, 40)
    BORDER_COLOR = QColor(100, 100, 100)
    TEXT_COLOR = QColor(80, 80, 80)
    TEXT_COLOR_BLACK = QColor(200, 200, 200)

    # 音名
    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.pixels_per_note = 12.0
        self.scroll_offset = 0

        self.setFixedWidth(60)
        self.setMinimumHeight(100)

    def set_scale(self, pixels_per_note: float):
        """设置垂直缩放"""
        self.pixels_per_note = pixels_per_note
        self.update()

    def set_scroll_offset(self, offset: int):
        """设置垂直滚动偏移"""
        self.scroll_offset = offset
        self.update()

    def paintEvent(self, event):
        """绘制键盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        note_min, note_max = self.NOTE_RANGE
        width = self.width()

        font = QFont("Arial", 7)
        painter.setFont(font)

        # 计算可见音符范围
        start_note = int(self.scroll_offset / self.pixels_per_note)
        visible_notes = int(self.height() / self.pixels_per_note) + 2

        for i in range(visible_notes + 1):
            note_idx = note_max - (start_note + i)
            if note_idx < note_min or note_idx > note_max:
                continue

            y = int(i * self.pixels_per_note - (self.scroll_offset % self.pixels_per_note))
            h = int(self.pixels_per_note)

            # 判断黑键/白键
            is_black = note_idx % 12 in [1, 3, 6, 8, 10]

            if is_black:
                painter.fillRect(0, y, width, h, QBrush(self.BLACK_KEY_COLOR))
                painter.setPen(self.TEXT_COLOR_BLACK)
            else:
                painter.fillRect(0, y, width, h, QBrush(self.WHITE_KEY_COLOR))
                painter.setPen(self.TEXT_COLOR)

            # 边框
            painter.setPen(QPen(self.BORDER_COLOR, 0.5))
            painter.drawLine(0, y + h, width, y + h)

            # 音名 (只在 C 音上显示八度号)
            note_name = self.NOTE_NAMES[note_idx % 12]
            octave = (note_idx // 12) - 1
            if note_name == "C":
                label = f"C{octave}"
            else:
                label = note_name

            # 文字颜色
            painter.setPen(self.TEXT_COLOR_BLACK if is_black else self.TEXT_COLOR)
            painter.drawText(5, y + h - 2, label)

        # 右边框
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawLine(width - 1, 0, width - 1, self.height())

    def note_to_y(self, note: int) -> int:
        """音符转 Y 坐标"""
        return int((self.NOTE_RANGE[1] - note) * self.pixels_per_note - self.scroll_offset)

    def y_to_note(self, y: int) -> int:
        """Y 坐标转音符"""
        return self.NOTE_RANGE[1] - int((y + self.scroll_offset) / self.pixels_per_note)
