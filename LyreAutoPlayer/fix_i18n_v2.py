# -*- coding: utf-8 -*-
"""Fix corrupted Chinese translations in main.py - Version 2"""

import re

# Correct translations (from main.md and manual translation)
CORRECT_ZH = {
    "window_title": "里拉琴自动演奏器 (21/36键)",
    "load_midi": "加载MIDI",
    "no_file": "未加载文件",
    "config": "配置",
    "middle_row_do": "中行 Do (根音)",
    "octave_shift": "八度移位",
    "transpose": "移调 (半音)",
    "accidental_policy": "变音策略",
    "speed": "速度",
    "press_duration": "按键时长 (ms)",
    "use_midi_duration": "使用MIDI音符时值",
    "keyboard_preset": "键盘预设",
    "countdown": "倒计时 (秒)",
    "target_window": "目标窗口",
    "refresh": "刷新",
    "sound_group": "音效 (本地播放)",
    "play_sound": "播放音效",
    "enable_sound": "启用本地音效",
    "soundfont": "音色库",
    "no_sf2": "(未选择 .sf2)",
    "browse": "浏览...",
    "instrument": "乐器",
    "velocity": "力度",
    "start": "开始",
    "stop": "停止",
    "test_keys": "测试按键 (ASDFGHJ)",
    "test_sound": "测试音效",
    "language": "语言",
    "no_midi": "无MIDI",
    "load_midi_first": "请先加载MIDI文件。",
    "starting": "启动中...",
    "stopping": "停止中...",
    "test_pressing": "测试: 按下 ASDFGHJ",
    "none_manual": "(无 / 手动切换)",
    "pywin32_unavail": "(pywin32不可用; 手动切换)",
    "tab_main": "主设置",
    "tab_keyboard": "键位设置",
    "current_preset": "当前预设",
    "octave_high": "高音区",
    "octave_mid": "中音区",
    "octave_low": "低音区",
    "note_names": "音符",
    "key_binding": "按键",
    "tab_shortcuts": "快捷键",
    "shortcut_start": "开始播放",
    "shortcut_stop": "停止播放",
    "shortcut_octave_up": "升八度",
    "shortcut_octave_down": "降八度",
    "shortcut_open_midi": "打开MIDI文件",
    "shortcut_toggle_duration": "切换智能时值",
    "shortcut_speed_up": "加速",
    "shortcut_speed_down": "减速",
    "global_hotkey_note": "* 全局快捷键 (F键) - 游戏中也能使用",
    "floating_title": "钢琴控制器",
    "show_floating": "控制面板",
    "hide_floating": "隐藏",
    "input_style": "输入风格",
    "style_mechanical": "机械",
    "style_natural": "自然",
    "style_expressive": "富有感情",
    "style_aggressive": "激进",
    "style_legato": "连奏",
    "style_staccato": "断奏",
    "style_swing": "摇摆",
    "style_rubato": "自由速度",
    "style_ballad": "抒情",
    "style_lazy": "慵懒",
    "style_rushed": "急促",
    "pause": "暂停",
    "resume": "继续",
    "tab_input_style": "输入风格",
    "style_preset": "风格预设",
    "style_custom": "自定义风格",
    "timing_offset": "时间偏移 (ms)",
    "timing_offset_min": "最小",
    "timing_offset_max": "最大",
    "chord_stagger": "和弦分散 (ms)",
    "duration_variation": "时长变化 (%)",
    "add_style": "添加风格",
    "delete_style": "删除",
    "style_name": "风格名称",
    "style_description": "描述",
    "apply_style": "应用",
    "style_params": "风格参数",
    "current_style": "当前风格",
    "tab_errors": "错误设置",
    "enable_errors": "启用随机错误",
    "errors_per_8bars": "每8小节错误数",
    "error_types": "错误类型",
    "error_wrong_note": "错音（相邻）",
    "error_miss_note": "漏音（跳过）",
    "error_extra_note": "重音（多按）",
    "error_pause": "断音（中断）",
    "pause_duration": "中断时长 (ms)",
    "pause_min": "最小",
    "pause_max": "最大",
    "errors": "错误",
    "quick_error_select": "快捷错误选择",
    "settings_presets": "设置预设",
    "preset_select": "选择预设",
    "preset_apply": "应用",
    "preset_fast_precise": "快速精确",
    "preset_natural_flow": "自然流畅",
    "preset_stable_compat": "稳定兼容",
    "preset_expressive_human": "富有感情",
    "preset_21key_default": "21键默认",
    "preset_36key_default": "36键默认",
    "import_settings": "导入...",
    "export_settings": "导出...",
    "reset_defaults": "恢复默认",
    "import_success": "设置导入成功",
    "import_failed": "设置导入失败",
    "export_success": "设置导出成功",
    "export_failed": "设置导出失败",
    "preset_applied": "预设已应用",
    "reset_confirm": "确定恢复默认设置？",
    "eight_bar_style": "八小节风格",
    "eight_bar_enabled": "启用八小节变奏",
    "eight_bar_mode": "变奏模式",
    "mode_warp": "节奏伸缩",
    "mode_beat_lock": "拍点锁定",
    "eight_bar_pattern": "选择模式",
    "pattern_skip3": "过三选一",
    "pattern_skip2": "过二选一",
    "pattern_skip1": "过一选一",
    "speed_variation": "速度变化",
    "timing_variation": "时间变化",
    "duration_variation_8bar": "时长变化",
    "variation_range": "范围 (%)",
    "eight_bar_preset": "预设",
    "preset_subtle": "轻微",
    "preset_moderate": "中等",
    "preset_dramatic": "强烈",
    "eight_bar_active": "[八节]",
    "show_indicator": "显示指示器",
}

def fix_line(line):
    """Fix a single line with corrupted LANG_ZH."""
    # Pattern for single-line dict entries: "key": {LANG_EN: "...", LANG_ZH: "..."}
    # The corrupted part is after LANG_ZH: " and before the closing
    for key, correct_zh in CORRECT_ZH.items():
        # Match pattern: "key": {LANG_EN: "...", LANG_ZH: "
        pattern = rf'^(\s*"{key}": \{{LANG_EN: "[^"]*", LANG_ZH: ").*$'
        match = re.match(pattern, line.rstrip())
        if match:
            # Check if the line ends with }, or }
            if line.rstrip().endswith('},'):
                return f'{match.group(1)}{correct_zh}"}},\n'
            elif line.rstrip().endswith('}'):
                return f'{match.group(1)}{correct_zh}"}}\n'
            else:
                # Line doesn't end properly, fix it
                return f'{match.group(1)}{correct_zh}"}},\n'
    return line

def fix_main_py():
    with open('main.py', 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Fix LANG_ZH = line
        if 'LANG_ZH = "' in line:
            line = 'LANG_ZH = "简体中文"\n'

        # Fix single-line LANG_ZH entries
        if 'LANG_ZH: "' in line and not 'LANG_ZH: "' + '"' in line:
            # Check if it's a single-line entry that needs fixing
            line = fix_line(line)

        fixed_lines.append(line)
        i += 1

    with open('main.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print("Fixed main.py (v2)")

if __name__ == '__main__':
    fix_main_py()
