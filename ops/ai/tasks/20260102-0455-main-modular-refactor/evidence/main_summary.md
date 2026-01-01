# main.py 全面分类摘要

> 生成时间: 2026-01-02
> 文件: `LyreAutoPlayer/main.py`
> 总行数: 3825 行

---

## 一、文件结构总览

| 区域 | 行号范围 | 内容 | 行数 |
|------|----------|------|------|
| 导入与初始化 | 1-156 | 标准库/第三方库/可选依赖导入 | 156 |
| 数据类与工具 | 157-461 | ErrorType/Config/Note/计算函数 | 305 |
| PlayerThread | 506-1332 | 播放引擎主线程 | 827 |
| FloatingController | 1336-1728 | 浮动控制面板 UI | 393 |
| 常量定义 | 1730-1742 | ROOT_CHOICES 等 | 13 |
| MainWindow | 1744-3815 | 主窗口 GUI | 2072 |
| 程序入口 | 3817-3825 | main() 函数 | 9 |

---

## 二、详细分类

### 2.1 导入与初始化 (L1-156)

#### 标准库 (L1-8)
```python
sys, os, time, heapq, random, json, typing, dataclasses
```

#### 内部模块 (L10-24)
| 模块 | 导入内容 |
|------|----------|
| `input_manager` | InputManager, press_key, release_key 等 |
| `settings_manager` | SettingsManager, SETTINGS_FILE 等 |
| `style_manager` | InputStyle, EightBarStyle, get_style 等 |
| `keyboard_layout` | PRESET_21KEY, PRESET_36KEY |
| `global_hotkey` | GlobalHotkeyManager |

#### Qt 导入 (L38-44)
```python
PyQt6.QtCore: Qt, QThread, pyqtSignal, QSettings
PyQt6.QtWidgets: QWidget, QTabWidget, QVBoxLayout, ...
```

#### 可选依赖 (L46-116)
| 依赖 | 用途 | 降级处理 |
|------|------|----------|
| mido | MIDI 文件解析 | 无法播放 MIDI |
| pydirectinput | 键盘模拟 | 备用方案 |
| win32gui | 窗口聚焦 | 无自动聚焦 |
| fluidsynth | 音频预览 | 静音模式 |
| keyboard | 全局热键 | 仅窗口内热键 |

#### 辅助函数 (L60-126)
| 函数 | 行号 | 用途 |
|------|------|------|
| `is_admin()` | 60-68 | 检测管理员权限 |
| `get_best_audio_driver()` | 108-126 | 选择最佳音频驱动 |

#### 常量定义 (L128-156)
| 常量 | 内容 |
|------|------|
| `GM_PROGRAM` | GM MIDI 乐器映射表 (128 种) |
| `SETTINGS_*` | 设置键名常量 |

---

### 2.2 数据类与工具函数 (L157-504)

#### ErrorType (L157-194)
错误类型定义类，包含:
- `wrong_note` - 弹错音符
- `miss_note` - 漏弹
- `extra_note` - 多弹
- `pause` - 停顿

#### ErrorConfig (L197-227)
```python
@dataclass
class ErrorConfig:
    enabled: bool
    errors_per_8bars: int  # 每8小节错误数
    wrong_note: bool
    miss_note: bool
    extra_note: bool
    pause_error: bool
    pause_min_ms: int
    pause_max_ms: int
```

#### KeyEvent (L229-241)
优先级队列用的按键事件:
```python
@dataclass(order=True)
class KeyEvent:
    time: float
    priority: int
    action: str  # 'down' | 'up'
    key: str
```

#### 音符处理函数 (L243-303)
| 函数 | 行号 | 用途 |
|------|------|------|
| `build_available_notes()` | 243-263 | 构建可用音符集 |
| `get_octave_shift()` | 265-270 | 获取八度偏移 |
| `quantize_note()` | 272-303 | 量化策略 (nearest/octave/lower/upper/drop) |

#### NoteEvent & MIDI解析 (L306-348)
| 函数/类 | 行号 | 用途 |
|---------|------|------|
| `NoteEvent` | 306-310 | 音符事件数据类 |
| `midi_to_events_with_duration()` | 313-348 | MIDI → NoteEvent 列表 |

