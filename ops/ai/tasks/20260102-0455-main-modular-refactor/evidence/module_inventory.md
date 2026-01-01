# Module Inventory: main.py

> Step 1 产出：盘点 main.py 功能模块与耦合点

## 文件基础信息

| 属性 | 值 |
|------|-----|
| 路径 | `LyreAutoPlayer/main.py` |
| 行数 | 3977 |
| 大小 | ~180KB |

## 现有独立模块

| 模块 | 文件 | 行数 | 职责 |
|------|------|------|------|
| input_manager | `input_manager.py` | ~800 | SendInput/扫描码输入、IME 控制、按键追踪 |
| settings_manager | `settings_manager.py` | ~400 | 设置读写、预设管理、配置持久化 |
| style_manager | `style_manager.py` | ~170 | 输入风格、8-bar 风格、风格插件系统 |
| keyboard_layout | `keyboard_layout.py` | ~210 | 21/36 键位布局定义、八度映射 |
| global_hotkey | `global_hotkey.py` | ~180 | 全局热键注册 (RegisterHotKey API) |

## main.py 内部模块边界

### 1. Imports & Constants (L1-136)

| 区域 | 行号 | 内容 |
|------|------|------|
| 标准库导入 | 1-8 | sys, os, time, heapq, random, json, dataclasses, typing |
| 内部模块导入 | 10-24 | input_manager, settings_manager, style_manager, keyboard_layout |
| 路径配置 | 26-36 | SCRIPT_DIR, BIN_DIR, DLL 路径 |
| Qt 导入 | 38-44 | PyQt6.QtCore, PyQt6.QtWidgets |
| 可选依赖 | 46-116 | mido, pydirectinput, ctypes, win32gui, fluidsynth, sounddevice, keyboard |
| 辅助函数 | 60-126 | is_admin(), get_best_audio_driver() |
| 常量 | 128-135 | GM_PROGRAM 音色映射 |

**耦合点**:
- `BIN_DIR` 需要在 FluidSynth 导入前设置
- 可选依赖有多个 try/except 块

### 2. i18n 模块 (L137-294)

| 区域 | 行号 | 内容 |
|------|------|------|
| 语言常量 | 138-139 | LANG_EN, LANG_ZH |
| 翻译字典 | 141-289 | TRANSLATIONS dict (~148 行, 101 个翻译键) |
| 翻译函数 | 291-293 | `tr(key, lang)` |

**耦合点**:
- `tr()` 被整个文件调用 (~150+ 处)
- 翻译键与 UI 组件紧耦合

**拆分难度**: 低 - 可直接提取为独立模块

### 3. 键盘布局常量 (L296-303)

| 区域 | 行号 | 内容 |
|------|------|------|
| 音阶偏移 | 297-300 | DIATONIC_OFFSETS, SHARP_OFFSETS |
| 预设引用 | 302 | 从 keyboard_layout.py 导入 |

**拆分难度**: 已部分拆分到 `keyboard_layout.py`

### 4. 错误模拟系统 (L305-655)

| 区域 | 行号 | 内容 |
|------|------|------|
| ErrorType 类 | 310-347 | 错误类型定义 (wrong_note, miss_note, extra_note, pause) |
| ErrorConfig 类 | 351-367 | 错误配置 dataclass |
| KeyEvent 类 | 373-378 | 按键事件 (priority queue) |
| 音符构建 | 380-416 | `build_available_notes()` |
| 八度移位 | 421-426 | `get_octave_shift()` |
| 量化策略 | 428-454 | `quantize_note()` (nearest/octave/lower/upper/drop) |
| MIDI 解析 | 457-499 | NoteEvent, `midi_to_events_with_duration()` |
| PlayerConfig | 503-527 | 播放配置 dataclass |
| 窗口辅助 | 530-555 | `list_windows()`, `try_focus_window()` |
| 小节计算 | 558-654 | `calculate_bar_and_beat_duration()`, `plan_errors_for_group()` |

**耦合点**:
- `PlayerConfig` 包含所有配置项 (sound, style, error, 8-bar)
- `quantize_note()` 依赖 available notes list
- 错误系统与 PlayerThread 紧耦合

**拆分难度**: 中 - 需要抽象配置模型

### 5. PlayerThread (L657-1484)

| 区域 | 行号 | 内容 |
|------|------|------|
| 信号定义 | 659-662 | log, finished, progress, paused |
| 初始化 | 664-683 | InputManager 创建、配置加载 |
| 控制方法 | 685-720 | stop(), pause(), _do_pause(), resume() |
| 播放逻辑 | 722-1484 | run() 主循环 (~760 行) |

