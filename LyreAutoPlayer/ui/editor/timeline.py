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

    # 常量 - 布局
    HEIGHT = 50              # 总高度 (增加以容纳两行)
    ROW_BAR = 20             # 上行高度 (小节/BPM)
    ROW_TIME = 30            # 下行高度 (秒数)

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
        # 原始 tick 事件 (用于精确计算)
        self._tempo_events_tick: List[Tuple[int, int]] = [(0, 500000)]
        self._time_sig_events_tick: List[Tuple[int, int, int]] = [(0, 4, 4)]

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
        """根据 tempo/time signature 重建小节边界时间列表"""
        self._bar_times = []

        if self.total_duration <= 0:
            return

        # 简化处理：使用第一个 tempo 和 time signature
        # (完整实现需要处理变速变拍)
        bpm = self.bpm
        beats_per_bar = self.time_sig_numerator
        beat_unit = self.time_sig_denominator

        # 每拍时长 (秒)
        # 注意：beat_unit 表示几分音符为一拍
        # 4 表示四分音符，所以 60/bpm 是四分音符时长
        # 如果 beat_unit=8，则一拍是八分音符，时长 = 60/bpm * 4/8
        seconds_per_beat = (60.0 / bpm) * (4.0 / beat_unit)
        seconds_per_bar = seconds_per_beat * beats_per_bar

        if seconds_per_bar <= 0:
            return

        # 生成小节边界
        bar_num = 1
        t = 0.0
        while t <= self.total_duration + seconds_per_bar:
            self._bar_times.append((bar_num, t))
            bar_num += 1
            t += seconds_per_bar

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

        # 字体 (BPM 字号根据 ROW_BAR 动态计算)
        font_bar = QFont("Arial", 9, QFont.Weight.Bold)
        font_time = QFont("Arial", 8)
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
        # 播放头 (贯穿两行)
        # ─────────────────────────────────────────────────────────────────────
        if 0 <= self.playhead_time <= self.total_duration:
            x = int((self.playhead_time - start_time) * self.pixels_per_second)
            painter.setPen(QPen(self.PLAYHEAD_COLOR, 2))
            painter.drawLine(x, 0, x, self.HEIGHT)

    def _draw_bar_row(self, painter: QPainter, start_time: float, end_time: float,
                       font_bar: QFont, font_bpm: QFont):
        """绘制上行: 小节编号 + BPM 指示 (使用 tick 精确计算)"""
        row_top = 0
        row_bottom = self.ROW_BAR

        # 绘制分隔线
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.drawLine(0, row_bottom, self.width(), row_bottom)

        # 绘制 BPM 指示 (始终在可视区左侧)
        painter.setFont(font_bpm)
        painter.setPen(self.BPM_COLOR)
        bpm_text = f"♩={int(self.bpm)}"
        painter.drawText(4, 14, bpm_text)

        # 使用 tick 精确计算拍子和小节
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
                painter.drawLine(x, row_top + 10, x, row_bottom)

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
                    painter.drawLine(x, row_top + 15, x, row_bottom)
                    # 时间标签
                    painter.setPen(self.TEXT_COLOR_DIM)
                    label = f"{int(t // 60)}:{int(t % 60):02d}" if t >= 60 else f"{t:.1f}s"
                    painter.drawText(x + 2, row_top + 12, label)
                else:
                    # 次刻度
                    painter.setPen(QPen(self.TICK_COLOR, 1))
                    painter.drawLine(x, row_top + 22, x, row_bottom)

            t += minor_interval

    def mousePressEvent(self, event):
        """点击跳转"""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            time_sec = (x + self.scroll_offset) / self.pixels_per_second
            time_sec = max(0, min(time_sec, self.total_duration))
            self.sig_seek.emit(time_sec)

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
        act_set_bpm = menu.addAction(f"Set BPM at Bar {bar_num}...")
        act_set_global_bpm = menu.addAction("Set Global BPM...")

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
        """弹出对话框设置小节 BPM

        注意：当前实现为简化版本，只修改全局 BPM。
        完整实现需要支持 tempo map 中间插入 tempo 变化。
        """
        bpm, ok = QInputDialog.getInt(
            self,
            f"Set BPM at Bar {bar_num}",
            f"Enter BPM for bar {bar_num}:",
            int(self.bpm), 20, 300
        )
        if ok:
            # 简化实现：修改全局 BPM
            # TODO: 实现真正的 tempo map 编辑
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
