# Project Summary

> 自动生成于 2026-01-02 12:30，供后续分析定位使用

## 1. 基础信息

| 项目 | 值 |
|------|-----|
| 项目根目录 | `D:\dw11\piano\LyreAutoPlayer` |
| Git 分支 | `main` |
| 主要语言 | Python 3.x |
| 框架 | PyQt6 (GUI) + mido (MIDI) + FluidSynth (音频) |
| 文件总数 | 52 (排除 .venv, bin, lib, 资源文件) |
| 代码行数 | ~5000+ (核心模块估算) |
| 版本 | v3.0 |

### 最近提交

```
16e8339 chore: add ops/ai skeleton and claude commands
1a400a0 Fix "Merge nearby notes" incorrectly removing notes
53c9fa7 Fix "Use system setting" theme not saving properly
90fac19 Fix inconsistent theme colors (#30)
72b2115 Change FontIcon control to fix missing icons (#28)
```

---

## 2. 目录结构

```
LyreAutoPlayer/
├── main.py                 # 主入口 (GUI + 播放逻辑) ~2300 行
├── input_manager.py        # 输入系统 (SendInput 后端) ~900 行
├── settings_manager.py     # 设置管理 + 预设系统
├── keyboard_layout.py      # 键位布局定义 (21/36 键)
├── style_manager.py        # 演奏风格管理
├── global_hotkey.py        # 全局热键 (F5-F12)
│
├── core/                   # 核心模块
│   ├── __init__.py
│   ├── config.py           # ConfigManager 配置管理
│   └── events.py           # EventBus 事件总线
│
├── player/                 # 播放器模块
│   ├── __init__.py
│   ├── thread.py           # PlayerThread 播放线程 ~1000 行
│   ├── config.py           # PlayerConfig
│   ├── quantize.py         # 音符量化策略
│   ├── midi_parser.py      # MIDI 解析
│   ├── errors.py           # 错误模拟
│   ├── bar_utils.py        # 小节/节拍计算
│   └── scheduler.py        # 事件调度
│
├── ui/                     # UI 模块
│   ├── __init__.py
│   ├── floating.py         # FloatingController 悬浮控制器
│   └── constants.py        # UI 常量
│
├── i18n/                   # 国际化
│   ├── __init__.py
│   └── translations.py     # 翻译字典 (EN/ZH)
│
├── styles/                 # 演奏风格插件系统
│   ├── __init__.py
│   ├── registry.py         # StyleRegistry
│   ├── loader.py           # 插件加载器
│   └── plugins/            # 可扩展插件目录
│       ├── arpeggio_soft.py
│       ├── classical_upbeat.py
│       ├── dreamy.py
│       └── tiktok_rhythm.py
│
├── bin/                    # FluidSynth 二进制
│   ├── fluidsynth.exe
│   └── libfluidsynth-3.dll
│
├── midi/                   # MIDI 文件存放
├── backup/                 # 旧版本备份
├── .venv/                  # Python 虚拟环境
├── FluidR3_GM.sf2          # GM SoundFont (~148MB)
└── requirements.txt        # Python 依赖
```

---

## 3. 入口文件

| 入口 | 路径 | 说明 |
|------|------|------|
| **主入口** | `main.py` | GUI 应用入口，包含 MainWindow 类和 main() 函数 |
| 启动脚本 | `启动.bat` / `启动.ps1` | Windows 快速启动 |
| 管理员启动 | `RunAsAdmin.bat` / `RunAsAdmin.vbs` | 以管理员权限启动 |

### 入口函数

