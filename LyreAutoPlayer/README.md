# LyreAutoPlayer

自动演奏器 - 支持 21/36 键模式，兼容 DirectX 游戏。

## 功能特点

- **游戏兼容性**: 使用 SendInput + 扫描码，支持 DirectX/DirectInput 游戏
- **双键位模式**: 21 键（全音）和 36 键（半音）布局
- **长按支持**: 真实的 KeyDown/KeyUp 控制，支持延音
- **10 种演奏风格**: mechanical, natural, expressive, aggressive, legato, staccato, swing, rubato, ballad, lazy
- **人性化模拟**: 时间偏移、和弦分解、时值变化、可选错误模拟
- **本地音效**: 内置 FluidSynth 预览（可选）
- **全局热键**: F5-F12 控制，游戏内也能使用

## 快速开始

### 1. 安装依赖

```powershell
cd LyreAutoPlayer
python -m venv .venv
.venv\Scripts\activate
pip install PyQt6 mido keyboard pydirectinput
# 可选: pip install pyfluidsynth sounddevice pywin32
```

### 2. 运行程序

```powershell
# 推荐：以管理员身份运行 PowerShell
.venv\Scripts\python.exe main.py
```

### 3. 基本使用

1. 点击 "Load MIDI" 加载 MIDI 文件
2. 选择目标窗口（游戏窗口）
3. 设置键位模式（21-key 或 36-key）
4. 点击 "Start" 或按 F5
5. 在倒计时期间切换到游戏

## 键位模式

### 21 键模式（全音）

适合只有白键的乐器（如原神风琴）。

| 区域 | 键位 | 音符 |
|------|------|------|
| 低音区 | Z X C V B N M | C3 D3 E3 F3 G3 A3 B3 |
| 中音区 | A S D F G H J | C4 D4 E4 F4 G4 A4 B4 |
| 高音区 | Q W E R T Y U | C5 D5 E5 F5 G5 A5 B5 |

### 36 键模式（半音）

适合有黑键的乐器（如某些游戏的全音阶乐器）。

