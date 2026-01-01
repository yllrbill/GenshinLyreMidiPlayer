# main.py 结构摘要

> 生成时间: 2026-01-02
> 版本: Phase 6 完成后

## 文件概览

| 指标 | 值 |
|------|-----|
| 总行数 | 2271 |
| 原始行数 | 3834 |
| 减少 | 1563 行 (-40.8%) |
| 类 | 1 (MainWindow) |
| 方法数 | 60+ |

---

## 代码结构分区

### 1. Imports (L1-75)

```
L1-28:   标准库 + PyQt6 + 第三方 (mido, pydirectinput, keyboard)
L29-37:  player 模块导入 (PlayerThread, PlayerConfig, ErrorConfig, 量化函数等)
L39-40:  ui 模块导入 (FloatingController, ROOT_CHOICES)
L41-75:  可选导入 (win32gui, fluidsynth, RegisterHotKey 热键管理)
```

**关键导入:**
```python
from player import (
    PlayerThread, PlayerConfig,
    ErrorConfig, ErrorType, DEFAULT_ERROR_TYPES, plan_errors_for_group,
    NoteEvent, midi_to_events_with_duration,
    KeyEvent, quantize_note, get_octave_shift, build_available_notes,
    calculate_bar_and_beat_duration, calculate_bar_duration,
    DIATONIC_OFFSETS, SHARP_OFFSETS, MIDI_C2, MIDI_C6,
)
from ui import FloatingController, ROOT_CHOICES
```

### 2. Helper Functions (L76-143)

| 函数 | 行 | 说明 |
|------|-----|------|
| `is_admin()` | L76-84 | 检查管理员权限 (Windows ctypes) |
| `get_best_audio_driver()` | L86-95 | 选择最佳音频驱动 (dsound/wasapi/portaudio) |
| `list_windows()` | L97-113 | 枚举可见窗口 (win32gui) |
| `load_settings_from_file()` | L115-126 | 从 JSON 加载设置 |
| `get_saved_theme()` | L128-143 | 获取保存的主题设置 |

### 3. Constants (L144-186)

| 常量组 | 行 | 内容 |
|--------|-----|------|
| 设置常量 | L144-155 | `SETTINGS_FILE`, `SETTINGS_VERSION`, `SETTINGS_*_DIR`, `GM_PROGRAM` |
| 时间常量 | L157-162 | `DEFAULT_TEMPO_US`, `DEFAULT_BPM`, `DEFAULT_BEAT_DURATION`, `DEFAULT_BAR_DURATION`, `DEFAULT_SEGMENT_BARS` |
| 预设常量 | L173-178 | `PRESET_COMBO_ITEMS`, `DEFAULT_KEYBOARD_PRESET` |

**时间常量定义:**
```python
DEFAULT_TEMPO_US = 500000       # 默认 tempo (微秒/拍) = 120 BPM
DEFAULT_BPM = 120               # 默认 BPM
DEFAULT_BEAT_DURATION = 0.5     # 默认拍时长 (秒) = 60/120
DEFAULT_BAR_DURATION = 2.0      # 默认小节时长 (秒) = 4拍 * 0.5秒
DEFAULT_SEGMENT_BARS = 8        # 8小节为一段
```

### 4. MainWindow Class (L188-2262)

#### 4.1 初始化 (L188-826)

| 方法 | 行 | 说明 |
|------|-----|------|
| `__init__` | L188-210 | 初始化状态变量、信号连接 |
| `init_ui` | L211-826 | **UI 构建核心 (615 行)** |

**init_ui 详细分区:**

| Tab | 行范围 | 内容 |
|-----|--------|------|
| Tab 1 Main | L260-590 | 文件加载、配置组、音效组、快捷错误、8小节、预设 |
| Tab 2 Keyboard | L592-620 | 键位映射显示 (21键/36键) |
| Tab 3 Shortcuts | L622-670 | 热键显示 (F5-F12) |
| Tab 4 Input Style | L672-730 | 风格参数、8小节风格设置 |
| Tab 5 Errors | L732-799 | 错误模拟设置 |

#### 4.2 语言/翻译 (L827-946)

| 方法 | 行 | 说明 |
|------|-----|------|
| `apply_language` | L827-937 | 应用 i18n 翻译到所有 UI 元素 (110 行) |
| `on_language_changed` | L939-945 | 语言切换回调 |

#### 4.3 Preset 相关 (L947-1007)

| 方法 | 行 | 说明 |
|------|-----|------|
| `on_preset_changed` | L947-953 | 主选项卡键盘预设变化 |
| `on_kb_preset_changed` | L955-961 | 键盘选项卡预设变化 |
| `_rebuild_style_combo` | L965-980 | 重建风格下拉列表 |
| `_rebuild_all_style_combos` | L982-996 | 重建所有风格下拉 |
| `_rebuild_settings_preset_combo` | L998-1007 | 重建设置预设下拉 |