#### PlayerConfig (L350-376)
播放配置数据类，包含所有播放参数:
- 音符设置: root_mid_do, octave_shift, transpose
- 播放设置: speed, press_ms, countdown_sec
- 声音设置: play_sound, soundfont_path, instrument, velocity
- 输入风格: input_style
- 错误模拟: error_config
- 8小节变化: eight_bar_style

#### 窗口辅助函数 (L379-403)
| 函数 | 行号 | 用途 |
|------|------|------|
| `list_windows()` | 379-391 | 枚举所有窗口 |
| `try_focus_window()` | 394-403 | 尝试聚焦窗口 |

#### 小节计算函数 (L406-461)
| 函数 | 行号 | 用途 |
|------|------|------|
| `calculate_bar_and_beat_duration()` | 406-449 | 从 MIDI 计算小节/拍时长 |
| `plan_errors_for_group()` | 452-504 | 规划一组8小节的错误 |

---

### 2.3 PlayerThread (L506-1332)

播放引擎主线程类，继承 `QThread`。

#### 信号定义 (L508-511)
| 信号 | 用途 |
|------|------|
| `log` | 日志输出 |
| `finished` | 播放完成 |
| `progress` | 播放进度 |
| `paused` | 暂停状态 |

#### 初始化 (L513-560)
- 创建 InputManager
- 加载配置
- 初始化音效系统 (FluidSynth)
- 构建可用音符集

#### 控制方法 (L562-610)
| 方法 | 行号 | 用途 |
|------|------|------|
| `stop()` | 562-564 | 停止播放 |
| `pause()` | 566-576 | 请求暂停 (小节末) |
| `resume()` | 578-587 | 恢复播放 |
| `is_paused()` | 589-590 | 是否已暂停 |
| `is_pause_pending()` | 592-593 | 是否等待暂停 |
| `_do_pause()` | 595-610 | 执行暂停逻辑 |

#### run() 主循环 (L612-1332)
核心播放逻辑，包含:

**倒计时阶段** (L630-660)
- 播放倒计时音效
- 等待用户准备

**初始化阶段** (L662-750)
- 计算小节/拍时长
- 初始化8小节变化参数
- 规划初始错误

**主事件循环** (L752-1200)
```
while running:
  1. 检查暂停请求
  2. 处理 heapq 事件队列
  3. 应用输入风格 (timing offset)
  4. 处理8小节边界
     - 计算新的速度/时值变化
     - 重新规划错误
  5. 执行按键事件
  6. 播放音效 (如开启)
  7. 处理错误模拟
```

**清理阶段** (L1200-1332)
- 释放 InputManager
- 关闭 FluidSynth
- 恢复 IME 状态

---

### 2.4 FloatingController (L1336-1728)

浮动控制面板，继承 `QWidget`。

#### UI 组件 (L1380-1580)
| 组件 | 用途 |
|------|------|
| `btn_play_pause` | 播放/暂停按钮 |
| `btn_stop` | 停止按钮 |
| `cmb_octave` | 八度选择下拉框 |
| `chk_errors` | 错误模拟开关 |
| `sp_error_freq` | 错误频率调节 |
| `chk_eight_bar` | 8小节变化开关 |
| `lbl_status` | 状态标签 |

#### 同步方法 (L1582-1680)
| 方法 | 用途 |
|------|------|
| `_sync_from_main()` | 从主窗口同步设置 |
| `sync_error_settings()` | 同步错误设置 |
| `sync_eight_bar_enabled()` | 同步8小节开关 |
| `update_playback_state()` | 更新播放状态显示 |

#### 事件处理 (L1682-1728)
| 方法 | 用途 |
|------|------|
| `_on_play_pause()` | 播放/暂停切换 |
| `_on_stop()` | 停止播放 |
| `_on_octave_changed()` | 八度变化 |
| `_on_error_toggle()` | 错误开关切换 |

---

### 2.5 MainWindow (L1744-3815)

主窗口类，继承 `QWidget`。

#### 信号定义 (L1746-1756)
全局热键信号 (9个):
```python
sig_toggle_play_pause, sig_stop, sig_speed_up, sig_speed_down,
sig_octave_up, sig_octave_down, sig_open_midi, sig_toggle_duration,
sig_show_floating
```