**核心功能**:
- MIDI 事件调度 (heapq priority queue)
- 按键输入 (via InputManager)
- 音效播放 (FluidSynth)
- 8-bar 变速/节拍锁定
- 错误模拟
- IME 禁用/恢复
- 诊断日志

**耦合点**:
- 直接使用 `tr()` 进行日志本地化
- 依赖 `InputManager`, `FluidSynth`, `mido`
- 包含复杂的 8-bar 逻辑 (~200 行)
- 错误模拟逻辑内嵌 (~100 行)

**拆分难度**: 高 - 核心逻辑，需要仔细分解

### 6. FloatingController (L1487-1879)

| 区域 | 行号 | 内容 |
|------|------|------|
| UI 初始化 | 1488-1534 | 窗口标志、样式表 |
| 控件布局 | 1536-1730 | 按钮、标签、下拉框 |
| 事件处理 | 1732-1879 | 播放控制、八度调整、错误切换 |

**耦合点**:
- 持有 `main_window` 引用
- 直接调用 MainWindow 方法
- 使用 `tr()` 进行本地化

**拆分难度**: 中 - 需要事件总线解耦

### 7. MainWindow (L1882-3967)

| 区域 | 行号 | 内容 |
|------|------|------|
| 信号定义 | 1896-1904 | 全局热键信号 (9 个) |
| 初始化 | 1906-1921 | 状态变量、UI 初始化 |
| UI 构建 | 1923-2700 | Tab 面板 (~780 行) |
| 事件处理 | 2700-3600 | 按钮回调、热键处理 (~900 行) |
| 辅助方法 | 3600-3967 | 日志、测试、音效 (~370 行) |

**Tab 结构**:
1. Main (主界面): 配置、音效、快速错误
2. Keyboard (键盘): 预设、音符对照表
3. Shortcuts (快捷键): 全局热键配置
4. Input Style (输入风格): 风格参数、自定义风格
5. Errors (演奏失误): 错误类型、频率配置

**耦合点**:
- 直接创建 `PlayerThread`
- 直接创建 `FloatingController`
- 使用 `QSettings` 持久化 (与 settings_manager 重复?)
- 全局热键注册逻辑内嵌
- 所有 Tab UI 构建内嵌

**拆分难度**: 高 - 需要大量解耦

### 8. 程序入口 (L3969-3977)

```python
def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
```

**拆分难度**: 低

---

## 模块依赖图

```
                    ┌──────────────────┐
                    │     main.py      │
                    │   (3977 lines)   │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ input_manager │   │settings_manager│   │ style_manager │
│   (~800L)     │   │   (~400L)     │   │   (~170L)     │
└───────────────┘   └───────────────┘   └───────────────┘
        │                    │
        ▼                    ▼
┌───────────────┐   ┌───────────────┐
│keyboard_layout│   │ global_hotkey │
│   (~210L)     │   │   (~180L)     │
└───────────────┘   └───────────────┘
```

## 功能模块拆分建议

| 优先级 | 模块 | 来源行号 | 预计大小 | 依赖 |
|--------|------|----------|----------|------|
| P1 | i18n | L137-294 | ~160 行 | 无 |
| P1 | core/config | (抽象) | ~200 行 | settings_manager |
| P2 | player/quantize | L380-454 | ~80 行 | keyboard_layout |
| P2 | player/midi_parser | L457-499 | ~50 行 | mido |
| P2 | player/errors | L305-655 | ~350 行 | 无 |
| P3 | player/thread | L657-1484 | ~830 行 | 上述所有 |
| P3 | ui/floating | L1487-1879 | ~400 行 | events |
| P4 | ui/tabs/* | L1923-2700 | ~780 行 | i18n, events |
| P4 | core/hotkeys | (内嵌) | ~100 行 | global_hotkey |

## 跨模块耦合点汇总

| 耦合类型 | 位置 | 当前方式 | 建议解耦方式 |
|----------|------|----------|--------------|
| 翻译调用 | 全局 | 直接调用 `tr()` | i18n 单例模块 |
| 配置传递 | PlayerConfig | dataclass 整体传递 | 分离配置域 (player/sound/error) |
| UI ↔ Player | MainWindow | 直接持有 thread 引用 | 事件总线 |
| Floating ↔ Main | FloatingController | 持有 main_window 引用 | 事件总线 |
| 热键 ↔ UI | MainWindow | Qt 信号 + keyboard 库 | 热键管理器服务 |
| 设置持久化 | MainWindow | QSettings + settings_manager | 统一使用 settings_manager |

---

*生成时间: 2026-01-02*
*Plan Step 1 完成*