```python
# main.py:2263
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

---

## 4. 核心模块

| 模块 | 路径 | 职责 | 主要类/函数 |
|------|------|------|-------------|
| **MainWindow** | `main.py:188` | GUI 主窗口，整合所有功能 | `MainWindow` 类 |
| **PlayerThread** | `player/thread.py` | MIDI 播放线程控制 | `PlayerThread(QThread)` |
| **InputManager** | `input_manager.py:473` | 键盘输入管理 | `InputManager`, `SendInputBackend` |
| **GlobalHotkeyManager** | `global_hotkey.py:51` | 全局热键注册 | `GlobalHotkeyManager` |
| **ConfigManager** | `core/config.py:53` | 配置持久化 | `ConfigManager` |
| **EventBus** | `core/events.py:73` | 事件发布/订阅 | `EventBus`, `EventType` |
| **StyleRegistry** | `styles/registry.py` | 演奏风格注册 | `StyleRegistry`, `InputStyle` |
| **KeyboardLayout** | `keyboard_layout.py:15` | 键位布局定义 | `KeyboardLayout` |

### 模块依赖关系

```
MainWindow
├── PlayerThread        # 播放控制
│   ├── InputManager    # 发送键盘输入
│   ├── midi_parser     # MIDI 解析
│   └── quantize        # 音符量化
├── GlobalHotkeyManager # F5-F12 热键
├── SettingsManager     # 配置持久化
├── FloatingController  # 悬浮窗
└── FluidSynth          # 本地音效预览 (可选)
```

---

## 5. 关键依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **PyQt6** | >=6.6 | GUI 框架 |
| **mido** | >=1.3 | MIDI 文件解析 |
| **pydirectinput** | >=1.0 | DirectInput 输入模拟 (备选后端) |
| **pywin32** | >=306 | Windows API (窗口管理) |
| **pyfluidsynth** | >=1.3 | FluidSynth Python 绑定 |
| **sounddevice** | >=0.4 | 音频设备枚举 |

### 系统依赖

| 依赖 | 路径 | 用途 |
|------|------|------|
| FluidSynth | `bin/fluidsynth.exe` | 音效合成引擎 |
| SoundFont | `FluidR3_GM.sf2` | GM 音色库 |

---

## 6. 配置文件

| 文件 | 用途 |
|------|------|
| `settings.json` | 应用配置 (键位、风格、速度等) |
| `requirements.txt` | Python 依赖声明 |
| `README.md` | 项目文档 |

### settings.json 结构

```json
{
  "key_mode": "21-key",
  "input_style": "natural",
  "speed": 1.0,
  "octave_shift": 0,
  "root_note": "C",
  "use_long_press": true,
  "press_ms": 30,
  "release_ms": 10,
  "diagnostics": false,
  "error_rate": 0.0
}
```

---

## 7. 构建/运行/测试

| 操作 | 命令 | 来源 |
|------|------|------|
| 创建虚拟环境 | `python -m venv .venv` | README |
| 激活环境 | `.venv\Scripts\activate` | README |
| 安装依赖 | `pip install -r requirements.txt` | README |
| **运行程序** | `python main.py` | README |
| 管理员运行 | `RunAsAdmin.bat` 或右键以管理员运行 | README |
| 快速测试 | `python test_regression.py --quick` | README |
| 完整测试 | `python test_regression.py` | README |
| 输入测试 | `python test_input_manager.py --interactive` | README |

---

## 8. 数据流概要

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              数据流                                      │
└─────────────────────────────────────────────────────────────────────────┘

[输入]                      [处理]                        [输出]

MIDI 文件 ──────────────┐                               ┌── pydirectinput
  (*.mid)               │                               │   (游戏键盘模拟)
                        ▼                               │
               ┌────────────────┐                       │
               │  mido.parse()  │                       │
               └───────┬────────┘                       │
                       │                                │
                       ▼                                │
               ┌────────────────┐    ┌───────────────┐ │
               │ NoteEvent 列表 │───▶│ PlayerThread  │─┤
               └────────────────┘    │               │ │
                                     │ - 量化音符    │ │
               ┌────────────────┐    │ - 应用风格    │ │
               │ KeyboardLayout │───▶│ - 错误模拟    │ │
               │ (21/36 键映射) │    │ - 事件调度    │ │
               └────────────────┘    └───────┬───────┘ │
                                             │         │
               ┌────────────────┐            │         │
               │  InputStyle    │────────────┤         │
               │ (演奏风格参数) │            │         ▼
               └────────────────┘            │  ┌──────────────┐
                                             ├─▶│ InputManager │
               ┌────────────────┐            │  │ (SendInput)  │
               │  ErrorConfig   │────────────┘  └──────────────┘
               │ (错误模拟配置) │                       │
               └────────────────┘                       ▼
                                             [游戏窗口] 键盘事件

                                             ┌── FluidSynth
                                             │   (本地音效预览)
                                             │
                                             ▼
                                      [音频输出] 播放预览
```

### 线程模型

