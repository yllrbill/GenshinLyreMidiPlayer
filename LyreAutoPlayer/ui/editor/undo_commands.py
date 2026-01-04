"""
Undo Commands - 撤销/重做命令类

Phase 3: 实现 QUndoCommand 子类用于各种编辑操作
"""
import random
import weakref
from typing import List, TYPE_CHECKING
from PyQt6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from .piano_roll import PianoRollWidget


class AddNoteCommand(QUndoCommand):
    """添加音符命令"""

    def __init__(self, piano_roll: "PianoRollWidget", note_data: dict):
        super().__init__("Add Note")
        self._piano_roll = piano_roll
        self._note_data = note_data.copy()
        self._note_item = None  # 创建后保存引用

    def redo(self):
        """执行/重做: 添加音符"""
        from .note_item import NoteItem

        pr = self._piano_roll
        note_max = pr.NOTE_RANGE[1]

        item = NoteItem(
            note=self._note_data["note"],
            start_time=self._note_data["start"],
            duration=self._note_data["duration"],
            velocity=self._note_data.get("velocity", 100),
            track=self._note_data.get("track", 0),
            channel=self._note_data.get("channel", 0)
        )
        item.update_geometry(pr.pixels_per_second, pr.pixels_per_note, note_max)
        pr.scene.addItem(item)
        pr.notes.append(item)
        self._note_item = item

        # 更新总时长
        end_time = self._note_data["start"] + self._note_data["duration"]
        pr.total_duration = max(pr.total_duration, end_time)

    def undo(self):
        """撤销: 删除音符"""
        pr = self._piano_roll
        if self._note_item and self._note_item in pr.notes:
            pr.scene.removeItem(self._note_item)
            pr.notes.remove(self._note_item)

        # 重新计算总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)
        else:
            pr.total_duration = 0.0


class DeleteNotesCommand(QUndoCommand):
    """删除音符命令"""

    def __init__(self, piano_roll: "PianoRollWidget", notes_data: List[dict]):
        super().__init__(f"Delete {len(notes_data)} Note(s)")
        self._piano_roll = piano_roll
        self._notes_data = [d.copy() for d in notes_data]
        self._note_items = []  # 恢复时创建

    def redo(self):
        """执行/重做: 删除音符"""
        from .note_item import NoteItem

        pr = self._piano_roll
        # 找到并删除匹配的音符
        to_remove = []
        for data in self._notes_data:
            for item in pr.notes:
                if (item.note == data["note"] and
                    abs(item.start_time - data["start"]) < 0.001 and
                    abs(item.duration - data["duration"]) < 0.001):
                    to_remove.append(item)
                    break

        for item in to_remove:
            pr.scene.removeItem(item)
            pr.notes.remove(item)

        # 重新计算总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)
        else:
            pr.total_duration = 0.0

    def undo(self):
        """撤销: 恢复音符"""
        from .note_item import NoteItem

        pr = self._piano_roll
        note_max = pr.NOTE_RANGE[1]

        self._note_items.clear()
        for data in self._notes_data:
            item = NoteItem(
                note=data["note"],
                start_time=data["start"],
                duration=data["duration"],
                velocity=data.get("velocity", 100),
                track=data.get("track", 0),
                channel=data.get("channel", 0)
            )
            item.update_geometry(pr.pixels_per_second, pr.pixels_per_note, note_max)
            pr.scene.addItem(item)
            pr.notes.append(item)
            self._note_items.append(item)

        # 更新总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)


class MoveNotesCommand(QUndoCommand):
    """移动音符命令"""

    def __init__(self, piano_roll: "PianoRollWidget",
                 old_positions: List[dict], new_positions: List[dict]):
        super().__init__(f"Move {len(old_positions)} Note(s)")
        self._piano_roll = piano_roll
        self._old_positions = [d.copy() for d in old_positions]
        self._new_positions = [d.copy() for d in new_positions]

    def redo(self):
        """执行/重做: 应用新位置"""
        self._apply_positions(self._new_positions)

    def undo(self):
        """撤销: 恢复旧位置"""
        self._apply_positions(self._old_positions)

    def _apply_positions(self, positions: List[dict]):
        """应用位置列表到音符"""
        pr = self._piano_roll

        for pos in positions:
            # 查找匹配的音符 (通过唯一 ID 或近似匹配)
            for item in pr.notes:
                # 使用 id 字段匹配 (如果有)
                if "id" in pos and id(item) == pos["id"]:
                    item.note = pos["note"]
                    item.start_time = pos["start"]
                    break

        pr._refresh_notes()

        # 更新总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)