#### 4.4 Input Style 方法 (L963-1195)

| 方法 | 行 | 说明 |
|------|-----|------|
| `_select_style_in_combo` | L1009-1016 | 在下拉中选择风格 |
| `_update_style_params_display` | L1018-1036 | 更新风格参数显示 |
| `on_input_style_changed` | L1038-1060 | 主设置风格变化 |
| `on_style_tab_changed` | L1062-1084 | 风格选项卡变化 |
| `on_add_custom_style` | L1086-1126 | 添加自定义风格 |
| `on_delete_custom_style` | L1128-1159 | 删除自定义风格 |
| `on_apply_style_params` | L1161-1194 | 应用风格参数 |

#### 4.5 Settings Preset 方法 (L1196-1366)

| 方法 | 行 | 说明 |
|------|-----|------|
| `on_apply_settings_preset` | L1198-1252 | 应用内置预设 (BUILTIN_PRESETS) |
| `on_import_settings` | L1254-1274 | 导入 JSON 设置 |
| `on_export_settings` | L1276-1298 | 导出 JSON 设置 |
| `on_reset_defaults` | L1300-1335 | 重置默认设置 |
| `_collect_current_settings` | L1337-1365 | 收集当前 UI 设置为 dict |
| `_apply_settings_dict` | L1367-1447 | 应用设置字典到 UI |

#### 4.6 Keyboard Display (L1449-1539)

| 方法 | 行 | 说明 |
|------|-----|------|
| `_build_keyboard_display` | L1449-1506 | 构建键盘映射网格 |
| `show_init_messages` | L1508-1527 | 显示初始化消息 |
| `append_log` | L1529-1530 | 追加日志到 QTextEdit |
| `refresh_windows` | L1532-1539 | 刷新目标窗口列表 |

#### 4.7 MIDI/Sound 方法 (L1541-1649)

| 方法 | 行 | 说明 |
|------|-----|------|
| `on_load` | L1541-1566 | 加载 MIDI 文件 |
| `on_browse_sf` | L1568-1580 | 浏览 SoundFont 文件 |
| `_on_error_enabled_changed` | L1582-1587 | 错误启用变化 |
| `_on_error_freq_changed` | L1589-1593 | 错误频率变化 |
| `_on_quick_error_enable_changed` | L1595-1604 | 快捷错误开关同步 |
| `_sync_quick_errors_to_tab5` | L1606-1622 | 同步快捷→Tab5 |
| `_sync_tab5_errors_to_quick` | L1624-1630 | 同步 Tab5→快捷 |
| `_sync_tab5_to_quick_errors` | L1632-1648 | 反向同步 (阻止递归) |

#### 4.8 Eight-Bar Style 方法 (L1650-1712)

| 方法 | 行 | 说明 |
|------|-----|------|
| `_on_eight_bar_enabled_changed` | L1652-1662 | 8小节启用变化 |
| `_apply_eight_bar_preset` | L1664-1678 | 应用8小节预设 (subtle/moderate/dramatic) |
| `_collect_eight_bar_style` | L1680-1695 | 收集8小节设置为 EightBarStyle |
| `_on_quick_eight_bar_changed` | L1697-1705 | 快捷8小节同步 |
| `_sync_eight_bar_to_quick` | L1707-1711 | 同步8小节→快捷 |

#### 4.9 Playback Control (L1713-1878)

| 方法 | 行 | 说明 |
|------|-----|------|
| `collect_cfg` | L1713-1746 | 收集 PlayerConfig (含 ErrorConfig + EightBarStyle) |
| `on_start` | L1748-1767 | 开始播放 (创建 PlayerThread) |
| `on_toggle_play_pause` | L1769-1797 | 切换播放/暂停 (F5 热键) |
| `on_stop` | L1799-1805 | 停止播放 |
| `on_pause` | L1807-1817 | 暂停/恢复 |
| `on_finished` | L1819-1824 | 播放完成回调 |
| `_on_thread_paused` | L1826-1829 | 线程暂停回调 |
| `on_octave_up` | L1831-1836 | 八度 +1 (F10) |
| `on_octave_down` | L1838-1843 | 八度 -1 (F9) |
| `on_toggle_midi_duration` | L1845-1849 | 切换 MIDI 时长模式 (F12) |
| `on_speed_up` | L1851-1856 | 速度 +0.1 (F8) |
| `on_speed_down` | L1858-1863 | 速度 -0.1 (F7) |
| `on_show_floating` | L1865-1878 | 显示/隐藏浮动控制器 |