| 区域 | 白键 | 黑键 |
|------|------|------|
| 低音区 | , . / I O P [ | L ; 9 0 - |
| 中音区 | Z X C V B N M | S D G H J |
| 高音区 | Q W E R T Y U | 2 3 5 6 7 |

## 演奏风格

| 风格 | 描述 | 适用场景 |
|------|------|----------|
| mechanical | 精确机械 | 高速乐曲、需要精准触发 |
| natural | 自然流畅 | 日常演奏 |
| expressive | 富有感情 | 抒情曲目 |
| aggressive | 激进有力 | 节奏感强的曲目 |
| legato | 连贯延音 | 柔和的旋律 |
| staccato | 断奏短促 | 跳跃感的曲目 |
| swing | 爵士摇摆 | 爵士风格 |
| rubato | 自由速度 | 古典浪漫 |
| ballad | 慢速抒情 | 情歌 |
| lazy | 慵懒放松 | 轻松曲风 |

### 验证风格生效

启用诊断模式后，日志会显示：
```
Input style: natural
```

风格参数影响：
- **timing_offset_ms**: 每个音符的随机时间偏移
- **stagger_ms**: 和弦分解时间（琶音效果）
- **duration_variation**: 音符时值变化百分比

## 全局热键

| 热键 | 功能 |
|------|------|
| F5 | 开始播放 |
| F6 | 停止播放 |
| F7 | 降低速度 |
| F8 | 提高速度 |
| F9 | 降低八度 |
| F10 | 提高八度 |
| F11 | 打开 MIDI |
| F12 | 切换时值模式 |

## 配置说明

### 设置文件

设置保存在 `settings.json`，包含：
- 键位模式
- 演奏风格
- 速度和时值
- 错误模拟参数
- 输入管理器参数

### 预设系统

内置 6 个预设：
- **快速精准**: 最低延迟
- **自然流畅**: 人性化
- **稳定兼容**: 最大兼容性
- **富有感情**: 最大人性化
- **21键默认**: 21 键优化
- **36键默认**: 36 键优化

### 导入/导出

- 导出: 设置 → 导出到文件
- 导入: 设置 → 从文件导入

## 故障排查

### 游戏内按键不触发

1. **检查管理员权限**
   ```powershell
   # 以管理员身份运行
   Start-Process powershell -Verb RunAs
   ```

2. **检查诊断输出**
   - 启用 "Enable diagnostics"
   - 查看日志中的 `[Input] Backend: SendInputBackend`
   - 确认 `failed_press=0`

3. **检查目标窗口**
   - 确保选择了正确的游戏窗口
   - 在倒计时期间切换到游戏

4. **尝试稳定兼容模式**
   - 使用 "稳定兼容" 预设
   - 增加 press_ms 到 50+

### 按键卡住

程序有多重保护：
- 焦点丢失自动释放
- 停止时自动释放
- 程序退出时自动释放

如果仍有卡键：
```powershell
# 重启程序
# 或手动按一下卡住的键释放
```

### 音符丢失

1. 降低速度（Speed < 1.0）
2. 增加 press_ms
3. 使用 "稳定兼容" 预设

## 开发者信息

### 运行测试

```powershell
# 快速测试
python test_regression.py --quick

# 完整测试
python test_regression.py

# 输入系统测试
python test_input_manager.py --interactive
```

### 核心模块

| 模块 | 功能 |
|------|------|
| `main.py` | 主程序入口、UI 容器 |
| `core/` | 核心模块 |
| `core/config.py` | 配置管理、settings_manager 封装 |
| `core/events.py` | 事件总线 (EventBus + EventType) |
| `i18n/` | 国际化模块 |
| `i18n/__init__.py` | tr() 翻译函数、语言切换 |
| `i18n/translations.py` | 中英文翻译字典 |
| `player/` | 播放引擎模块 |
| `player/thread.py` | PlayerThread 播放线程 |
| `player/config.py` | PlayerConfig 播放配置 |
| `player/quantize.py` | 量化策略 |
| `player/midi_parser.py` | MIDI 解析、NoteEvent |
| `player/scheduler.py` | 事件调度、KeyEvent |
| `player/errors.py` | 错误模拟 (ErrorConfig, ErrorType) |
| `player/bar_utils.py` | 小节/节拍计算工具 |
| `ui/` | UI 模块 |
| `ui/floating.py` | FloatingController 浮动控制器 |
| `ui/constants.py` | UI 常量 (ROOT_CHOICES) |
| `input_manager.py` | 输入系统（SendInput 后端） |
| `keyboard_layout.py` | 键位布局定义 |
| `settings_manager.py` | 设置管理、预设、验证 |
| `style_manager.py` | 演奏风格、8-bar 管理 |

### 架构说明

```
LyreAutoPlayer/
├── main.py              # 主程序入口、UI 容器 (~1960 行)
├── core/                # 核心模块
│   ├── config.py        # 配置管理
│   └── events.py        # 事件总线 (EventBus)
├── i18n/                # 国际化
│   ├── __init__.py      # tr() 函数
│   └── translations.py  # 翻译字典
├── player/              # 播放引擎
│   ├── thread.py        # PlayerThread
│   ├── config.py        # PlayerConfig
│   ├── quantize.py      # 量化策略
│   ├── midi_parser.py   # MIDI 解析
│   ├── scheduler.py     # 事件调度
│   ├── errors.py        # 错误模拟
│   └── bar_utils.py     # 小节工具
├── ui/                  # UI 组件
│   ├── floating.py      # FloatingController
│   └── constants.py     # UI 常量
├── input_manager.py     # 输入系统
├── keyboard_layout.py   # 键位布局
├── settings_manager.py  # 设置管理
└── style_manager.py     # 风格/8-bar

主线程 (Qt)
├── MainWindow (main.py)
│   ├── UI 渲染
│   ├── 热键信号处理
│   └── 设置管理
└── i18n.tr() 翻译

PlayerThread (player/thread.py)
├── 事件队列 (heapq)
├── 风格应用 (style_manager)
├── 错误模拟 (player/errors.py)
└── InputManager 调用

InputManager
├── SendInputBackend (扫描码)
├── 状态追踪 (active_keys)
├── 焦点监控线程
└── 诊断统计

FocusMonitor (后台线程)
├── 100ms 轮询
└── 失焦自动释放
```

## 版本历史

### v3.1 (当前)
- **模块化重构**: main.py 从 3834 行精简到 1961 行 (-48.8%)
- 新增 `core/` 模块 (配置管理、事件总线)
- 新增 `i18n/` 模块 (国际化、tr() 函数)
- 新增 `player/` 模块 (播放引擎、量化、调度、错误模拟)
- 新增 `ui/` 模块 (浮动控制器、UI 常量)
- 架构更清晰，便于扩展

### v3.0
- 完全重写输入系统（SendInput + 扫描码）
- 添加焦点监控和自动释放
- 新增设置管理器和预设系统
- 增强诊断功能

### v2.0
- 添加 InputManager 抽象层
- 支持多后端切换

### v1.0
- 基本 MIDI 播放
- 21/36 键支持

## 许可证

仅供学习研究使用，请勿用于商业目的或违反游戏服务条款。

## 致谢

- PyQt6
- mido (MIDI 处理)
- keyboard (全局热键)
- FluidSynth (音效预览)