class TransposeCommand(QUndoCommand):
    """移调命令"""

    def __init__(self, piano_roll: "PianoRollWidget",
                 notes_data: List[dict], semitones: int):
        direction = "up" if semitones > 0 else "down"
        super().__init__(f"Transpose {abs(semitones)} semitone(s) {direction}")
        self._piano_roll = piano_roll
        self._notes_data = [d.copy() for d in notes_data]
        self._semitones = semitones

    def redo(self):
        """执行/重做: 移调"""
        self._transpose(self._semitones)

    def undo(self):
        """撤销: 反向移调"""
        self._transpose(-self._semitones)

    def _transpose(self, semitones: int):
        """应用移调"""
        pr = self._piano_roll
        note_min, note_max = pr.NOTE_RANGE

        for data in self._notes_data:
            # 查找匹配的音符
            for item in pr.notes:
                if (abs(item.start_time - data["start"]) < 0.001 and
                    abs(item.duration - data["duration"]) < 0.001):
                    new_note = item.note + semitones
                    item.note = max(note_min, min(note_max, new_note))
                    break

        pr._refresh_notes()


class QuantizeCommand(QUndoCommand):
    """量化命令"""

    def __init__(self, piano_roll: "PianoRollWidget",
                 old_times: List[dict], new_times: List[dict]):
        super().__init__(f"Quantize {len(old_times)} Note(s)")
        self._piano_roll = piano_roll
        self._old_times = [d.copy() for d in old_times]
        self._new_times = [d.copy() for d in new_times]

    def redo(self):
        """执行/重做: 应用量化后的时间"""
        self._apply_times(self._new_times)

    def undo(self):
        """撤销: 恢复原始时间"""
        self._apply_times(self._old_times)

    def _apply_times(self, times: List[dict]):
        """应用时间列表"""
        pr = self._piano_roll

        for t in times:
            for item in pr.notes:
                if (item.note == t["note"] and
                    abs(item.duration - t["duration"]) < 0.001):
                    # 匹配成功，更新时间
                    item.start_time = t["start"]
                    break

        pr._refresh_notes()

        # 更新总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)


class AutoTransposeCommand(QUndoCommand):
    """自动移调命令 (八度策略)

    只允许 ±12 或 ±24 半音移调，超出目标音域的音符标记为 out_of_range
    """

    def __init__(self, piano_roll: "PianoRollWidget",
                 notes_data: List[dict], semitones: int,
                 target_low: int, target_high: int):
        direction = "up" if semitones > 0 else "down"
        super().__init__(f"Auto transpose {abs(semitones)} semitone(s) {direction}")
        self._piano_roll = piano_roll
        self._notes_data = [d.copy() for d in notes_data]
        self._semitones = semitones
        self._target_low = target_low
        self._target_high = target_high
        # 记录原始的 out_of_range 状态
        self._original_out_of_range: List[bool] = []

    def redo(self):
        """执行/重做: 应用自动移调"""
        pr = self._piano_roll
        note_min, note_max = pr.NOTE_RANGE

        # 清空原始状态列表（首次执行时）
        if not self._original_out_of_range:
            for data in self._notes_data:
                for item in pr.notes:
                    if (abs(item.start_time - data["start"]) < 0.001 and
                        abs(item.duration - data["duration"]) < 0.001 and
                        item.note == data["note"]):
                        self._original_out_of_range.append(item.out_of_range)
                        break
                else:
                    self._original_out_of_range.append(False)

        # 应用移调
        for data in self._notes_data:
            for item in pr.notes:
                if (abs(item.start_time - data["start"]) < 0.001 and
                    abs(item.duration - data["duration"]) < 0.001 and
                    item.note == data["note"]):
                    new_note = item.note + self._semitones
                    # 限制在 MIDI 有效范围内
                    new_note = max(note_min, min(note_max, new_note))
                    item.note = new_note

                    # 检查是否在目标音域内
                    if new_note < self._target_low or new_note > self._target_high:
                        item.set_out_of_range(True)
                    else:
                        item.set_out_of_range(False)
                    break

        pr._refresh_notes()

    def undo(self):
        """撤销: 恢复原始音高和 out_of_range 状态"""
        pr = self._piano_roll

        for idx, data in enumerate(self._notes_data):
            for item in pr.notes:
                # 匹配移调后的音符（当前音高 = 原音高 + semitones）
                expected_note = data["note"] + self._semitones
                if (abs(item.start_time - data["start"]) < 0.001 and
                    abs(item.duration - data["duration"]) < 0.001 and
                    item.note == max(pr.NOTE_RANGE[0], min(pr.NOTE_RANGE[1], expected_note))):
                    # 恢复原始音高
                    item.note = data["note"]
                    # 恢复原始 out_of_range 状态
                    if idx < len(self._original_out_of_range):
                        item.set_out_of_range(self._original_out_of_range[idx])
                    else:
                        item.set_out_of_range(False)
                    break

        pr._refresh_notes()


