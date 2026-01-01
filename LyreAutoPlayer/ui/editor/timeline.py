"""
TimelineWidget - 顶部时间轴
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal


class TimelineWidget(QWidget):
    """顶部时间轴，显示时间刻度"""

    sig_seek = pyqtSignal(float)  # 点击跳转到指定时间 (秒)

    # 常量
    BG_COLOR = QColor(40, 40, 40)
    TEXT_COLOR = QColor(200, 200, 200)
    TICK_COLOR = QColor(100, 100, 100)
    MAJOR_TICK_COLOR = QColor(150, 150, 150)
    PLAYHEAD_COLOR = QColor(255, 0, 0)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.pixels_per_second = 100.0
        self.scroll_offset = 0  # 水平滚动偏移
        self.total_duration = 0.0
        self.playhead_time = 0.0

        self.setFixedHeight(30)
        self.setMinimumWidth(100)

    def set_scale(self, pixels_per_second: float):
        """设置缩放"""
        self.pixels_per_second = pixels_per_second
        self.update()

    def set_scroll_offset(self, offset: int):
        """设置滚动偏移"""
        self.scroll_offset = offset
        self.update()

    def set_duration(self, duration: float):
        """设置总时长"""
        self.total_duration = duration
        self.update()

    def set_playhead(self, time_sec: float):
        """设置播放头位置"""
        self.playhead_time = time_sec
        self.update()

    def paintEvent(self, event):
        """绘制时间轴"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), self.BG_COLOR)

        # 计算可见范围
        start_time = self.scroll_offset / self.pixels_per_second
        end_time = start_time + self.width() / self.pixels_per_second

        # 决定刻度间隔 (根据缩放)
        if self.pixels_per_second >= 200:
            major_interval = 0.5
            minor_interval = 0.1
        elif self.pixels_per_second >= 100:
            major_interval = 1.0
            minor_interval = 0.5
        elif self.pixels_per_second >= 50:
            major_interval = 2.0
            minor_interval = 1.0
        else:
            major_interval = 5.0
            minor_interval = 1.0

        # 绘制刻度
        font = QFont("Arial", 8)
        painter.setFont(font)

        t = 0.0
        while t <= self.total_duration + major_interval:
            if t >= start_time - major_interval and t <= end_time + major_interval:
                x = int((t - start_time) * self.pixels_per_second)

                # 主刻度
                if abs(t % major_interval) < 0.001 or abs(t % major_interval - major_interval) < 0.001:
                    painter.setPen(QPen(self.MAJOR_TICK_COLOR, 1))
                    painter.drawLine(x, 15, x, 30)
                    # 时间标签
                    painter.setPen(self.TEXT_COLOR)
                    label = f"{int(t // 60)}:{int(t % 60):02d}" if t >= 60 else f"{t:.1f}"
                    painter.drawText(x + 2, 12, label)
                else:
                    # 次刻度
                    painter.setPen(QPen(self.TICK_COLOR, 1))
                    painter.drawLine(x, 22, x, 30)

            t += minor_interval

        # 绘制播放头
        if 0 <= self.playhead_time <= self.total_duration:
            x = int((self.playhead_time - start_time) * self.pixels_per_second)
            painter.setPen(QPen(self.PLAYHEAD_COLOR, 2))
            painter.drawLine(x, 0, x, 30)

    def mousePressEvent(self, event):
        """点击跳转"""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            time_sec = (x + self.scroll_offset) / self.pixels_per_second
            time_sec = max(0, min(time_sec, self.total_duration))
            self.sig_seek.emit(time_sec)
