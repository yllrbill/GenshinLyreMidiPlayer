# Architecture Design: Core & Plugin Boundaries

> Step 2 产出：定义核心与插件边界

## 设计原则

1. **核心最小化**: 核心只包含启动、配置、事件调度、插件加载
2. **插件可选**: 任何插件加载失败不影响核心功能
3. **配置兼容**: 旧配置格式无需迁移
4. **入口不变**: 仍可通过 `python main.py` 启动

## 目录结构设计

```
LyreAutoPlayer/
├── main.py                    # 入口 (精简后 ~200 行)
├── __init__.py                # 包初始化
│
├── core/                      # 核心模块 (必需)
│   ├── __init__.py
│   ├── app.py                 # Application 类 (插件加载、生命周期)
│   ├── config.py              # 配置模型与管理 (整合 settings_manager)
│   ├── events.py              # 事件总线 (发布/订阅)
│   └── constants.py           # 全局常量
│
├── i18n/                      # 国际化模块 (核心依赖)
│   ├── __init__.py            # tr() 函数
│   └── translations.py        # 翻译字典
│
├── player/                    # 播放器模块 (功能核心)
│   ├── __init__.py
│   ├── thread.py              # PlayerThread (精简)
│   ├── quantize.py            # 音符量化策略
│   ├── midi_parser.py         # MIDI 解析
│   ├── scheduler.py           # 事件调度 (KeyEvent queue)
│   └── sound.py               # FluidSynth 音效
│
├── ui/                        # UI 模块 (可选)
│   ├── __init__.py
│   ├── main_window.py         # 主窗口框架
│   ├── floating.py            # 悬浮窗
│   └── tabs/                  # Tab 面板
│       ├── __init__.py
│       ├── main_tab.py        # 主设置
│       ├── keyboard_tab.py    # 键盘
│       ├── shortcuts_tab.py   # 快捷键
│       ├── style_tab.py       # 输入风格
│       └── errors_tab.py      # 错误模拟
│
├── plugins/                   # 插件目录 (可选)
│   ├── __init__.py
│   ├── errors.py              # 错误模拟插件
│   ├── eight_bar.py           # 8-bar 变速插件
│   └── humanize.py            # 人性化输入插件
│
├── input_manager.py           # 保留 (已独立)
├── keyboard_layout.py         # 保留 (已独立)
├── style_manager.py           # 保留 (已独立)
├── global_hotkey.py           # 保留 (已独立)
└── settings_manager.py        # 保留 (被 core/config.py 封装)
```

## 模块职责定义

### 核心层 (core/)

| 模块 | 职责 | 依赖 |
|------|------|------|
| `app.py` | Application 单例、插件注册/加载、生命周期管理 | events, config |
| `config.py` | 配置读写、配置域分离、默认值管理 | settings_manager |
| `events.py` | 事件发布/订阅、信号解耦 | 无 |
| `constants.py` | 全局常量 (MIDI、音阶、文件路径) | 无 |

### 功能层 (player/, ui/)

| 模块 | 职责 | 依赖 |
|------|------|------|
| `player/thread.py` | 播放主循环、事件调度 | scheduler, quantize, events |
| `player/quantize.py` | 音符量化策略 (nearest/octave/lower/upper/drop) | keyboard_layout |
| `player/midi_parser.py` | MIDI 文件解析、NoteEvent 生成 | mido |
| `player/scheduler.py` | 按键事件优先队列、时序控制 | 无 |
| `player/sound.py` | FluidSynth 音效播放 | fluidsynth (可选) |
| `ui/main_window.py` | 主窗口框架、Tab 容器 | PyQt6, events |
| `ui/floating.py` | 悬浮控制面板 | PyQt6, events |
| `ui/tabs/*.py` | 各功能 Tab 面板 | PyQt6, i18n |

### 插件层 (plugins/)