#### 初始化 (L1758-1820)
- 设置窗口标题/大小
- 加载语言设置
- 初始化状态变量
- 连接信号槽

#### Tab 面板结构

**Tab 1: Main Settings (L1850-2100)**
| 控件组 | 内容 |
|--------|------|
| MIDI 文件选择 | 文件选择器、SoundFont 选择 |
| 基础设置 | 语言、根音、八度、速度 |
| 播放选项 | 按键时长、倒计时、窗口目标 |
| 快捷错误开关 | 错误模拟快捷复选框 |
| 控制按钮 | Start/Stop/Pause |
| 日志区域 | 滚动文本框 |

**Tab 2: Keyboard Settings (L2102-2250)**
| 控件组 | 内容 |
|--------|------|
| 预设选择 | 21-key / 36-key |
| 键盘映射网格 | 可编辑的按键映射表 |

**Tab 3: Shortcuts (L2252-2400)**
| 控件组 | 内容 |
|--------|------|
| 热键设置 | F5-F12 全局热键 |
| 热键说明 | 功能对照表 |

**Tab 4: Input Style (L2402-2700)**
| 控件组 | 内容 |
|--------|------|
| 风格选择 | 内置/自定义风格下拉框 |
| 风格参数 | timing offset, stagger, duration variation |
| 8小节变化 | 模式/选择模式/速度范围/时值范围 |
| 预设按钮 | Beginner/Intermediate/Advanced |

**Tab 5: Error Settings (L2702-2900)**
| 控件组 | 内容 |
|--------|------|
| 错误开关 | 全局开关、频率设置 |
| 错误类型 | wrong/miss/extra/pause 复选框 |
| 暂停设置 | 最小/最大暂停时长 |

#### 核心方法分组

**UI 构建方法** (L1850-2900)
| 方法 | 行号 | 用途 |
|------|------|------|
| `init_ui()` | 1850-1870 | 创建 Tab 容器 |
| `_create_main_tab()` | 1872-2100 | 构建 Main Tab |
| `_create_keyboard_tab()` | 2102-2250 | 构建 Keyboard Tab |
| `_create_shortcuts_tab()` | 2252-2400 | 构建 Shortcuts Tab |
| `_create_input_style_tab()` | 2402-2700 | 构建 Input Style Tab |
| `_create_errors_tab()` | 2702-2900 | 构建 Error Tab |

**设置管理方法** (L2902-3000)
| 方法 | 行号 | 用途 |
|------|------|------|
| `on_preset_changed()` | 2902-2920 | 预设变更处理 |
| `on_apply_settings_preset()` | 2935-2970 | 应用设置预设 |
| `on_import_settings()` | 2972-3000 | 导入设置 |
| `on_export_settings()` | 3002-3030 | 导出设置 |
| `_collect_current_settings()` | 3032-3100 | 收集当前设置 |
| `_apply_settings_dict()` | 3102-3200 | 应用设置字典 |

**键盘显示方法** (L3003-3060)
| 方法 | 行号 | 用途 |
|------|------|------|
| `_build_keyboard_display()` | 3003-3060 | 构建键盘映射网格 |

**日志与初始化** (L3062-3082)
| 方法 | 行号 | 用途 |
|------|------|------|
| `show_init_messages()` | 3062-3082 | 显示启动消息 |
| `append_log()` | 3083-3084 | 追加日志 |
| `refresh_windows()` | 3086-3093 | 刷新窗口列表 |

**文件操作** (L3095-3134)
| 方法 | 行号 | 用途 |
|------|------|------|
| `on_load()` | 3095-3120 | 加载 MIDI 文件 |
| `on_browse_sf()` | 3122-3134 | 浏览 SoundFont |

**错误同步方法** (L3136-3202)
| 方法 | 行号 | 用途 |
|------|------|------|
| `_on_error_enabled_changed()` | 3136-3141 | 错误开关变更 |
| `_on_error_freq_changed()` | 3143-3147 | 错误频率变更 |
| `_sync_quick_errors_to_tab5()` | 3160-3176 | Tab1 → Tab5 同步 |
| `_sync_tab5_to_quick_errors()` | 3186-3202 | Tab5 → Tab1 同步 |

