# -*- coding: utf-8 -*-
"""
Translation dictionary for LyreAutoPlayer.

This module contains all UI strings in multiple languages.
"""

# Language constants
LANG_EN = "English"
LANG_ZH = "简体中文"

# All supported languages
SUPPORTED_LANGUAGES = [LANG_EN, LANG_ZH]

# Default language
DEFAULT_LANGUAGE = LANG_EN

TRANSLATIONS = {
    "window_title": {
        LANG_EN: "Lyre Auto Player (21/36 keys)",
        LANG_ZH: "里拉琴自动演奏器 (21/36键)",
    },
    "load_midi": {LANG_EN: "Load MIDI", LANG_ZH: "加载MIDI"},
    "no_file": {LANG_EN: "No file loaded.", LANG_ZH: "未加载文件"},
    "config": {LANG_EN: "Config", LANG_ZH: "配置"},
    "middle_row_do": {LANG_EN: "Middle-row Do (root)", LANG_ZH: "中行 Do (根音)"},
    "octave_shift": {LANG_EN: "Octave Shift", LANG_ZH: "八度移位"},
    "octave_range": {LANG_EN: "Octave Range (MIDI)", LANG_ZH: "音域阈值 (MIDI)"},
    "octave_range_mode": {LANG_EN: "Octave Range Mode", LANG_ZH: "音域阈值模式"},
    "octave_range_auto": {LANG_EN: "Auto", LANG_ZH: "自动"},
    "octave_range_hint": {
        LANG_EN: "Octave shift threshold (e.g., C2=36, C6=84)",
        LANG_ZH: "八度移位阈值（例如 C2=36，C6=84）",
    },
    "transpose": {LANG_EN: "Transpose (semitones)", LANG_ZH: "移调 (半音)"},
    "accidental_policy": {LANG_EN: "Accidental policy", LANG_ZH: "变音策略"},
    "enable_accidental_policy": {LANG_EN: "Enable accidental policy", LANG_ZH: "启用变音策略"},
    "enable_accidental_policy_hint": {
        LANG_EN: "When off, only play in-range notes without octave/lower/upper mapping.",
        LANG_ZH: "关闭后仅播放音域内原始音符，不做八度/上下邻近映射。",
    },
    "speed": {LANG_EN: "Speed", LANG_ZH: "速度"},
    "press_duration": {LANG_EN: "Press duration (ms)", LANG_ZH: "按键时长 (ms)"},
    "use_midi_duration": {LANG_EN: "Use MIDI note duration", LANG_ZH: "使用MIDI音符时值"},
    "keyboard_preset": {LANG_EN: "Keyboard preset", LANG_ZH: "键盘预设"},
    "countdown": {LANG_EN: "Countdown (sec)", LANG_ZH: "倒计时 (秒)"},
    "target_window": {LANG_EN: "Target window", LANG_ZH: "目标窗口"},
    "target_window_hint": {
        LANG_EN: "Note: The target window MUST be in foreground (visible and focused).\n"
                 "SendInput cannot send keys to minimized or background windows.\n"
                 "Use the countdown to switch to the game window before playback starts.",
        LANG_ZH: "注意：目标窗口必须在前台（可见且获得焦点）。\n"
                 "SendInput 无法向最小化或后台窗口发送按键。\n"
                 "请在倒计时期间切换到游戏窗口。",
    },
    "refresh": {LANG_EN: "Refresh", LANG_ZH: "刷新"},
    "sound_group": {LANG_EN: "Sound (Local Playback)", LANG_ZH: "音效 (本地播放)"},
    "play_sound": {LANG_EN: "Play Sound", LANG_ZH: "播放音效"},
    "enable_sound": {LANG_EN: "Enable local sound", LANG_ZH: "启用本地音效"},
    "soundfont": {LANG_EN: "SoundFont", LANG_ZH: "音色库"},
    "no_sf2": {LANG_EN: "(No .sf2 selected)", LANG_ZH: "(未选择 .sf2)"},
    "browse": {LANG_EN: "Browse...", LANG_ZH: "浏览..."},
    "instrument": {LANG_EN: "Instrument", LANG_ZH: "乐器"},
    "velocity": {LANG_EN: "Velocity", LANG_ZH: "力度"},
    "start": {LANG_EN: "Start", LANG_ZH: "开始"},
    "stop": {LANG_EN: "Stop", LANG_ZH: "停止"},
    "test_keys": {LANG_EN: "Test Keys (ASDFGHJ)", LANG_ZH: "测试按键 (ASDFGHJ)"},
    "test_sound": {LANG_EN: "Test Sound", LANG_ZH: "测试音效"},
    "language": {LANG_EN: "Language", LANG_ZH: "语言"},
    "admin_ok": {
        LANG_EN: "[OK] Admin: True - Running as administrator (can send input to all windows)",
        LANG_ZH: "[OK] Admin: True - 以管理员身份运行（可向所有窗口发送输入）",
    },
    "admin_warn": {
        LANG_EN: "[WARN] Admin: False - Some windows may not receive input",
        LANG_ZH: "[WARN] Admin: False - 部分窗口可能无法接收输入",
    },
    "uipi_hint": {
        LANG_EN: "Hint: Run as administrator for full compatibility.",
        LANG_ZH: "提示：以管理员身份运行可获得完整兼容性。",
    },
    "ready_msg": {
        LANG_EN: "Ready. Load a MIDI file to start.",
        LANG_ZH: "就绪。请加载 MIDI 文件开始。",
    },
    "sound_hint": {
        LANG_EN: "Tip: Enable 'Play Sound' for local audio preview.",
        LANG_ZH: "提示：启用「播放音效」可本地预览音频。",
    },
    # Tab names
    "tab_main": {LANG_EN: "Main", LANG_ZH: "主界面"},
    "tab_keyboard": {LANG_EN: "Keyboard", LANG_ZH: "键盘"},
    "tab_shortcuts": {LANG_EN: "Shortcuts", LANG_ZH: "快捷键"},
    "tab_input_style": {LANG_EN: "Input Style", LANG_ZH: "输入风格"},
    "tab_errors": {LANG_EN: "Errors", LANG_ZH: "演奏失误"},
    # Input style
    "input_style": {LANG_EN: "Input Style", LANG_ZH: "输入风格"},
    "current_style": {LANG_EN: "Current Style", LANG_ZH: "当前风格"},
    "style_params": {LANG_EN: "Style Parameters", LANG_ZH: "风格参数"},
    "timing_offset": {LANG_EN: "Timing Offset", LANG_ZH: "时序偏移"},
    "timing_offset_min": {LANG_EN: "Min", LANG_ZH: "最小"},
    "timing_offset_max": {LANG_EN: "Max", LANG_ZH: "最大"},
    "chord_stagger": {LANG_EN: "Chord Stagger", LANG_ZH: "和弦分散"},
    "duration_variation": {LANG_EN: "Duration Variation", LANG_ZH: "时值变化"},
    "style_custom": {LANG_EN: "Custom Style", LANG_ZH: "自定义风格"},
    "style_name": {LANG_EN: "Name", LANG_ZH: "名称"},
    "style_description": {LANG_EN: "Description", LANG_ZH: "描述"},
    "add_style": {LANG_EN: "Add", LANG_ZH: "添加"},
    "delete_style": {LANG_EN: "Delete", LANG_ZH: "删除"},
    "apply_style": {LANG_EN: "Apply", LANG_ZH: "应用"},
    # Eight-bar style
    "eight_bar_style": {LANG_EN: "8-Bar Style", LANG_ZH: "八小节风格"},
    "eight_bar_enabled": {LANG_EN: "Enable 8-Bar Style", LANG_ZH: "启用八小节风格"},
    "eight_bar_mode": {LANG_EN: "Mode", LANG_ZH: "模式"},
    "mode_warp": {LANG_EN: "Tempo Warp", LANG_ZH: "速度变化"},
    "mode_beat_lock": {LANG_EN: "Beat-Lock", LANG_ZH: "节拍锁定"},
    "eight_bar_pattern": {LANG_EN: "Pattern", LANG_ZH: "选择模式"},
    "eight_bar_clamp": {LANG_EN: "Global Clamp", LANG_ZH: "全局上限/下限锁"},
    "pattern_skip3": {LANG_EN: "Skip 3, Pick 1", LANG_ZH: "过三选一"},
    "pattern_skip2": {LANG_EN: "Skip 2, Pick 1", LANG_ZH: "过二选一"},
    "pattern_skip1": {LANG_EN: "Skip 1, Pick 1", LANG_ZH: "过一选一"},
    "pattern_continuous": {LANG_EN: "Continuous", LANG_ZH: "持续变化"},
    "speed_variation": {LANG_EN: "Speed Variation", LANG_ZH: "速度变化"},
    "timing_variation": {LANG_EN: "Timing Variation", LANG_ZH: "时序变化"},
    "duration_variation_8bar": {LANG_EN: "Duration Variation", LANG_ZH: "时值变化"},
    "eight_bar_preset": {LANG_EN: "Presets", LANG_ZH: "预设"},
    "preset_subtle": {LANG_EN: "Subtle", LANG_ZH: "细微"},
    "preset_moderate": {LANG_EN: "Moderate", LANG_ZH: "适中"},
    "preset_dramatic": {LANG_EN: "Dramatic", LANG_ZH: "明显"},
    "show_indicator": {LANG_EN: "Show Indicator", LANG_ZH: "显示指示器"},
    # Error simulation
    "errors": {LANG_EN: "Errors", LANG_ZH: "演奏失误"},
    "enable_errors": {LANG_EN: "Enable Error Simulation", LANG_ZH: "启用失误模拟"},
    "errors_per_8bars": {LANG_EN: "Errors per 8 bars", LANG_ZH: "每8小节失误数"},
    "error_types": {LANG_EN: "Error Types", LANG_ZH: "失误类型"},
    "error_wrong_note": {LANG_EN: "Wrong Note", LANG_ZH: "错音"},
    "error_miss_note": {LANG_EN: "Miss Note", LANG_ZH: "漏音"},
    "error_extra_note": {LANG_EN: "Extra Note", LANG_ZH: "多音"},
    "error_pause": {LANG_EN: "Pause", LANG_ZH: "断音"},
    "pause_duration": {LANG_EN: "Pause Duration (ms)", LANG_ZH: "断音时长 (ms)"},
    "quick_error_select": {LANG_EN: "Quick Error Select", LANG_ZH: "快速失误选择"},
    # Settings presets
    "settings_presets": {LANG_EN: "Settings Presets", LANG_ZH: "设置预设"},
    "preset_select": {LANG_EN: "Select Preset", LANG_ZH: "选择预设"},
    "preset_apply": {LANG_EN: "Apply", LANG_ZH: "应用"},
    "preset_applied": {LANG_EN: "Preset applied", LANG_ZH: "预设已应用"},
    "import_settings": {LANG_EN: "Import", LANG_ZH: "导入"},
    "export_settings": {LANG_EN: "Export", LANG_ZH: "导出"},
    "reset_defaults": {LANG_EN: "Reset", LANG_ZH: "重置"},
    # Keyboard tab
    "current_preset": {LANG_EN: "Current Preset", LANG_ZH: "当前预设"},
    # Shortcuts tab
    "global_hotkey_note": {
        LANG_EN: "Note: Global hotkeys work even when the window is not focused.",
        LANG_ZH: "注意：全局快捷键在窗口未聚焦时也可使用。",
    },
    # Floating controller
    "show_floating": {LANG_EN: "Show Floating", LANG_ZH: "显示悬浮窗"},
    "floating_title": {LANG_EN: "Floating Panel", LANG_ZH: "悬浮面板"},
    # Playback states
    "resume": {LANG_EN: "Resume", LANG_ZH: "继续"},
    "pause": {LANG_EN: "Pause", LANG_ZH: "暂停"},
    "starting": {LANG_EN: "Starting...", LANG_ZH: "启动中..."},
    "stopping": {LANG_EN: "Stopping...", LANG_ZH: "停止中..."},
    # Messages
    "pywin32_unavail": {LANG_EN: "(pywin32 unavailable)", LANG_ZH: "(pywin32 不可用)"},
    "none_manual": {LANG_EN: "(None / Manual)", LANG_ZH: "(无/手动)"},
    "no_midi": {LANG_EN: "No MIDI", LANG_ZH: "无MIDI"},
    "load_midi_first": {LANG_EN: "Please load a MIDI file first.", LANG_ZH: "请先加载 MIDI 文件。"},
    "test_pressing": {LANG_EN: "Testing keys...", LANG_ZH: "测试按键中..."},
    # Shortcuts tab
    "shortcut_start": {LANG_EN: "Start/Resume", LANG_ZH: "开始/继续"},
    "shortcut_stop": {LANG_EN: "Stop", LANG_ZH: "停止"},
    "shortcut_speed_down": {LANG_EN: "Speed -5%", LANG_ZH: "速度-5%"},
    "shortcut_speed_up": {LANG_EN: "Speed +5%", LANG_ZH: "速度+5%"},
    "shortcut_octave_down": {LANG_EN: "Octave Down", LANG_ZH: "降八度"},
    "shortcut_octave_up": {LANG_EN: "Octave Up", LANG_ZH: "升八度"},
    "shortcut_open_midi": {LANG_EN: "Open MIDI", LANG_ZH: "打开MIDI"},
    "shortcut_toggle_duration": {LANG_EN: "Toggle Duration", LANG_ZH: "切换时值"},
    # Range labels (Phase 2 i18n fix)
    "range_min": {LANG_EN: "Min", LANG_ZH: "最小"},
    "range_max": {LANG_EN: "Max", LANG_ZH: "最大"},
    "range_to": {LANG_EN: "~", LANG_ZH: "~"},
    # Placeholder texts
    "placeholder_style_name": {LANG_EN: "custom1", LANG_ZH: "自定义1"},
    "placeholder_style_desc": {LANG_EN: "My custom style", LANG_ZH: "我的自定义风格"},
    # Diagnostics window
    "diag_window_title": {LANG_EN: "Input Diagnostics", LANG_ZH: "输入诊断"},
    "diag_controls": {LANG_EN: "Controls", LANG_ZH: "控制"},
    "diag_filter": {LANG_EN: "Filter:", LANG_ZH: "过滤:"},
    "diag_filter_all": {LANG_EN: "All Keys", LANG_ZH: "全部按键"},
    "diag_filter_non_f": {LANG_EN: "Non-F Keys", LANG_ZH: "非F键"},
    "diag_filter_non_fn": {LANG_EN: "Non-Function Keys", LANG_ZH: "非功能键"},
    "diag_auto_scroll": {LANG_EN: "Auto Scroll", LANG_ZH: "自动滚动"},
    "diag_clear": {LANG_EN: "Clear", LANG_ZH: "清空"},
    "diag_copy": {LANG_EN: "Copy All", LANG_ZH: "复制全部"},
    "diag_clear_on_stop": {LANG_EN: "Clear on Stop", LANG_ZH: "停止时清空"},
    "diag_status_ready": {LANG_EN: "Ready", LANG_ZH: "就绪"},
    "diag_status_count": {LANG_EN: "{count} entries", LANG_ZH: "{count} 条记录"},
    "diag_copied": {LANG_EN: "Copied to clipboard", LANG_ZH: "已复制到剪贴板"},
    "show_diagnostics": {LANG_EN: "Diagnostics", LANG_ZH: "诊断"},
    # Editor window
    "original_file": {LANG_EN: "Original (原始文件)", LANG_ZH: "原始文件"},
    "select_version": {LANG_EN: "Select Version", LANG_ZH: "选择版本"},
    "select_version_prompt": {LANG_EN: "Select version to open:", LANG_ZH: "选择要打开的版本:"},
    # Strict Mode / Auto-Pause
    "strict_mode_group": {LANG_EN: "Strict Mode / Auto-Pause", LANG_ZH: "严格跟谱 / 自动暂停"},
    "strict_mode": {LANG_EN: "Strict Mode", LANG_ZH: "严格跟谱"},
    "strict_mode_hint": {
        LANG_EN: "Forces mechanical input, speed=1.0, MIDI duration, disables errors/8-bar",
        LANG_ZH: "强制机械输入、速度=1.0、使用MIDI时值，禁用失误/8小节风格",
    },
    "strict_midi_timing": {LANG_EN: "Strict MIDI Timing", LANG_ZH: "严格 MIDI 时序"},
    "strict_midi_timing_hint": {
        LANG_EN: "Disable humanization (timing offset/stagger/duration variation) while keeping speed settings",
        LANG_ZH: "禁用人性化抖动（时序偏移/分解/时值变化），保留速度设置",
    },
    "pause_every_bars": {LANG_EN: "Auto Pause", LANG_ZH: "自动暂停"},
    "auto_resume_countdown": {LANG_EN: "Resume Countdown", LANG_ZH: "恢复倒计时"},
    "late_drop": {LANG_EN: "Late Drop", LANG_ZH: "延迟丢弃"},
    "late_drop_hint": {
        LANG_EN: "Skip key events that are too far behind schedule (prevents dense chord pile-up)",
        LANG_ZH: "跳过超时过久的按键事件（防止密集和弦堆积）",
    },
    "enable_diagnostics": {LANG_EN: "Enable Diagnostics", LANG_ZH: "启用诊断"},
    "enable_diagnostics_hint": {
        LANG_EN: "Write playback trace logs (expected/actual) for debugging",
        LANG_ZH: "写入播放验证日志（期望/实际）用于排查问题",
    },
    "press_f5_continue": {LANG_EN: "Press F5 to continue", LANG_ZH: "按 F5 继续"},
    # Editor Key List Widget
    "key_sequence": {LANG_EN: "Key Sequence", LANG_ZH: "按键序列"},
    "show_key_list": {LANG_EN: "Key List", LANG_ZH: "按键列表"},
    # Editor controls
    "editor_octave_shift": {LANG_EN: "Octave", LANG_ZH: "八度"},
    "editor_input_style": {LANG_EN: "Style", LANG_ZH: "风格"},
    "editor_pause_bars": {LANG_EN: "Pause Bars", LANG_ZH: "暂停间隔"},
    "editor_auto_resume": {LANG_EN: "Auto Resume", LANG_ZH: "自动恢复"},
    # Editor humanization / input style jitter
    "apply_jitter": {LANG_EN: "Apply Input Style Jitter (Humanize)", LANG_ZH: "应用输入风格抖动 (人性化)"},
    "apply_jitter_tooltip": {
        LANG_EN: "Apply timing jitter from selected input style to notes",
        LANG_ZH: "将所选输入风格的时序抖动应用到音符",
    },
    "style_not_found": {LANG_EN: "Style not found", LANG_ZH: "风格未找到"},
    "style_not_found_msg": {LANG_EN: "Style '{name}' not found in registry.", LANG_ZH: "风格 '{name}' 未在注册表中找到。"},
    "style_no_variation": {
        LANG_EN: "Style '{name}' has no timing variation (mechanical).\nChoose a different style for humanization.",
        LANG_ZH: "风格 '{name}' 没有时序变化（机械）。\n请选择其他风格进行人性化处理。",
    },
    "no_notes_to_jitter": {LANG_EN: "No notes to apply jitter to.", LANG_ZH: "没有可应用抖动的音符。"},
    "jitter_applied": {
        LANG_EN: "Applied '{style}' jitter to {count} {scope} notes (timing: {min_offset}~{max_offset}ms, duration: ±{duration_pct:.0f}%)",
        LANG_ZH: "已将 '{style}' 抖动应用到 {count} 个{scope}音符 (时序: {min_offset}~{max_offset}ms, 时值: ±{duration_pct:.0f}%)",
    },
    "scope_selected": {LANG_EN: "selected", LANG_ZH: "选中的"},
    "scope_all": {LANG_EN: "all", LANG_ZH: "全部"},
    # Duration adjustment
    "duration_label": {LANG_EN: " Duration: ", LANG_ZH: " 时值: "},
    "duration_tooltip": {
        LANG_EN: "Duration adjustment in milliseconds (step: 50ms)",
        LANG_ZH: "时值调整（毫秒，步进 50ms）",
    },
    "apply_duration": {LANG_EN: "Apply", LANG_ZH: "应用"},
    "apply_duration_tooltip": {
        LANG_EN: "Apply duration change to selected notes",
        LANG_ZH: "将时值变化应用到选中音符",
    },
    # Bar duration adjustment
    "bar_duration_label": {LANG_EN: " Bar: ", LANG_ZH: " 小节: "},
    "bar_duration_tooltip": {
        LANG_EN: "Time stretch/compress selected bars (ms, Ctrl+drag timeline to select)",
        LANG_ZH: "拉伸/压缩选中小节的时值（毫秒，Ctrl+拖拽时间轴选择小节）",
    },
    "apply_bar_duration": {LANG_EN: "Stretch", LANG_ZH: "拉伸"},
    "apply_bar_duration_tooltip": {
        LANG_EN: "Apply time stretch to notes in selected bars",
        LANG_ZH: "将时值变化应用到选中小节内的音符",
    },
    "no_bars_selected_title": {LANG_EN: "Bar Duration", LANG_ZH: "小节时长"},
    "no_bars_selected_msg": {
        LANG_EN: "No bars selected.\nCtrl+drag on the timeline to select bars.",
        LANG_ZH: "未选中任何小节。\n在时间轴上按住 Ctrl 拖拽选择小节。",
    },
}
