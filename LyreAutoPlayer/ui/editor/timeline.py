"""
TimelineWidget - 顶部时间轴

显示两行信息:
- 上行: 小节编号 + BPM 指示
- 下行: 秒数刻度
"""
from typing import List, Tuple
from PyQt6.QtWidgets import QWidget, QMenu, QInputDialog
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics
from PyQt6.QtCore import Qt, pyqtSignal


class TimelineWidget(QWidget):
    """顶部时间轴，显示时间刻度和小节编号"""

    sig_seek = pyqtSignal(float)  # 点击跳转到指定时间 (秒)
    sig_bpm_changed = pyqtSignal(int)  # BPM 变化 (用于同步 spinbox)
    sig_select_range = pyqtSignal(float, float)  # 拖动选择范围 (start, end)
    sig_bar_selection_changed = pyqtSignal(list)  # 选中小节列表变化 [bar_num, ...]
    sig_drag_range = pyqtSignal(float, float, bool)  # 拖动边界线 (start, end, active)
    sig_bar_times_changed = pyqtSignal(list)  # 小节边界时间变化 [(bar_num, time_sec), ...]

    # 常量 - 颜色
    BG_COLOR = QColor(40, 40, 40)
    TEXT_COLOR = QColor(200, 200, 200)
    TEXT_COLOR_DIM = QColor(140, 140, 140)
    TICK_COLOR = QColor(100, 100, 100)
    MAJOR_TICK_COLOR = QColor(150, 150, 150)
    BAR_LINE_COLOR = QColor(200, 180, 100)    # 小节线 (金色)
    BEAT_LINE_COLOR = QColor(100, 100, 120)   # 拍线 (淡蓝灰)
    BPM_COLOR = QColor(255, 180, 80)          # BPM 文字 (橙色)
    PLAYHEAD_COLOR = QColor(255, 0, 0)
    SELECT_COLOR = QColor(80, 150, 255, 80)   # 选区背景 (半透明蓝)
    SELECT_BORDER = QColor(80, 150, 255)      # 选区边框
    BAR_SELECTED_COLOR = QColor(255, 255, 200, 100)  # 选中小节背景 (半透明黄)
    DRAG_LINE_COLOR = QColor(255, 255, 0)     # 拖动边界线 (黄色)

    # 常量 - 布局 (节拍行 +25%, 时间行 -25%)
    HEIGHT = 72              # 总高度 = 38 + 34
    ROW_BAR = 38             # 上行高度 (小节/BPM) = 30 * 1.25
    ROW_TIME = 34            # 下行高度 (秒数) = 45 * 0.75

    def __init__(self, parent=None):
        super().__init__(parent)

        self.pixels_per_second = 100.0
        self.scroll_offset = 0  # 水平滚动偏移
        self.total_duration = 0.0
        self.playhead_time = 0.0

        # 节拍信息 (默认 120 BPM, 4/4 拍)
        self.bpm = 120.0
        self.time_sig_numerator = 4    # 分子 (每小节拍数)
        self.time_sig_denominator = 4  # 分母 (几分音符为一拍)
        self.ticks_per_beat = 480      # MIDI ticks per beat

        # Tempo map: [(time_sec, bpm), ...] 按时间排序
        self._tempo_map: List[Tuple[float, float]] = [(0.0, 120.0)]
        # Time signature map: [(time_sec, numerator, denominator), ...]
        self._time_sig_map: List[Tuple[float, int, int]] = [(0.0, 4, 4)]
        # 小节边界缓存: [(bar_number, time_sec), ...]
        self._bar_times: List[Tuple[int, float]] = []
        # 可变小节时长: bar_durations_sec[i] = 第 i+1 小节的时长 (秒)
        # 若为空列表，则使用 BPM 计算的默认时长
        self._bar_durations_sec: List[float] = []
        # 原始 tick 事件 (用于精确计算)
        self._tempo_events_tick: List[Tuple[int, int]] = [(0, 500000)]
        self._time_sig_events_tick: List[Tuple[int, int, int]] = [(0, 4, 4)]

        # 拖动选择状态
        self._drag_start: float = -1.0   # 拖动起点时间 (秒)
        self._drag_end: float = -1.0     # 拖动终点时间 (秒)
        self._is_dragging = False

        # Ctrl+拖动选择小节状态
        self._ctrl_dragging = False      # Ctrl+拖动模式
        self._selected_bars: List[int] = []  # 选中小节编号列表

        self.setFixedHeight(self.HEIGHT)
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
        self._rebuild_bar_times()
        self.sig_bar_times_changed.emit(self._bar_times)
        self.update()

    def set_playhead(self, time_sec: float):
        """设置播放头位置"""
        self.playhead_time = time_sec
        self.update()

    def set_tempo_info(
        self,
        ticks_per_beat: int,
        tempo_events: List[Tuple[int, int]],
        time_sig_events: List[Tuple[int, int, int]]
    ):
        """设置 tempo 和 time signature 信息

        Args:
            ticks_per_beat: MIDI ticks per beat
            tempo_events: [(abs_tick, tempo_microseconds), ...] 按 tick 排序
            time_sig_events: [(abs_tick, numerator, denominator), ...] 按 tick 排序
        """
        self.ticks_per_beat = ticks_per_beat

        # 保存原始 tick 事件 (确保 tick 0 有默认值)
        if not tempo_events or tempo_events[0][0] > 0:
            tempo_events = [(0, 500000)] + list(tempo_events)
        if not time_sig_events or time_sig_events[0][0] > 0:
            time_sig_events = [(0, 4, 4)] + list(time_sig_events)
        self._tempo_events_tick = list(tempo_events)
        self._time_sig_events_tick = list(time_sig_events)

        # 转换 tempo 事件为秒
        self._tempo_map = []
        current_sec = 0.0
        prev_tick = 0
        prev_tempo = 500000  # 默认 120 BPM

        for tick, tempo in tempo_events:
            if tick > prev_tick:
                # 计算时间增量
                delta_ticks = tick - prev_tick
                delta_sec = delta_ticks * prev_tempo / (ticks_per_beat * 1_000_000)
                current_sec += delta_sec
            bpm = 60_000_000 / tempo
            self._tempo_map.append((current_sec, bpm))
            prev_tick = tick
            prev_tempo = tempo

        # 更新初始 BPM
        if self._tempo_map:
            self.bpm = self._tempo_map[0][1]

        # 转换 time signature 事件为秒
        self._time_sig_map = []
        current_sec = 0.0
        prev_tick = 0
        prev_tempo = 500000

        # 重新计算时间 (使用 tempo map)
        tempo_idx = 0
        for tick, num, denom in time_sig_events:
            # 找到此 tick 对应的时间
            time_sec = self._tick_to_second(tick, tempo_events, ticks_per_beat)
            self._time_sig_map.append((time_sec, num, denom))

        # 更新初始 time signature
        if self._time_sig_map:
            _, self.time_sig_numerator, self.time_sig_denominator = self._time_sig_map[0]

        self._rebuild_bar_times()
        self.sig_bar_times_changed.emit(self._bar_times)
        self.update()

    def _tick_to_second(
        self,
        target_tick: int,
        tempo_events: List[Tuple[int, int]],
        ticks_per_beat: int
    ) -> float:
        """将 tick 转换为秒"""
        if target_tick <= 0:
            return 0.0

        current_sec = 0.0
        prev_tick = 0
        prev_tempo = 500000

        for tick, tempo in tempo_events:
            if tick >= target_tick:
                break
            if tick > prev_tick:
                delta_ticks = tick - prev_tick
                delta_sec = delta_ticks * prev_tempo / (ticks_per_beat * 1_000_000)
                current_sec += delta_sec
            prev_tick = tick
            prev_tempo = tempo

        # 计算剩余部分
        if target_tick > prev_tick:
            delta_ticks = target_tick - prev_tick
            delta_sec = delta_ticks * prev_tempo / (ticks_per_beat * 1_000_000)
            current_sec += delta_sec

        return current_sec

    def _rebuild_bar_times(self):
        """根据 tempo/time signature 或可变小节时长重建小节边界时间列表

        优先级:
        1. 如果 _bar_durations_sec 非空，使用可变小节时长
        2. 否则使用 tick 精确计算（基于 tempo map 和 time signature map）
        """
        self._bar_times = []

        if self.total_duration <= 0:
            return

        # 优先使用可变小节时长
        if self._bar_durations_sec:
            self._rebuild_bar_times_from_durations()
        else:
            # 使用 tick 精确计算（基于 tempo map）
            self._rebuild_bar_times_from_ticks()

    def _rebuild_bar_times_from_durations(self):
        """从可变小节时长生成小节边界"""
        bar_num = 1
        t = 0.0
        default_duration = self._get_default_bar_duration()

        while t <= self.total_duration + default_duration:
            self._bar_times.append((bar_num, t))

            if bar_num <= len(self._bar_durations_sec):
                bar_duration = self._bar_durations_sec[bar_num - 1]
            else:
                bar_duration = default_duration

            bar_num += 1
            t += bar_duration

    def _rebuild_bar_times_from_ticks(self):
        """从 tick 精确计算小节边界（基于 tempo map 和 time signature map）

        这确保 _bar_times 与 _draw_bar_row_fixed() 使用相同的计算逻辑，
        避免节拍线与钢琴卷帘白色竖线错位。
        """
        tempo_events = self._tempo_events_tick
        time_sig_events = self._time_sig_events_tick
        ticks_per_beat = self.ticks_per_beat

        if not time_sig_events or ticks_per_beat <= 0:
            # Fallback: 使用固定 BPM 计算
            self._rebuild_bar_times_fixed_bpm()
            return

        # 计算最大 tick (基于总时长)
        max_tick = self._second_to_tick(self.total_duration + 10)  # 加余量

        # 遍历 time signature 区间，按 tick 生成小节边界
        bar_num = 1
        for i, (sig_tick, numerator, denominator) in enumerate(time_sig_events):
            # 计算此区间的结束 tick
            if i + 1 < len(time_sig_events):
                next_sig_tick = time_sig_events[i + 1][0]
            else:
                next_sig_tick = max_tick

            # 每拍/每小节 tick 数
            beat_ticks = ticks_per_beat * 4 // denominator
            bar_ticks = beat_ticks * numerator

            if bar_ticks <= 0:
                continue

            # 从 sig_tick 开始，按 bar_ticks 步进生成小节边界
            current_tick = sig_tick
            while current_tick < next_sig_tick and current_tick <= max_tick:
                time_sec = self._tick_to_second(current_tick, tempo_events, ticks_per_beat)
                if time_sec <= self.total_duration + 1:  # 允许略微超出
                    self._bar_times.append((bar_num, time_sec))
                    bar_num += 1
                current_tick += bar_ticks

    def _rebuild_bar_times_fixed_bpm(self):
        """Fallback: 使用固定 BPM 计算小节边界"""
        default_duration = self._get_default_bar_duration()
        if default_duration <= 0:
            return

        bar_num = 1
        t = 0.0
        while t <= self.total_duration + default_duration:
            self._bar_times.append((bar_num, t))
            bar_num += 1
            t += default_duration

    def get_beat_times(self, start_time: float, end_time: float) -> List[Tuple[float, bool]]:
        """获取指定时间范围内的拍子时间

        Returns:
            [(time_sec, is_bar_start), ...] - is_bar_start=True 表示小节起始
        """
        result = []

        bpm = self.bpm
        beats_per_bar = self.time_sig_numerator
        beat_unit = self.time_sig_denominator

        seconds_per_beat = (60.0 / bpm) * (4.0 / beat_unit)
        if seconds_per_beat <= 0:
            return result

        # 找到起始拍位置
        beat_idx = int(start_time / seconds_per_beat)
        t = beat_idx * seconds_per_beat

        while t <= end_time:
            if t >= start_time:
                # 判断是否是小节起始
                beat_in_song = int(round(t / seconds_per_beat))
                is_bar_start = (beat_in_song % beats_per_bar) == 0
                result.append((t, is_bar_start))
            t += seconds_per_beat

        return result

    def paintEvent(self, event):
        """绘制时间轴 (两行: 小节/BPM + 秒数)"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), self.BG_COLOR)

        # 计算可见范围
        start_time = self.scroll_offset / self.pixels_per_second
        end_time = start_time + self.width() / self.pixels_per_second

        # 字体 (根据行高动态计算)
        bar_font_size = max(9, int(self.ROW_BAR * 0.4))  # ~12pt @ ROW_BAR=30
        time_font_size = max(8, int(self.ROW_TIME * 0.25))  # ~11pt @ ROW_TIME=45
        font_bar = QFont("Arial", bar_font_size, QFont.Weight.Bold)
        font_time = QFont("Arial", time_font_size)
        bpm_font_size = max(9, int(self.ROW_BAR * 0.6))
        font_bpm = QFont("Arial", bpm_font_size, QFont.Weight.Bold)

        # ─────────────────────────────────────────────────────────────────────
        # 上行: 小节编号 + BPM (y: 0 ~ ROW_BAR)
        # ─────────────────────────────────────────────────────────────────────
        self._draw_bar_row(painter, start_time, end_time, font_bar, font_bpm)

        # ─────────────────────────────────────────────────────────────────────
        # 下行: 秒数刻度 (y: ROW_BAR ~ HEIGHT)
        # ─────────────────────────────────────────────────────────────────────
        self._draw_time_row(painter, start_time, end_time, font_time)

        # ─────────────────────────────────────────────────────────────────────
        # 选中小节高亮 (Ctrl+拖动选中的小节)
        # ─────────────────────────────────────────────────────────────────────
        if self._selected_bars:
            for bar_num in self._selected_bars:
                bar_start, bar_end = self._get_bar_time_range(bar_num)
                x1 = int((bar_start - start_time) * self.pixels_per_second)
                x2 = int((bar_end - start_time) * self.pixels_per_second)
                if x2 > x1 and x2 > 0 and x1 < self.width():
                    painter.fillRect(x1, 0, x2 - x1, self.HEIGHT, self.BAR_SELECTED_COLOR)

        # ─────────────────────────────────────────────────────────────────────
        # 选区 (拖动时绘制，但 Ctrl+拖动时不显示蓝色选区)
        # ─────────────────────────────────────────────────────────────────────
        if self._drag_start >= 0 and self._drag_end >= 0 and not self._ctrl_dragging:
            sel_start = min(self._drag_start, self._drag_end)
            sel_end = max(self._drag_start, self._drag_end)
            x1 = int((sel_start - start_time) * self.pixels_per_second)
            x2 = int((sel_end - start_time) * self.pixels_per_second)
            if x2 > x1:
                painter.fillRect(x1, 0, x2 - x1, self.HEIGHT, self.SELECT_COLOR)
                painter.setPen(QPen(self.SELECT_BORDER, 1))
                painter.drawLine(x1, 0, x1, self.HEIGHT)
                painter.drawLine(x2, 0, x2, self.HEIGHT)

        # ─────────────────────────────────────────────────────────────────────
        # Ctrl+拖动时的边界线 (黄线)
        # ─────────────────────────────────────────────────────────────────────
        if self._ctrl_dragging and self._drag_start >= 0 and self._drag_end >= 0:
            raw_start = min(self._drag_start, self._drag_end)
            raw_end = max(self._drag_start, self._drag_end)
            snapped_start = self._snap_bar_floor(raw_start)
            snapped_end = self._snap_bar_ceil(raw_end)
            x1 = int((snapped_start - start_time) * self.pixels_per_second)
            x2 = int((snapped_end - start_time) * self.pixels_per_second)
            painter.setPen(QPen(self.DRAG_LINE_COLOR, 2))
            painter.drawLine(x1, 0, x1, self.HEIGHT)
            painter.drawLine(x2, 0, x2, self.HEIGHT)

        # ─────────────────────────────────────────────────────────────────────
        # 播放头 (贯穿两行)
        # ─────────────────────────────────────────────────────────────────────
        if 0 <= self.playhead_time <= self.total_duration:
            x = int((self.playhead_time - start_time) * self.pixels_per_second)
            painter.setPen(QPen(self.PLAYHEAD_COLOR, 2))
            painter.drawLine(x, 0, x, self.HEIGHT)

    def _draw_bar_row(self, painter: QPainter, start_time: float, end_time: float,
                       font_bar: QFont, font_bpm: QFont):
        """绘制上行: 小节编号 + BPM 指示 (支持可变小节时长)"""
        row_top = 0
        row_bottom = self.ROW_BAR

        # 绘制分隔线
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.drawLine(0, row_bottom, self.width(), row_bottom)

        # 绘制 BPM 指示 (始终在可视区左侧)
        painter.setFont(font_bpm)
        painter.setPen(self.BPM_COLOR)
        bpm_text = f"♩={int(self.bpm)}"
        bpm_y = int(row_bottom * 0.7)  # ~21 @ ROW_BAR=30
        painter.drawText(4, bpm_y, bpm_text)

        # 优先使用 _bar_times（确保 timeline 与 piano_roll 节拍线对齐）
        # _bar_times 来源于 _rebuild_bar_times()，可能是可变时长或 tick 精确计算
        if self._bar_times:
            # 使用预计算的小节边界绘制（与 piano_roll 共享同一数据源）
            self._draw_bar_row_variable(painter, start_time, end_time, font_bar, row_top, row_bottom)
        else:
            # 兜底：_bar_times 为空时实时计算（仅在初始化阶段或特殊情况）
            self._draw_bar_row_fixed(painter, start_time, end_time, font_bar, row_top, row_bottom)

    def _draw_bar_row_variable(self, painter: QPainter, start_time: float, end_time: float,
                                font_bar: QFont, row_top: int, row_bottom: int):
        """使用可变小节边界绘制小节行"""
        beats_per_bar = self.time_sig_numerator

        for i, (bar_num, bar_start) in enumerate(self._bar_times):
            # 获取小节结束时间
            if i + 1 < len(self._bar_times):
                bar_end = self._bar_times[i + 1][1]
            else:
                bar_end = self.total_duration

            # 跳过不在可视区的小节
            if bar_end < start_time:
                continue
            if bar_start > end_time:
                break

            # 绘制小节线 (粗)
            x = int((bar_start - start_time) * self.pixels_per_second)
            painter.setPen(QPen(self.BAR_LINE_COLOR, 2))
            painter.drawLine(x, row_top + 2, x, row_bottom)

            # 小节编号
            painter.setFont(font_bar)
            painter.setPen(self.TEXT_COLOR)
            painter.drawText(x + 3, row_bottom - 4, str(bar_num))

            # 在小节内均分绘制拍线
            if beats_per_bar > 1:
                bar_duration = bar_end - bar_start
                beat_duration = bar_duration / beats_per_bar
                for beat in range(1, beats_per_bar):
                    beat_time = bar_start + beat * beat_duration
                    if start_time <= beat_time <= end_time:
                        bx = int((beat_time - start_time) * self.pixels_per_second)
                        painter.setPen(QPen(self.BEAT_LINE_COLOR, 1))
                        beat_line_top = row_top + int(self.ROW_BAR * 0.5)
                        painter.drawLine(bx, beat_line_top, bx, row_bottom)

        # 绘制最后一条小节线 (总时长位置)
        if self._bar_times and self.total_duration > start_time:
            x = int((self.total_duration - start_time) * self.pixels_per_second)
            painter.setPen(QPen(self.BAR_LINE_COLOR, 2))
            painter.drawLine(x, row_top + 2, x, row_bottom)

    def _draw_bar_row_fixed(self, painter: QPainter, start_time: float, end_time: float,
                             font_bar: QFont, row_top: int, row_bottom: int):
        """使用固定 tick 计算绘制小节行 (原有逻辑)"""
        tempo_events = self._tempo_events_tick
        time_sig_events = self._time_sig_events_tick
        ticks_per_beat = self.ticks_per_beat

        if ticks_per_beat <= 0:
            return

        # 生成拍/小节 tick 列表: [(tick, is_bar_start, bar_num), ...]
        beat_ticks = self._generate_beat_ticks(start_time, end_time)

        for tick, is_bar_start, bar_num in beat_ticks:
            t = self._tick_to_second(tick, tempo_events, ticks_per_beat)
            x = int((t - start_time) * self.pixels_per_second)

            if is_bar_start:
                # 小节线 (粗)
                painter.setPen(QPen(self.BAR_LINE_COLOR, 2))
                painter.drawLine(x, row_top + 2, x, row_bottom)

                # 小节编号
                painter.setFont(font_bar)
                painter.setPen(self.TEXT_COLOR)
                painter.drawText(x + 3, row_bottom - 4, str(bar_num))
            else:
                # 拍线 (细)
                painter.setPen(QPen(self.BEAT_LINE_COLOR, 1))
                beat_line_top = row_top + int(self.ROW_BAR * 0.5)  # ~15 @ ROW_BAR=30
                painter.drawLine(x, beat_line_top, x, row_bottom)

    def _generate_beat_ticks(self, start_time: float, end_time: float) -> List[Tuple[int, bool, int]]:
        """生成可见时间范围内的拍子 tick 列表 (优化版: 直接跳到可视区)

        Returns:
            [(tick, is_bar_start, bar_num), ...]
        """
        result = []
        tempo_events = self._tempo_events_tick
        time_sig_events = self._time_sig_events_tick
        ticks_per_beat = self.ticks_per_beat

        if not time_sig_events or ticks_per_beat <= 0:
            return result

        # 计算可视 tick 范围 (带边距)
        margin = 1.0  # 秒
        visible_start_tick = self._second_to_tick(max(0, start_time - margin))
        visible_end_tick = self._second_to_tick(end_time + margin)

        # 累计小节数 (用于跨 time_sig 区间)
        cumulative_bars = 0

        for i, (sig_tick, numerator, denominator) in enumerate(time_sig_events):
            # 计算此 time signature 区间的结束 tick
            if i + 1 < len(time_sig_events):
                next_sig_tick = time_sig_events[i + 1][0]
            else:
                next_sig_tick = visible_end_tick + ticks_per_beat * 4

            # 每拍/每小节 tick 数
            beat_ticks = ticks_per_beat * 4 // denominator
            bar_ticks = beat_ticks * numerator

            if beat_ticks <= 0 or bar_ticks <= 0:
                continue

            # 跳过完全在可视区之前的区间
            if next_sig_tick <= visible_start_tick:
                # 计算此区间贡献的完整小节数
                interval_ticks = next_sig_tick - sig_tick
                cumulative_bars += interval_ticks // bar_ticks
                continue

            # 跳过完全在可视区之后的区间
            if sig_tick >= visible_end_tick:
                break

            # 计算从可视区开始的第一个拍子
            if visible_start_tick > sig_tick:
                # 从 sig_tick 到 visible_start_tick 之间有多少完整拍
                ticks_before_visible = visible_start_tick - sig_tick
                beats_before = ticks_before_visible // beat_ticks
                first_beat_tick = sig_tick + beats_before * beat_ticks
                # 计算 beat_in_bar 和已过小节数
                beat_in_bar = beats_before % numerator
                bars_before = beats_before // numerator
            else:
                first_beat_tick = sig_tick
                beat_in_bar = 0
                bars_before = 0

            # 生成可视区内的拍子
            current_tick = first_beat_tick
            current_bar_num = cumulative_bars + bars_before + 1

            while current_tick < next_sig_tick and current_tick <= visible_end_tick:
                is_bar_start = (beat_in_bar == 0)
                result.append((current_tick, is_bar_start, current_bar_num))

                # 移动到下一拍
                current_tick += beat_ticks
                beat_in_bar += 1
                if beat_in_bar >= numerator:
                    beat_in_bar = 0
                    current_bar_num += 1

            # 累加此区间的完整小节数
            interval_ticks = min(next_sig_tick, visible_end_tick + bar_ticks) - sig_tick
            cumulative_bars += max(0, interval_ticks // bar_ticks)

        return result

    def _second_to_tick(self, time_sec: float) -> int:
        """将秒转换为 tick (使用 tempo map)"""
        if time_sec <= 0:
            return 0

        tempo_events = self._tempo_events_tick
        ticks_per_beat = self.ticks_per_beat

        current_tick = 0
        current_sec = 0.0
        prev_tempo = 500000

        for i, (tick, tempo) in enumerate(tempo_events):
            tick_sec = self._tick_to_second(tick, tempo_events, ticks_per_beat)
            if tick_sec >= time_sec:
                break
            current_tick = tick
            current_sec = tick_sec
            prev_tempo = tempo

        # 计算剩余时间对应的 tick
        remaining_sec = time_sec - current_sec
        if remaining_sec > 0 and prev_tempo > 0:
            # tick = sec * ticks_per_beat * 1_000_000 / tempo
            additional_ticks = int(remaining_sec * ticks_per_beat * 1_000_000 / prev_tempo)
            current_tick += additional_ticks

        return current_tick

    def _draw_time_row(self, painter: QPainter, start_time: float, end_time: float,
                        font_time: QFont):
        """绘制下行: 秒数刻度"""
        row_top = self.ROW_BAR
        row_bottom = self.HEIGHT

        painter.setFont(font_time)

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

        t = 0.0
        while t <= self.total_duration + major_interval:
            if t >= start_time - major_interval and t <= end_time + major_interval:
                x = int((t - start_time) * self.pixels_per_second)

                # 主刻度
                if abs(t % major_interval) < 0.001 or abs(t % major_interval - major_interval) < 0.001:
                    painter.setPen(QPen(self.MAJOR_TICK_COLOR, 1))
                    major_tick_top = row_top + int(self.ROW_TIME * 0.5)  # ~23 @ ROW_TIME=45
                    painter.drawLine(x, major_tick_top, x, row_bottom)
                    # 时间标签
                    painter.setPen(self.TEXT_COLOR_DIM)
                    label = f"{int(t // 60)}:{int(t % 60):02d}" if t >= 60 else f"{t:.1f}s"
                    label_y = row_top + int(self.ROW_TIME * 0.4)  # ~18 @ ROW_TIME=45
                    painter.drawText(x + 2, label_y, label)
                else:
                    # 次刻度
                    painter.setPen(QPen(self.TICK_COLOR, 1))
                    minor_tick_top = row_top + int(self.ROW_TIME * 0.73)  # ~33 @ ROW_TIME=45
                    painter.drawLine(x, minor_tick_top, x, row_bottom)

            t += minor_interval

    def _snap_bar_floor(self, time_sec: float) -> float:
        """将时间向下取整到小节起点"""
        if not self._bar_times:
            return time_sec
        best_t = 0.0
        for _, t in self._bar_times:
            if t <= time_sec:
                best_t = t
            else:
                break
        return best_t

    def _snap_bar_ceil(self, time_sec: float) -> float:
        """将时间向上取整到小节终点"""
        if not self._bar_times:
            return time_sec
        for _, t in self._bar_times:
            if t >= time_sec:
                return t
        # 超出最后小节，返回总时长
        return self.total_duration

    def _get_bar_at_time(self, time_sec: float) -> int:
        """获取指定时间所在的小节编号"""
        bar_num = 1
        for bn, bt in self._bar_times:
            if bt > time_sec:
                break
            bar_num = bn
        return bar_num

    def _get_bars_in_range(self, start_time: float, end_time: float) -> List[int]:
        """获取时间范围内的所有小节编号"""
        bars = []
        for bn, bt in self._bar_times:
            # 获取此小节的结束时间
            next_bt = self.total_duration
            for nbn, nbt in self._bar_times:
                if nbn == bn + 1:
                    next_bt = nbt
                    break
            # 小节与范围有交集
            if bt < end_time and next_bt > start_time:
                bars.append(bn)
        return bars

    def _get_bar_time_range(self, bar_num: int) -> Tuple[float, float]:
        """获取指定小节的时间范围 (start, end)"""
        start_time = 0.0
        end_time = self.total_duration
        for i, (bn, bt) in enumerate(self._bar_times):
            if bn == bar_num:
                start_time = bt
                # 找下一个小节的开始时间作为结束
                if i + 1 < len(self._bar_times):
                    end_time = self._bar_times[i + 1][1]
                break
        return start_time, end_time

    def get_selected_bars(self) -> List[int]:
        """获取选中的小节列表"""
        return list(self._selected_bars)

    def set_selected_bars(self, bars: List[int]):
        """设置选中的小节列表"""
        self._selected_bars = list(bars)
        self.update()

    def clear_selected_bars(self):
        """清除选中的小节"""
        if self._selected_bars:
            self._selected_bars = []
            self.sig_bar_selection_changed.emit([])
            self.update()

    # ─────────────────────────────────────────────────────────────────────────
    # 可变小节时长 API
    # ─────────────────────────────────────────────────────────────────────────

    def get_bar_times(self) -> List[Tuple[int, float]]:
        """获取小节边界时间列表

        Returns:
            [(bar_number, start_time_sec), ...] - bar_number 从 1 开始
        """
        return list(self._bar_times)

    def get_bar_durations(self) -> List[float]:
        """获取可变小节时长列表

        Returns:
            [duration_sec, ...] - 索引 i 对应小节 i+1 的时长
            若为空列表，表示使用 BPM 计算的默认时长
        """
        return list(self._bar_durations_sec)

    def set_bar_durations(self, durations: List[float]):
        """设置可变小节时长

        Args:
            durations: [duration_sec, ...] - 索引 i 对应小节 i+1 的时长
                       传入空列表恢复使用 BPM 计算的默认时长
        """
        self._bar_durations_sec = list(durations)
        self._rebuild_bar_times()
        self.sig_bar_times_changed.emit(self._bar_times)
        self.update()

    def update_bar_duration(self, bar_num: int, new_duration: float):
        """更新单个小节的时长

        Args:
            bar_num: 小节编号 (1-based)
            new_duration: 新时长 (秒)
        """
        if bar_num < 1 or new_duration <= 0:
            return

        # 确保列表足够长
        default_duration = self._get_default_bar_duration()
        while len(self._bar_durations_sec) < bar_num:
            self._bar_durations_sec.append(default_duration)

        self._bar_durations_sec[bar_num - 1] = new_duration
        self._rebuild_bar_times()
        self.sig_bar_times_changed.emit(self._bar_times)
        self.update()

    def get_bar_duration(self, bar_num: int) -> float:
        """获取指定小节的时长

        Args:
            bar_num: 小节编号 (1-based)

        Returns:
            该小节的时长 (秒)
        """
        if bar_num < 1:
            return 0.0

        if self._bar_durations_sec and bar_num <= len(self._bar_durations_sec):
            return self._bar_durations_sec[bar_num - 1]

        return self._get_default_bar_duration()

    def _get_default_bar_duration(self) -> float:
        """计算默认小节时长 (从 BPM 和拍号)"""
        bpm = self.bpm
        beats_per_bar = self.time_sig_numerator
        beat_unit = self.time_sig_denominator
        seconds_per_beat = (60.0 / bpm) * (4.0 / beat_unit)
        return seconds_per_beat * beats_per_bar

    def mousePressEvent(self, event):
        """点击/开始拖动（不吸附，记录精确位置）"""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            time_sec = (x + self.scroll_offset) / self.pixels_per_second
            time_sec = max(0, min(time_sec, self.total_duration))

            # 检查是否按住 Ctrl 键
            ctrl_held = event.modifiers() & Qt.KeyboardModifier.ControlModifier

            if ctrl_held:
                # Ctrl+左键: 小节选择模式
                self._ctrl_dragging = True
                self._drag_start = time_sec
                self._drag_end = time_sec
                # 发射拖动边界信号（黄线）
                snapped_start = self._snap_bar_floor(time_sec)
                snapped_end = self._snap_bar_ceil(time_sec)
                self.sig_drag_range.emit(snapped_start, snapped_end, True)
            else:
                # 普通左键: 跳转/选区模式
                self._ctrl_dragging = False
                self._drag_start = time_sec
                self._drag_end = time_sec
                self._is_dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        """拖动选区（实时显示原始位置，不吸附预览）"""
        x = event.position().x()
        time_sec = (x + self.scroll_offset) / self.pixels_per_second
        time_sec = max(0, min(time_sec, self.total_duration))

        if self._ctrl_dragging:
            # Ctrl+拖动: 小节选择模式
            self._drag_end = time_sec
            # 发射拖动边界信号（黄线）
            raw_start = min(self._drag_start, self._drag_end)
            raw_end = max(self._drag_start, self._drag_end)
            snapped_start = self._snap_bar_floor(raw_start)
            snapped_end = self._snap_bar_ceil(raw_end)
            self.sig_drag_range.emit(snapped_start, snapped_end, True)
            self.update()
        elif self._is_dragging:
            self._drag_end = time_sec
            self.update()

    def mouseReleaseEvent(self, event):
        """结束拖动并发射选择信号"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._ctrl_dragging:
                # Ctrl+拖动结束: 小节选择
                self._ctrl_dragging = False
                raw_start = min(self._drag_start, self._drag_end)
                raw_end = max(self._drag_start, self._drag_end)
                snapped_start = self._snap_bar_floor(raw_start)
                snapped_end = self._snap_bar_ceil(raw_end)

                # 获取范围内的小节
                new_bars = self._get_bars_in_range(snapped_start, snapped_end)

                # 累加选择（不清除原有）
                for bar in new_bars:
                    if bar not in self._selected_bars:
                        self._selected_bars.append(bar)
                self._selected_bars.sort()

                # 发射信号
                self.sig_bar_selection_changed.emit(list(self._selected_bars))
                # 隐藏黄线
                self.sig_drag_range.emit(0, 0, False)

                self._drag_start = -1.0
                self._drag_end = -1.0
                self.update()
            elif self._is_dragging:
                self._is_dragging = False
                raw_start = min(self._drag_start, self._drag_end)
                raw_end = max(self._drag_start, self._drag_end)
                if abs(raw_end - raw_start) < 0.01:
                    # 单击 → 精确跳转（不吸附），同时清除小节选择
                    self.clear_selected_bars()
                    self.sig_seek.emit(raw_start)
                else:
                    # 拖动 → 选区（start 向下取整，end 向上取整）
                    snapped_start = self._snap_bar_floor(raw_start)
                    snapped_end = self._snap_bar_ceil(raw_end)
                    self.sig_select_range.emit(snapped_start, snapped_end)
                self._drag_start = -1.0
                self._drag_end = -1.0
                self.update()

    def get_bpm_text(self) -> str:
        """获取当前 BPM 显示文本"""
        return f"♩={int(self.bpm)} {self.time_sig_numerator}/{self.time_sig_denominator}"

    def set_bpm(self, bpm: int):
        """设置全局 BPM

        Args:
            bpm: 新的 BPM 值 (20-300)
        """
        bpm = max(20, min(300, bpm))
        self.bpm = float(bpm)
        self._rebuild_bar_times()
        self.update()

    def contextMenuEvent(self, event):
        """右键菜单: 设置 BPM"""
        menu = QMenu(self)

        # 计算点击位置对应的时间和小节
        x = event.pos().x()
        time_sec = (x + self.scroll_offset) / self.pixels_per_second

        # 找到对应的小节号
        bar_num = 1
        for bn, bt in self._bar_times:
            if bt > time_sec:
                break
            bar_num = bn

        # 创建菜单项
        # 注意: BPM 影响网格显示、导出与预览播放速度
        # 真正的 tempo map 编辑（按小节变速）暂未实现
        act_set_bpm = menu.addAction(f"Set BPM (Grid/Export) at Bar {bar_num}...")
        act_set_global_bpm = menu.addAction("Set Global BPM (Grid/Export)...")

        menu.addSeparator()
        act_copy_bpm = menu.addAction(f"Current: {int(self.bpm)} BPM")
        act_copy_bpm.setEnabled(False)

        # 执行菜单
        action = menu.exec(event.globalPos())

        if action == act_set_bpm:
            self._prompt_set_bpm_at_bar(bar_num, time_sec)
        elif action == act_set_global_bpm:
            self._prompt_set_global_bpm()

    def _prompt_set_bpm_at_bar(self, bar_num: int, time_sec: float):
        """弹出对话框设置全局 BPM (应用到整个曲目)

        注意：BPM 影响网格显示、量化、导出与预览播放速度。
        真正的按小节 tempo map 编辑暂未实现。
        """
        bpm, ok = QInputDialog.getInt(
            self,
            f"Set BPM (Grid/Export)",
            f"Set BPM for grid display and export:\n"
            f"(Clicked at bar {bar_num})\n\n"
            f"Note: Affects preview playback speed.",
            int(self.bpm), 20, 300
        )
        if ok:
            # 修改全局 BPM (影响网格、导出与预览速度)
            self.set_bpm(bpm)
            self.sig_bpm_changed.emit(bpm)

    def _prompt_set_global_bpm(self):
        """弹出对话框设置全局 BPM"""
        bpm, ok = QInputDialog.getInt(
            self,
            "Set Global BPM",
            "Enter BPM:",
            int(self.bpm), 20, 300
        )
        if ok:
            self.set_bpm(bpm)
            self.sig_bpm_changed.emit(bpm)