```
主线程 (Qt Event Loop)
├── UI 渲染 (MainWindow)
├── 热键信号处理 (pyqtSignal)
└── 设置管理

PlayerThread (QThread)
├── 事件队列 (heapq 优先队列)
├── 风格应用 (timing_offset, stagger)
├── 错误模拟 (miss, wrong_key, timing_error)
└── InputManager 调用

FocusMonitor (后台线程)
├── 100ms 轮询窗口焦点
└── 失焦时自动释放按键

GlobalHotkeyManager (后台线程)
├── Windows 消息循环
└── RegisterHotKey API
```

---

## 9. 扩展点

| 扩展点 | 位置 | 说明 |
|--------|------|------|
| **演奏风格插件** | `styles/plugins/*.py` | 添加 .py 文件自动加载，实现 `InputStyle` dataclass |
| **输入后端** | `input_manager.py` | 继承 `InputBackend` 抽象类，实现 `press`/`release` |
| **键盘布局** | `keyboard_layout.py` | 添加新的 `KeyboardLayout` 实例 |
| **事件订阅** | `core/events.py` | 使用 `EventBus.subscribe()` 订阅事件 |
| **预设系统** | `settings_manager.py` | 在 `BUILTIN_PRESETS` 添加预设 |

### 添加自定义演奏风格

```python
# styles/plugins/my_style.py
from styles.registry import InputStyle

MY_STYLE = InputStyle(
    name="my_custom",
    description="My Custom Style",
    timing_offset_ms=10,
    stagger_ms=5,
    duration_variation=0.1,
    velocity_variation=0.1,
    swing_ratio=1.0,
    articulation="normal",
)
```

---

## 10. 风险点

| 类型 | 位置 | 说明 |
|------|------|------|
| **管理员权限** | `main.py:76` | 需要管理员权限才能发送键盘事件到游戏 |
| **IME 兼容** | `input_manager.py:132` | 禁用/启用输入法可能影响系统状态 |
| **焦点丢失** | `input_manager.py` | 需要 FocusMonitor 防止按键卡住 |
| **热键冲突** | `global_hotkey.py` | F5-F12 可能与其他应用冲突 |
| **大文件** | `FluidR3_GM.sf2` | ~148MB SoundFont 文件 |
| **游戏反作弊** | - | 某些游戏可能检测 SendInput |

### 无 TODO/FIXME

扫描结果：项目中没有发现 TODO、FIXME、HACK 或 XXX 注释。

---

## 11. 测试覆盖

| 测试文件 | 用途 |
|----------|------|
| `test_regression.py` | 回归测试套件 |
| `test_input_manager.py` | 输入管理器测试 |
| `test_hotkey_simple.py` | 热键简单测试 |
| `test_hotkey_interactive.py` | 热键交互测试 |
| `diagnose_input.py` | 输入诊断工具 |
| `diagnose_hotkey.py` | 热键诊断工具 |

---

## 12. 快速定位索引

### 按功能定位

| 功能 | 文件 | 行号/类 |
|------|------|---------|
| GUI 主窗口 | `main.py` | `MainWindow:188` |
| MIDI 播放 | `player/thread.py` | `PlayerThread` |
| 键盘输入 | `input_manager.py` | `InputManager:473` |
| 全局热键 | `global_hotkey.py` | `GlobalHotkeyManager:51` |
| 键位布局 | `keyboard_layout.py` | `KeyboardLayout:15` |
| 演奏风格 | `style_manager.py` | `InputStyle`, `EightBarStyle:86` |
| 配置管理 | `core/config.py` | `ConfigManager:53` |
| 事件总线 | `core/events.py` | `EventBus:73` |
| 国际化 | `i18n/__init__.py` | `tr()`, `set_language()` |

### 按问题定位

| 问题 | 相关文件 |
|------|----------|
| 按键不触发 | `input_manager.py`, `diagnose_input.py` |
| 热键无响应 | `global_hotkey.py`, `diagnose_hotkey.py` |
| 音符丢失 | `player/thread.py`, `player/quantize.py` |
| 音效不播放 | `main.py` (FluidSynth 初始化) |
| 设置不保存 | `settings_manager.py`, `core/config.py` |
| 风格无效 | `style_manager.py`, `styles/` |

---

*Generated by /ai-project-sum*
*Version: 1.0*