**8小节方法** (L3204-3266)
| 方法 | 行号 | 用途 |
|------|------|------|
| `_on_eight_bar_enabled_changed()` | 3206-3216 | 8小节开关变更 |
| `_apply_eight_bar_preset()` | 3218-3232 | 应用8小节预设 |
| `_collect_eight_bar_style()` | 3234-3249 | 收集8小节设置 |
| `_on_quick_eight_bar_changed()` | 3251-3259 | 快捷开关变更 |

**播放控制** (L3267-3383)
| 方法 | 行号 | 用途 |
|------|------|------|
| `collect_cfg()` | 3267-3300 | 收集播放配置 |
| `on_start()` | 3302-3321 | 开始播放 |
| `on_toggle_play_pause()` | 3323-3351 | 切换播放/暂停 |
| `on_stop()` | 3353-3359 | 停止播放 |
| `on_pause()` | 3361-3371 | 暂停/恢复 |
| `on_finished()` | 3373-3378 | 播放完成处理 |

**快捷键处理** (L3385-3432)
| 方法 | 行号 | 用途 |
|------|------|------|
| `on_octave_up()` | 3385-3390 | 八度上调 |
| `on_octave_down()` | 3392-3397 | 八度下调 |
| `on_toggle_midi_duration()` | 3399-3403 | 切换 MIDI 时长模式 |
| `on_speed_up()` | 3405-3410 | 加速 |
| `on_speed_down()` | 3412-3417 | 减速 |
| `on_show_floating()` | 3419-3432 | 显示浮动面板 |

**全局热键** (L3434-3462)
| 方法 | 行号 | 用途 |
|------|------|------|
| `_register_global_hotkeys()` | 3434-3462 | 注册 F5-F12 热键 |

**设置持久化** (L3464-3688)
| 方法 | 行号 | 用途 |
|------|------|------|
| `save_settings()` | 3464-3523 | 保存设置到 JSON |
| `load_settings()` | 3525-3688 | 从 JSON 加载设置 |

**窗口事件** (L3689-3716)
| 方法 | 行号 | 用途 |
|------|------|------|
| `closeEvent()` | 3689-3716 | 窗口关闭清理 |

**测试方法** (L3718-3815)
| 方法 | 行号 | 用途 |
|------|------|------|
| `on_test()` | 3718-3722 | 测试按键 |
| `on_test_sound()` | 3724-3815 | 测试 FluidSynth 音效 |

---

### 2.6 程序入口 (L3817-3825)

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

## 三、模块依赖关系

```
main.py
├── input_manager.py     # 键盘输入管理
├── settings_manager.py  # 设置持久化
├── style_manager.py     # 输入风格/8小节风格
├── keyboard_layout.py   # 键盘布局定义
├── global_hotkey.py     # 全局热键 (RegisterHotKey)
│
├── [PyQt6]              # GUI 框架
├── [mido]               # MIDI 解析
├── [pydirectinput]      # 键盘模拟
├── [fluidsynth]         # 音频合成
├── [keyboard]           # 全局热键 (备选)
└── [win32gui]           # 窗口管理
```

---

## 四、重复代码统计 (参见 dedup_plan.md)

| 类型 | 出现次数 | 可节省行数 |
|------|----------|-----------|
| UI 控件创建 (QSpinBox/QComboBox) | 33+ 处 | ~100 行 |
| setValue 初始化/加载 | 4+ 处 | ~50 行 |
| 时间常量 (tempo/beat/bar) | 9 处 | ~20 行 |
| i18n 批量更新 | 38+ 处 | ~30 行 |
| 日志前缀 | 24+ 处 | ~10 行 |
| **总计** | - | **~200-250 行** |

---

## 五、拆分建议优先级

| 优先级 | 模块 | 来源行号 | 预计大小 | 依赖 |
|--------|------|----------|----------|------|
| **P1** | i18n | 已拆分 | ~250 行 | 无 |
| **P1** | core/config | 已拆分 | ~200 行 | settings_manager |
| **P1** | core/events | 已拆分 | ~100 行 | 无 |
| **P2** | player/ | 已拆分 | ~1300 行 | 上述所有 |
| **P3** | ui/floating | 已拆分 | ~400 行 | events |
| **P4** | ui/tabs/* | 待拆分 | ~780 行 | i18n, events |

---

*生成工具: Claude Code*
*基于: main.py 全文扫描*