class HumanizeCommand(QUndoCommand):
    """人性化抖动命令

    对选中音符应用随机偏移：
    - timing_ms: 起始时间偏移 (毫秒，高斯分布标准差)
    - velocity_var: 力度偏移 (高斯分布标准差)
    - duration_pct: 时值偏移比例 (如 0.05 = ±5%)
    """

    def __init__(self, piano_roll: "PianoRollWidget",
                 notes_data: List[dict],
                 timing_ms: float = 20.0,
                 velocity_var: float = 10.0,
                 duration_pct: float = 0.05):
        super().__init__(f"Humanize {len(notes_data)} Note(s)")
        self._piano_roll = piano_roll
        self._notes_data = [d.copy() for d in notes_data]
        self._timing_ms = timing_ms
        self._velocity_var = velocity_var
        self._duration_pct = duration_pct

        # 预生成随机偏移值 (确保 redo 一致性)
        self._offsets: List[dict] = []
        for _ in notes_data:
            self._offsets.append({
                "timing": random.gauss(0, timing_ms / 1000.0),  # 转换为秒
                "velocity": int(random.gauss(0, velocity_var)),
                "duration": random.gauss(0, duration_pct)
            })

    def redo(self):
        """执行/重做: 应用人性化偏移"""
        pr = self._piano_roll

        for idx, data in enumerate(self._notes_data):
            for item in pr.notes:
                if (item.note == data["note"] and
                    abs(item.start_time - data["start"]) < 0.001 and
                    abs(item.duration - data["duration"]) < 0.001):
                    # 应用偏移
                    offset = self._offsets[idx]
                    item.start_time = max(0, data["start"] + offset["timing"])
                    item.velocity = max(1, min(127, data["velocity"] + offset["velocity"]))
                    new_dur = data["duration"] * (1 + offset["duration"])
                    item.duration = max(0.01, new_dur)  # 最小 10ms
                    break

        pr._refresh_notes()

        # 更新总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)

    def undo(self):
        """撤销: 恢复原始值"""
        pr = self._piano_roll

        for idx, data in enumerate(self._notes_data):
            offset = self._offsets[idx]
            # 查找偏移后的音符
            target_start = max(0, data["start"] + offset["timing"])
            target_vel = max(1, min(127, data["velocity"] + offset["velocity"]))
            target_dur = max(0.01, data["duration"] * (1 + offset["duration"]))

            for item in pr.notes:
                if (item.note == data["note"] and
                    abs(item.start_time - target_start) < 0.01 and
                    abs(item.velocity - target_vel) <= 1):
                    # 恢复原始值
                    item.start_time = data["start"]
                    item.velocity = data["velocity"]
                    item.duration = data["duration"]
                    break

        pr._refresh_notes()

        # 更新总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)


class ApplyJitterCommand(QUndoCommand):
    """应用输入风格抖动命令

    根据 InputStyle 参数对音符应用随机抖动：
    - timing_offset_ms: (min, max) 时间偏移范围 (毫秒, 均匀分布)
    - duration_variation: 时值变化比例 (负值=缩短)
    """

    def __init__(self, piano_roll: "PianoRollWidget",
                 notes_data: List[dict],
                 timing_offset_ms: tuple = (0, 0),
                 duration_variation: float = 0.0,
                 style_name: str = ""):
        super().__init__(f"Apply '{style_name}' jitter to {len(notes_data)} Note(s)")
        self._piano_roll = piano_roll
        self._notes_data = [d.copy() for d in notes_data]
        self._timing_offset_ms = timing_offset_ms
        self._duration_variation = duration_variation

        # 预生成随机偏移值 (确保 redo 一致性)
        min_offset, max_offset = timing_offset_ms
        self._offsets: List[dict] = []
        for _ in notes_data:
            # 时间偏移: 均匀分布
            if min_offset != 0 or max_offset != 0:
                timing_ms = random.uniform(min_offset, max_offset)
            else:
                timing_ms = 0.0

            # 时值变化: 均匀分布
            if duration_variation != 0.0:
                if duration_variation < 0:
                    # 负值 = 只缩短 (staccato)
                    dur_var = random.uniform(duration_variation, 0)
                else:
                    dur_var = random.uniform(-duration_variation, duration_variation)
            else:
                dur_var = 0.0

            self._offsets.append({
                "timing_sec": timing_ms / 1000.0,
                "duration_var": dur_var
            })

    def redo(self):
        """执行/重做: 应用抖动偏移"""
        pr = self._piano_roll

        for idx, data in enumerate(self._notes_data):
            for item in pr.notes:
                if (item.note == data["note"] and
                    abs(item.start_time - data["start"]) < 0.001 and
                    abs(item.duration - data["duration"]) < 0.001):
                    # 应用偏移
                    offset = self._offsets[idx]
                    item.start_time = max(0, data["start"] + offset["timing_sec"])
                    new_dur = data["duration"] * (1 + offset["duration_var"])
                    item.duration = max(0.01, new_dur)  # 最小 10ms
                    break

        pr._refresh_notes()

        # 更新总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)

    def undo(self):
        """撤销: 恢复原始值"""
        pr = self._piano_roll

        for idx, data in enumerate(self._notes_data):
            offset = self._offsets[idx]
            # 查找偏移后的音符
            target_start = max(0, data["start"] + offset["timing_sec"])
            target_dur = max(0.01, data["duration"] * (1 + offset["duration_var"]))

            for item in pr.notes:
                if (item.note == data["note"] and
                    abs(item.start_time - target_start) < 0.01 and
                    abs(item.duration - target_dur) < 0.01):
                    # 恢复原始值
                    item.start_time = data["start"]
                    item.duration = data["duration"]
                    break

        pr._refresh_notes()

        # 更新总时长
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)