| 模块 | 职责 | 依赖 |
|------|------|------|
| `errors.py` | 错误模拟 (wrong_note, miss_note, extra_note, pause) | events |
| `eight_bar.py` | 8-bar 变速/节拍锁定 | events |
| `humanize.py` | 人性化输入 (timing offset, chord stagger) | style_manager |

---

## 配置域分离

当前 `PlayerConfig` 包含所有配置，需要分离为独立域：

### 配置域定义

```python
# core/config.py

@dataclass
class PlaybackConfig:
    """播放相关配置"""
    root_mid_do: int = 60
    octave_shift: int = 0
    transpose: int = 0
    speed: float = 1.0
    accidental_policy: str = "nearest"
    press_ms: int = 25
    use_midi_duration: bool = False
    keyboard_preset: str = "21-key"
    countdown_sec: int = 2

@dataclass
class SoundConfig:
    """音效相关配置"""
    play_sound: bool = False
    soundfont_path: str = ""
    instrument: str = "Piano"
    velocity: int = 90

@dataclass
class ErrorConfig:
    """错误模拟配置"""
    enabled: bool = False
    errors_per_8bars: int = 1
    wrong_note: bool = True
    miss_note: bool = True
    extra_note: bool = True
    pause_error: bool = True
    pause_min_ms: int = 100
    pause_max_ms: int = 500

@dataclass
class EightBarConfig:
    """8-bar 风格配置"""
    enabled: bool = False
    mode: str = "warp"
    pattern: str = "skip1"
    speed_variation: float = 0.0
    timing_variation: float = 0.0
    duration_variation: float = 0.0

@dataclass
class AppConfig:
    """应用配置 (组合所有域)"""
    playback: PlaybackConfig
    sound: SoundConfig
    error: ErrorConfig
    eight_bar: EightBarConfig
    target_hwnd: Optional[int] = None
    midi_path: str = ""
    enable_diagnostics: bool = False
```

### 配置兼容性

```python
class ConfigManager:
    """配置管理器 (兼容旧格式)"""

    def load(self) -> AppConfig:
        """加载配置，自动迁移旧格式"""
        pass

    def save(self, config: AppConfig):
        """保存配置"""
        pass

    def migrate_v1_to_v2(self, old_data: dict) -> dict:
        """旧格式迁移"""
        pass
```

---

## 事件总线设计

### 事件类型

```python
# core/events.py

class EventType(Enum):
    # 播放控制
    PLAY_START = "play_start"
    PLAY_STOP = "play_stop"
    PLAY_PAUSE = "play_pause"
    PLAY_RESUME = "play_resume"
    PLAY_PROGRESS = "play_progress"  # (current, total)
    PLAY_FINISHED = "play_finished"

    # 配置变更
    CONFIG_CHANGED = "config_changed"  # (domain, key, value)
    LANGUAGE_CHANGED = "language_changed"  # (new_lang)

    # 热键
    HOTKEY_TRIGGERED = "hotkey_triggered"  # (action)

    # 日志
    LOG_MESSAGE = "log_message"  # (level, message)

    # UI
    UI_REFRESH = "ui_refresh"
    FLOATING_TOGGLE = "floating_toggle"
```

### 事件总线 API

```python
class EventBus:
    """事件发布/订阅"""

    def subscribe(self, event_type: EventType, handler: Callable):
        """订阅事件"""
        pass

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """取消订阅"""
        pass

    def publish(self, event_type: EventType, *args, **kwargs):
        """发布事件"""
        pass

    def publish_async(self, event_type: EventType, *args, **kwargs):
        """异步发布事件 (用于 Qt 线程安全)"""
        pass
```

---

## 插件接口设计

### 最小接口

```python
# core/app.py

class Plugin(ABC):
    """插件基类"""

    name: str  # 插件名称
    version: str = "1.0.0"
    description: str = ""

    @abstractmethod
    def on_load(self, app: "Application"):
        """插件加载时调用"""
        pass

    def on_unload(self):
        """插件卸载时调用 (可选)"""
        pass

    def on_config_changed(self, domain: str, key: str, value: Any):
        """配置变更时调用 (可选)"""
        pass
```

