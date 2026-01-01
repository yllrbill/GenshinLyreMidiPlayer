"""
Keyboard Layout - 键盘布局抽象模块

支持 21 键（全音）和 36 键（半音）布局，
提供 MIDI 音符到按键的映射。

Author: LyreAutoPlayer Refactor
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


@dataclass
class KeyboardLayout:
    """键盘布局定义"""
    name: str
    display_name: str
    note_count: int

    # 音符到按键的映射
    # key: MIDI音符偏移(相对于root), value: 按键字符
    note_to_key: Dict[int, str]

    # 按键到音符偏移的反向映射（自动构建）
    key_to_note: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        # 构建反向映射
        self.key_to_note = {v.lower(): k for k, v in self.note_to_key.items()}

    def get_key(self, midi_note: int, root: int) -> Optional[str]:
        """获取MIDI音符对应的按键"""
        offset = midi_note - root
        return self.note_to_key.get(offset)

    def get_note(self, key: str, root: int) -> Optional[int]:
        """获取按键对应的MIDI音符"""
        offset = self.key_to_note.get(key.lower())
        if offset is not None:
            return root + offset
        return None

    def get_available_notes(self, root: int) -> List[Tuple[int, str]]:
        """获取所有可用的(MIDI音符, 按键)对，按音符排序"""
        result = [(root + offset, key) for offset, key in self.note_to_key.items()]
        return sorted(result, key=lambda x: x[0])

    def get_range(self, root: int) -> Tuple[int, int]:
        """获取布局的音符范围 (min_note, max_note)"""
        offsets = list(self.note_to_key.keys())
        if not offsets:
            return (root, root)
        return (root + min(offsets), root + max(offsets))

    def contains_note(self, midi_note: int, root: int) -> bool:
        """检查音符是否在布局范围内"""
        offset = midi_note - root
        return offset in self.note_to_key

    def get_all_keys(self) -> List[str]:
        """获取所有按键（小写），按音符顺序排序"""
        sorted_items = sorted(self.note_to_key.items(), key=lambda x: x[0])
        return [key.lower() for _, key in sorted_items]


# ============== 预设布局 ==============

# 21键布局 (仅白键/全音)
# 三个八度区：低音区(ZXCVBNM)、中音区(ASDFGHJ)、高音区(QWERTYU)
LAYOUT_21KEY = KeyboardLayout(
    name="21-key",
    display_name="21键 (全音)",
    note_count=21,
    note_to_key={
        # 低音区 (ZXCVBNM) - root - 12 到 root - 1
        # C3(-12), D3(-10), E3(-8), F3(-7), G3(-5), A3(-3), B3(-1)
        -12: 'z', -10: 'x', -8: 'c', -7: 'v', -5: 'b', -3: 'n', -1: 'm',
        # 中音区 (ASDFGHJ) - root 到 root + 11
        # C4(0), D4(2), E4(4), F4(5), G4(7), A4(9), B4(11)
        0: 'a', 2: 's', 4: 'd', 5: 'f', 7: 'g', 9: 'h', 11: 'j',
        # 高音区 (QWERTYU) - root + 12 到 root + 23
        # C5(12), D5(14), E5(16), F5(17), G5(19), A5(21), B5(23)
        12: 'q', 14: 'w', 16: 'e', 17: 'r', 19: 't', 21: 'y', 23: 'u',
    }
)

# 36键布局 (白键+黑键/半音)
LAYOUT_36KEY = KeyboardLayout(
    name="36-key",
    display_name="36键 (全音+半音)",
    note_count=36,
    note_to_key={
        # 低音区白键 (,./IOP[)
        # C3(-12), D3(-10), E3(-8), F3(-7), G3(-5), A3(-3), B3(-1)
        -12: ',', -10: '.', -8: '/', -7: 'i', -5: 'o', -3: 'p', -1: '[',
        # 低音区黑键 (L:90-)
        # C#3(-11), D#3(-9), F#3(-6), G#3(-4), A#3(-2)
        -11: 'l', -9: ';', -6: '9', -4: '0', -2: '-',
        # 中音区白键 (ZXCVBNM)
        # C4(0), D4(2), E4(4), F4(5), G4(7), A4(9), B4(11)
        0: 'z', 2: 'x', 4: 'c', 5: 'v', 7: 'b', 9: 'n', 11: 'm',
        # 中音区黑键 (SDGHJ)
        # C#4(1), D#4(3), F#4(6), G#4(8), A#4(10)
        1: 's', 3: 'd', 6: 'g', 8: 'h', 10: 'j',
        # 高音区白键 (QWERTYU)
        # C5(12), D5(14), E5(16), F5(17), G5(19), A5(21), B5(23)
        12: 'q', 14: 'w', 16: 'e', 17: 'r', 19: 't', 21: 'y', 23: 'u',
        # 高音区黑键 (23567)
        # C#5(13), D#5(15), F#5(18), G#5(20), A#5(22)
        13: '2', 15: '3', 18: '5', 20: '6', 22: '7',
    }
)


# 布局注册表
KEYBOARD_LAYOUTS: Dict[str, KeyboardLayout] = {
    "21-key": LAYOUT_21KEY,
    "36-key": LAYOUT_36KEY,
}


def get_layout(name: str) -> Optional[KeyboardLayout]:
    """获取指定名称的布局"""
    return KEYBOARD_LAYOUTS.get(name)


def get_layout_names() -> List[str]:
    """获取所有可用布局名称"""
    return list(KEYBOARD_LAYOUTS.keys())


def get_default_layout() -> KeyboardLayout:
    """获取默认布局"""
    return LAYOUT_21KEY


# ============== 辅助函数 ==============

def find_nearest_note(midi_note: int, root: int, layout: KeyboardLayout) -> Optional[Tuple[int, str]]:
    """
    查找最接近的可用音符

    Returns:
        (nearest_midi_note, key) 或 None
    """
    if layout.contains_note(midi_note, root):
        key = layout.get_key(midi_note, root)
        return (midi_note, key) if key else None

    # 搜索附近的音符
    available = layout.get_available_notes(root)
    if not available:
        return None

    # 二分查找最近的
    best_note, best_key = available[0]
    best_diff = abs(midi_note - best_note)

    for note, key in available:
        diff = abs(midi_note - note)
        if diff < best_diff:
            best_diff = diff
            best_note = note
            best_key = key

    return (best_note, best_key)


# ============== Legacy Preset Format (for UI compatibility) ==============

# Legacy format expected by main.py UI code:
# {
#   "high": ["Q", "W", "E", "R", "T", "Y", "U"],       # white keys for high octave
#   "high_sharp": ["2", "3", "5", "6", "7"],           # black keys for high octave (36-key only)
#   "mid": [...],
#   "low": [...],
#   ...
# }

def get_preset_dict(layout_name: str) -> Dict[str, List[str]]:
    """
    获取布局的 UI 预设字典格式（用于显示和编辑）

    Returns:
        Dict with keys like "high", "mid", "low" (and "_sharp" variants for 36-key)
    """
    if layout_name == "21-key":
        return {
            "high": list("QWERTYU"),
            "mid":  list("ASDFGHJ"),
            "low":  list("ZXCVBNM"),
        }
    elif layout_name == "36-key":
        return {
            "high":       list("QWERTYU"),
            "high_sharp": list("23567"),
            "mid":        list("ZXCVBNM"),
            "mid_sharp":  list("SDGHJ"),
            "low":        list(",./IOP["),
            "low_sharp":  list("L:90-"),  # Do#=L Re#=: Fa#=9 Sol#=0 La#=-
        }
    else:
        # Fallback to 21-key
        return get_preset_dict("21-key")


# Backward-compatible constants (deprecated, use get_preset_dict instead)
PRESET_21KEY = get_preset_dict("21-key")
PRESET_36KEY = get_preset_dict("36-key")


def quantize_to_layout(
    midi_notes: List[int],
    root: int,
    layout: KeyboardLayout,
    allow_octave_shift: bool = True,
    max_octave_shift: int = 2
) -> List[Tuple[int, Optional[str], int]]:
    """
    将一组 MIDI 音符量化到指定布局

    Args:
        midi_notes: 原始 MIDI 音符列表
        root: 根音
        layout: 目标布局
        allow_octave_shift: 是否允许八度移位
        max_octave_shift: 最大八度移位范围

    Returns:
        List[(original_note, key_or_none, octave_shift)]
    """
    result = []
    for note in midi_notes:
        # 首先尝试直接匹配
        key = layout.get_key(note, root)
        if key:
            result.append((note, key, 0))
            continue

        # 尝试八度移位
        if allow_octave_shift:
            for shift in range(-max_octave_shift, max_octave_shift + 1):
                if shift == 0:
                    continue
                shifted = note + shift * 12
                key = layout.get_key(shifted, root)
                if key:
                    result.append((note, key, shift))
                    break
            else:
                # 没有找到
                result.append((note, None, 0))
        else:
            result.append((note, None, 0))

    return result