#### 4.10 Global Hotkeys (L1880-1908)

| 方法 | 行 | 说明 |
|------|-----|------|
| `_register_global_hotkeys` | L1880-1908 | 注册 F5-F12 全局热键 (keyboard 库) |

**热键映射:**
| 热键 | 功能 |
|------|------|
| F5 | 播放/暂停/恢复 |
| F6 | 停止 |
| F7 | 速度 -0.1 |
| F8 | 速度 +0.1 |
| F9 | 八度 -1 |
| F10 | 八度 +1 |
| F11 | 打开 MIDI |
| F12 | 切换 MIDI 时长 |

#### 4.11 Settings Persistence (L1910-2134)

| 方法 | 行 | 说明 |
|------|-----|------|
| `save_settings` | L1910-1969 | 保存设置到 `lyre_settings.json` |
| `load_settings` | L1971-2133 | 从 JSON 加载设置 (含自定义风格) |

#### 4.12 Cleanup & Test (L2135-2260)

| 方法 | 行 | 说明 |
|------|-----|------|
| `closeEvent` | L2135-2162 | 关闭事件: 保存设置、清理热键、停止线程 |
| `on_test` | L2164-2168 | 测试按键 (pydirectinput) |
| `on_test_sound` | L2170-2260 | 测试 FluidSynth 声音输出 |

### 5. Main Entry (L2263-2271)

```python
def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

---

## 模块依赖关系

```
main.py (2271 行)
│
├── player/              # 播放引擎 (1316 行)
│   ├── thread.py        # PlayerThread (~600 行)
│   ├── config.py        # PlayerConfig (~50 行)
│   ├── midi_parser.py   # NoteEvent, midi_to_events_with_duration (~100 行)
│   ├── scheduler.py     # KeyEvent (~60 行)
│   ├── errors.py        # ErrorConfig, ErrorType (~80 行)
│   ├── quantize.py      # quantize_note, get_octave_shift (~150 行)
│   └── bar_utils.py     # calculate_bar_* (~50 行)
│
├── ui/                  # UI 组件 (447 行)
│   ├── floating.py      # FloatingController (~320 行)
│   └── constants.py     # ROOT_CHOICES (~10 行)
│
├── i18n/                # 国际化 (250 行)
│   ├── __init__.py      # tr(), LANG_EN, LANG_ZH
│   └── translations.py  # TRANSLATIONS dict
│
├── core/                # 核心配置 (465 行)
│   ├── config.py        # settings_manager
│   └── events.py        # EventBus, EventType
│
└── style_manager/       # 风格管理 (外部模块)
    ├── InputStyle       # 输入风格数据类
    ├── EightBarStyle    # 8小节风格数据类
    └── INPUT_STYLES     # 风格注册表
```

---

## 已提取到模块的功能

| 原 main.py 内容 | 目标模块 | 行数 |
|----------------|----------|------|
| PlayerThread (播放线程) | `player/thread.py` | ~600 |
| PlayerConfig (播放配置) | `player/config.py` | ~50 |
| NoteEvent, midi_to_events_with_duration | `player/midi_parser.py` | ~100 |
| KeyEvent (按键事件) | `player/scheduler.py` | ~60 |
| ErrorConfig, ErrorType | `player/errors.py` | ~80 |
| quantize_note, get_octave_shift, build_available_notes | `player/quantize.py` | ~150 |
| calculate_bar_*, bar utilities | `player/bar_utils.py` | ~50 |
| FloatingController (浮动窗口) | `ui/floating.py` | ~320 |
| ROOT_CHOICES (根音选择) | `ui/constants.py` | ~10 |
| i18n (tr, TRANSLATIONS) | `i18n/__init__.py` | ~250 |

**新增模块代码总计: 2478 行**

---

## 验证命令

```powershell
cd LyreAutoPlayer

# 语法检查
.venv/Scripts/python.exe -m py_compile main.py

# 测试导入
.venv/Scripts/python.exe -c "from main import MainWindow; print('MainWindow import OK')"

# 检查行数
wc -l main.py  # 预期: 2271 行

# 测试所有模块导入
.venv/Scripts/python.exe -c "from i18n import tr; from core import get_config, get_event_bus; from player import PlayerThread, PlayerConfig; from ui import FloatingController, ROOT_CHOICES; print('All modules OK')"
```

---

## 版本历史

| 日期 | 版本 | 行数 | 变更 |
|------|------|------|------|
| 2026-01-01 | Phase 1-5 | 3834 | 初始重构计划 |
| 2026-01-02 | Phase 6 | 2271 | main.py 精简 (-40.8%) |

---

*Generated: 2026-01-02*
*Task: 20260102-0251-main-modular-refactor*