### 插件注册

```python
class Application:
    """应用主类"""

    def __init__(self):
        self.events = EventBus()
        self.config = ConfigManager()
        self.plugins: Dict[str, Plugin] = {}

    def register_plugin(self, plugin: Plugin):
        """注册插件"""
        try:
            plugin.on_load(self)
            self.plugins[plugin.name] = plugin
            self.events.publish(EventType.LOG_MESSAGE, "info", f"Plugin loaded: {plugin.name}")
        except Exception as e:
            self.events.publish(EventType.LOG_MESSAGE, "warn", f"Plugin failed: {plugin.name}: {e}")

    def unregister_plugin(self, name: str):
        """卸载插件"""
        if name in self.plugins:
            self.plugins[name].on_unload()
            del self.plugins[name]
```

### 插件发现

```python
def discover_plugins(plugin_dir: str = "plugins") -> List[Type[Plugin]]:
    """自动发现插件"""
    plugins = []
    for file in Path(plugin_dir).glob("*.py"):
        if file.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin:
                plugins.append(obj)
    return plugins
```

---

## 模块边界图

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py (入口)                          │
│  - 创建 Application                                              │
│  - 加载插件                                                       │
│  - 启动 Qt 事件循环                                               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      core/ (核心层)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    app.py   │◄─│  events.py  │◄─│  config.py  │             │
│  │  Application│  │  EventBus   │  │ConfigManager│             │
│  └──────┬──────┘  └─────────────┘  └─────────────┘             │
│         │                                                       │
│         │ register_plugin()                                     │
└─────────┼───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    功能层 (player/, ui/)                         │
│  ┌─────────────────────────┐   ┌─────────────────────────┐     │
│  │     player/             │   │     ui/                 │     │
│  │  ┌──────────────────┐   │   │  ┌──────────────────┐   │     │
│  │  │  thread.py       │   │   │  │  main_window.py  │   │     │
│  │  │  PlayerThread    │   │   │  │  MainWindow      │   │     │
│  │  └──────────────────┘   │   │  └──────────────────┘   │     │
│  │  ┌──────────────────┐   │   │  ┌──────────────────┐   │     │
│  │  │  quantize.py     │   │   │  │  floating.py     │   │     │
│  │  └──────────────────┘   │   │  └──────────────────┘   │     │
│  │  ┌──────────────────┐   │   │  ┌──────────────────┐   │     │
│  │  │  midi_parser.py  │   │   │  │  tabs/*.py       │   │     │
│  │  └──────────────────┘   │   │  └──────────────────┘   │     │
│  └─────────────────────────┘   └─────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼ (可选)
┌─────────────────────────────────────────────────────────────────┐
│                    plugins/ (插件层)                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│  │ errors.py  │  │ eight_bar  │  │ humanize   │                 │
│  │ ErrorPlugin│  │.py         │  │.py         │                 │
│  └────────────┘  └────────────┘  └────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 实施优先级

| 阶段 | 模块 | 依赖 | 验收标准 |
|------|------|------|----------|
| Phase 1 | i18n/ | 无 | `tr()` 可从独立模块调用 |
| Phase 1 | core/events.py | 无 | 发布/订阅示例可运行 |
| Phase 1 | core/config.py | settings_manager | 配置读写正常 |
| Phase 2 | core/app.py | events, config | 插件加载/卸载正常 |
| Phase 2 | player/* | 无 | MIDI 播放正常 |
| Phase 3 | ui/* | events, i18n | UI 显示正常 |
| Phase 3 | plugins/* | core | 错误/8-bar 功能正常 |
| Phase 4 | main.py 精简 | 所有 | 体积 < 300 行 |

---

*生成时间: 2026-01-02*
*Plan Step 2 完成*
