"""
KeyboardWidget - 左侧钢琴键盘

Features:
- 显示音符名
- 八度音域段可视化 (可用范围 / 选中八度)
- 点击八度标签切换选中
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtCore import Qt, pyqtSignal


class KeyboardWidget(QWidget):
    """左侧钢琴键盘，显示音符名 + 八度音域段"""

    # 信号：八度选中变化 (octave_number)
    sig_octave_selected = pyqtSignal(int)
    # 信号：拖拽选择音域范围 (low_note, high_note)
    sig_range_selected = pyqtSignal(int, int)

    # 常量
    NOTE_RANGE = (21, 108)  # A0 to C8
    WHITE_KEY_COLOR = QColor(240, 240, 240)
    BLACK_KEY_COLOR = QColor(40, 40, 40)
    BORDER_COLOR = QColor(100, 100, 100)
    TEXT_COLOR = QColor(80, 80, 80)
    TEXT_COLOR_BLACK = QColor(200, 200, 200)

    # 八度音域段颜色
    RANGE_AVAILABLE_COLOR = QColor(100, 200, 100, 80)   # 绿色半透明 - 可用范围
    RANGE_SELECTED_COLOR = QColor(255, 200, 50, 120)    # 黄色半透明 - 选中八度
    RANGE_UNAVAILABLE_COLOR = QColor(100, 100, 100, 60) # 灰色半透明 - 不可用
    DRAG_SELECT_COLOR = QColor(100, 150, 255, 150)      # 蓝色半透明 - 拖拽选择中

    # 音名
    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    # 布局常量
    OCTAVE_LABEL_WIDTH = 20  # 八度标签列宽度
    KEYBOARD_WIDTH = 60      # 键盘区域宽度

    def __init__(self, parent=None):
        super().__init__(parent)

        self.pixels_per_note = 12.0
        self.scroll_offset = 0

        # 八度音域段
        self.available_range = self.NOTE_RANGE  # 默认可用范围 = 完整 88 键
        self.selected_octave = 4                # 当前选中的八度 (C4-B4)

        # 拖拽选择音域
        self._drag_start_note: int = None
        self._drag_current_note: int = None
        self._is_dragging: bool = False

        self.setFixedWidth(self.OCTAVE_LABEL_WIDTH + self.KEYBOARD_WIDTH)
        self.setMinimumHeight(100)

    def set_scale(self, pixels_per_note: float):
        """设置垂直缩放"""
        self.pixels_per_note = pixels_per_note
        self.update()

    def set_scroll_offset(self, offset: int):
        """设置垂直滚动偏移"""
        self.scroll_offset = offset
        self.update()

    def set_available_range(self, low: int, high: int):
        """设置可用音域范围 (MIDI note numbers)

        来源: EditorWindow._update_keyboard_range() 在加载 MIDI 后调用，
        根据 MIDI 文件中实际音符范围计算并扩展到完整八度边界。
        若无音符则回退到默认 NOTE_RANGE (21-108)。
        """
        self.available_range = (low, high)
        self.update()

    def set_selected_octave(self, octave: int):
        """设置选中的八度 (0-8)"""
        self.selected_octave = octave
        self.update()

    def paintEvent(self, event):
        """绘制键盘 + 八度音域段"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        note_min, note_max = self.NOTE_RANGE
        total_width = self.width()
        kbd_x = self.OCTAVE_LABEL_WIDTH  # 键盘区域起始 X
        kbd_w = self.KEYBOARD_WIDTH      # 键盘区域宽度

        font = QFont("Arial", 7)
        painter.setFont(font)

        # 计算可见音符范围
        start_note = int(self.scroll_offset / self.pixels_per_note)
        visible_notes = int(self.height() / self.pixels_per_note) + 2

        # 绘制八度标签背景
        painter.fillRect(0, 0, kbd_x, self.height(), QBrush(QColor(50, 50, 50)))

        for i in range(visible_notes + 1):
            note_idx = note_max - (start_note + i)
            if note_idx < note_min or note_idx > note_max:
                continue

            y = int(i * self.pixels_per_note - (self.scroll_offset % self.pixels_per_note))
            h = int(self.pixels_per_note)

            # 判断黑键/白键
            is_black = note_idx % 12 in [1, 3, 6, 8, 10]

            # 绘制键盘区域
            if is_black:
                painter.fillRect(kbd_x, y, kbd_w, h, QBrush(self.BLACK_KEY_COLOR))
            else:
                painter.fillRect(kbd_x, y, kbd_w, h, QBrush(self.WHITE_KEY_COLOR))

            # 绘制八度音域段覆盖色
            octave = (note_idx // 12) - 1
            range_low, range_high = self.available_range

            if range_low <= note_idx <= range_high:
                # 在可用范围内
                if octave == self.selected_octave:
                    # 选中的八度 - 黄色
                    painter.fillRect(kbd_x, y, kbd_w, h, QBrush(self.RANGE_SELECTED_COLOR))
                else:
                    # 可用但未选中 - 绿色
                    painter.fillRect(kbd_x, y, kbd_w, h, QBrush(self.RANGE_AVAILABLE_COLOR))
            else:
                # 不可用范围 - 灰色
                painter.fillRect(kbd_x, y, kbd_w, h, QBrush(self.RANGE_UNAVAILABLE_COLOR))

            # 拖拽选择高亮
            if self._is_dragging and self._drag_start_note is not None and self._drag_current_note is not None:
                drag_low = min(self._drag_start_note, self._drag_current_note)
                drag_high = max(self._drag_start_note, self._drag_current_note)
                if drag_low <= note_idx <= drag_high:
                    painter.fillRect(kbd_x, y, kbd_w, h, QBrush(self.DRAG_SELECT_COLOR))

            # 边框
            painter.setPen(QPen(self.BORDER_COLOR, 0.5))
            painter.drawLine(kbd_x, y + h, total_width, y + h)

            # 音名 (只在 C 音上显示八度号)
            note_name = self.NOTE_NAMES[note_idx % 12]
            if note_name == "C":
                label = f"C{octave}"
            else:
                label = note_name

            # 文字颜色
            painter.setPen(self.TEXT_COLOR_BLACK if is_black else self.TEXT_COLOR)
            painter.drawText(kbd_x + 5, y + h - 2, label)

        # 绘制八度标签
        self._draw_octave_labels(painter)

        # 右边框
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawLine(total_width - 1, 0, total_width - 1, self.height())

        # 八度标签列右边框
        painter.drawLine(kbd_x - 1, 0, kbd_x - 1, self.height())

    def note_to_y(self, note: int) -> int:
        """音符转 Y 坐标"""
        return int((self.NOTE_RANGE[1] - note) * self.pixels_per_note - self.scroll_offset)

    def y_to_note(self, y: int) -> int:
        """Y 坐标转音符"""
        return self.NOTE_RANGE[1] - int((y + self.scroll_offset) / self.pixels_per_note)

    def _draw_octave_labels(self, painter: QPainter):
        """绘制八度标签列 (0-8)"""
        note_min, note_max = self.NOTE_RANGE
        range_low, range_high = self.available_range

        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)

        # 遍历所有八度 (0-8)
        for octave in range(9):
            # 八度对应的 MIDI note 范围: C(n) = 12*(n+1), B(n) = 12*(n+1)+11
            octave_start = 12 * (octave + 1)      # C of this octave
            octave_end = 12 * (octave + 1) + 11   # B of this octave

            # 计算八度区域的 Y 坐标范围
            y_top = self.note_to_y(min(octave_end, note_max))
            y_bottom = self.note_to_y(max(octave_start, note_min))

            if y_bottom < 0 or y_top > self.height():
                continue  # 不在可见区域

            # 八度标签背景色
            if octave_start >= range_low and octave_end <= range_high:
                # 整个八度在可用范围内
                if octave == self.selected_octave:
                    bg_color = QColor(255, 200, 50)  # 黄色 - 选中
                else:
                    bg_color = QColor(100, 200, 100)  # 绿色 - 可用
            elif octave_end < range_low or octave_start > range_high:
                # 整个八度不在范围内
                bg_color = QColor(80, 80, 80)  # 灰色 - 不可用
            else:
                # 部分在范围内
                bg_color = QColor(150, 180, 130)  # 浅绿 - 部分可用

            # 绘制标签背景
            label_h = max(y_bottom - y_top, 12)
            painter.fillRect(0, y_top, self.OCTAVE_LABEL_WIDTH, label_h, QBrush(bg_color))

            # 绘制八度号
            painter.setPen(QColor(30, 30, 30))
            label_y = y_top + label_h // 2 + 4
            painter.drawText(4, label_y, str(octave))

            # 绘制分隔线
            painter.setPen(QPen(self.BORDER_COLOR, 1))
            painter.drawLine(0, y_bottom, self.OCTAVE_LABEL_WIDTH, y_bottom)

    def mousePressEvent(self, event):
        """点击八度标签切换选中，或开始拖拽选择音域"""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            if x < self.OCTAVE_LABEL_WIDTH:
                # 点击在八度标签列
                note = self.y_to_note(int(event.position().y()))
                octave = (note // 12) - 1
                if 0 <= octave <= 8:
                    self.selected_octave = octave
                    self.sig_octave_selected.emit(octave)
                    self.update()
                return
            else:
                # 点击在键盘区域 - 开始拖拽选择音域
                note = self.y_to_note(int(event.position().y()))
                note = max(self.NOTE_RANGE[0], min(self.NOTE_RANGE[1], note))
                self._drag_start_note = note
                self._drag_current_note = note
                self._is_dragging = True
                self.update()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """拖拽更新选择音域"""
        if self._is_dragging:
            note = self.y_to_note(int(event.position().y()))
            note = max(self.NOTE_RANGE[0], min(self.NOTE_RANGE[1], note))
            self._drag_current_note = note
            self.update()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """释放完成选择，发出信号"""
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            if self._drag_start_note is not None and self._drag_current_note is not None:
                low = min(self._drag_start_note, self._drag_current_note)
                high = max(self._drag_start_note, self._drag_current_note)
                self.sig_range_selected.emit(low, high)
            self._drag_start_note = None
            self._drag_current_note = None
            self.update()
            return

        super().mouseReleaseEvent(event)