class AdjustDurationCommand(QUndoCommand):
    """调整选中音符时值"""

    def __init__(self, piano_roll, notes_data: list, delta_sec: float, parent=None):
        """
        Args:
            piano_roll: PianoRollWidget 实例
            notes_data: 选中音符数据 [{note, start, duration}, ...]
            delta_sec: 时值增量（秒，可正可负）
        """
        super().__init__(parent)
        self._piano_roll = weakref.ref(piano_roll)
        self._notes_data = notes_data
        self._delta_sec = delta_sec
        self.setText(f"Adjust Duration {delta_sec:+.3f}s")

    def redo(self):
        pr = self._piano_roll()
        if not pr:
            return

        for data in self._notes_data:
            for item in pr.notes:
                if (item.note == data["note"] and
                    abs(item.start_time - data["start"]) < 0.001 and
                    abs(item.duration - data["duration"]) < 0.001):
                    new_dur = max(0.01, item.duration + self._delta_sec)
                    item.duration = new_dur
                    break

        pr._refresh_notes()
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)

    def undo(self):
        pr = self._piano_roll()
        if not pr:
            return

        for data in self._notes_data:
            for item in pr.notes:
                if (item.note == data["note"] and
                    abs(item.start_time - data["start"]) < 0.001):
                    item.duration = data["duration"]
                    break

        pr._refresh_notes()
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)


class AdjustBarsDurationCommand(QUndoCommand):
    """调整选中小节内音符的时值（时间拉伸/压缩）

    - 选中的小节内所有音符按比例拉伸/压缩
    - 选中小节之后的所有音符整体平移
    """

    def __init__(self, piano_roll, old_notes_data: list, new_notes_data: list, parent=None):
        """
        Args:
            piano_roll: PianoRollWidget 实例
            old_notes_data: 原始音符数据 [{note, start, duration, velocity, track, channel}, ...]
            new_notes_data: 新音符数据（与 old_notes_data 一一对应）
        """
        super().__init__(parent)
        self._piano_roll = weakref.ref(piano_roll)
        self._old_notes_data = [d.copy() for d in old_notes_data]
        self._new_notes_data = [d.copy() for d in new_notes_data]
        self.setText(f"Adjust Bars Duration ({len(old_notes_data)} notes)")

    def redo(self):
        """执行/重做: 应用新的音符位置和时值"""
        self._apply_notes_data(self._old_notes_data, self._new_notes_data)

    def undo(self):
        """撤销: 恢复原始音符位置和时值"""
        self._apply_notes_data(self._new_notes_data, self._old_notes_data)

    def _apply_notes_data(self, from_data: list, to_data: list):
        """将音符从 from_data 状态更新到 to_data 状态"""
        pr = self._piano_roll()
        if not pr:
            return

        for from_d, to_d in zip(from_data, to_data):
            for item in pr.notes:
                if (item.note == from_d["note"] and
                    abs(item.start_time - from_d["start"]) < 0.001 and
                    abs(item.duration - from_d["duration"]) < 0.001):
                    # 更新到新状态
                    item.start_time = to_d["start"]
                    item.duration = to_d["duration"]
                    break

        pr._refresh_notes()
        if pr.notes:
            pr.total_duration = max(n.start_time + n.duration for n in pr.notes)