# Project Summary - LyreAutoPlayer

> 自动生成于 2026-01-02，供后续分析定位使用

## 1. 基础信息

| 项目 | 值 |
|------|-----|
| 项目根目录 | `d:/dw11/piano/LyreAutoPlayer` |
| Git 分支 | `main` |
| 主要语言 | Python |
| 框架 | PyQt6 |
| Python 文件数 | 44 |
| 代码行数 | ~5949 行 |

## 2. 目录结构

```
LyreAutoPlayer/
├── main.py              # 主程序入口 (2206 行)
├── core/                # 核心模块 (599 行)
│   ├── __init__.py      # 模块导出
│   ├── config.py        # 配置管理 (220 行)
│   ├── constants.py     # 常量定义 (108 行)
│   └── events.py        # 事件总线 (226 行)
├── player/              # 播放引擎 (~1316 行)
│   ├── __init__.py      # 模块导出
│   ├── config.py        # PlayerConfig
│   ├── errors.py        # 错误模拟
│   ├── midi_parser.py   # MIDI 解析
│   ├── scheduler.py     # 事件调度
│   └── thread.py        # PlayerThread (836 行)
├── ui/                  # UI 组件 (~447 行)
│   ├── constants.py     # UI 常量
│   └── floating.py      # FloatingController (412 行)
├── i18n/                # 国际化 (~250 行)
│   ├── __init__.py      # tr() 函数
│   └── translations.py  # 翻译字典
├── styles/              # 演奏风格
│   └── registry.py      # StyleRegistry
├── input_manager.py     # 输入系统 (964 行)
├── keyboard_layout.py   # 键位布局
├── settings_manager.py  # 设置管理
├── style_manager.py     # 风格/8-bar
└── backup/              # 备份文件 (可删除)
```

## 3. 入口文件

| 入口 | 路径 | 说明 |
|------|------|------|
| 主入口 | `main.py` | PyQt6 GUI 应用入口 |
| 测试入口 | `test_regression.py` | 回归测试 |
| 诊断工具 | `diagnose_input.py` | 输入系统诊断 |

## 4. 核心模块与类

| 模块 | 核心类 | 职责 |
|------|--------|------|
| `main.py` | `MainWindow` | PyQt6 主窗口、UI 容器 |
| `core/config.py` | `ConfigManager` | 配置管理 |
| `core/events.py` | `EventBus`, `EventType` | 发布/订阅事件系统 |
| `player/thread.py` | `PlayerThread` | MIDI 播放线程 |
| `player/config.py` | `PlayerConfig` | 播放配置数据类 |
| `player/errors.py` | `ErrorConfig`, `ErrorType` | 错误模拟 |
| `player/scheduler.py` | `KeyEvent` | 键盘事件调度 |
| `ui/floating.py` | `FloatingController` | 浮动控制器窗口 |
| `input_manager.py` | `InputManager`, `SendInputBackend` | 键盘输入抽象 |
| `styles/registry.py` | `StyleRegistry`, `InputStyle` | 演奏风格注册 |
| `settings_manager.py` | `SettingsManager` | 设置持久化 |

## 5. 关键依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| PyQt6 | >=6.6 | GUI 框架 |
| mido | >=1.3 | MIDI 文件解析 |
| pydirectinput | >=1.0 | 键盘输入模拟 |
| pywin32 | >=306 | Windows API 调用 |
| pyfluidsynth | >=1.3 | 音效预览 |
| sounddevice | >=0.4 | 音频设备 |
| keyboard | (可选) | 全局热键 |

## 6. 配置文件

| 文件 | 用途 |
|------|------|
| `settings.json` | 应用运行时配置 |
| `requirements.txt` | Python 依赖 |
| `FluidR3_GM.sf2` | SoundFont 音色库 |

## 7. 构建/运行/测试

| 操作 | 命令 |
|------|------|
| 创建虚拟环境 | `python -m venv .venv` |
| 激活环境 | `.venv\Scripts\activate` |
| 安装依赖 | `pip install -r requirements.txt` |
| 运行 | `python main.py` |
| 测试输入 | `python test_input_manager.py --interactive` |

## 8. 数据流概要

```
[输入] MIDI 文件
    ↓
[解析] mido (player/midi_parser.py)
    ↓
[处理] PlayerThread (player/thread.py)
    │
    ├─→ [应用风格] style_manager.py
    ├─→ [错误模拟] player/errors.py
    │
    ↓
[输出] InputManager (input_manager.py)
    │
    ├─→ SendInputBackend → 游戏窗口
    └─→ FluidSynth → 音频预览
```

## 9. 扩展点

| 扩展点 | 位置 | 说明 |
|--------|------|------|
| 输入后端 | `input_manager.py:InputBackend` | 可添加新的输入方式 |
| 演奏风格 | `styles/registry.py:StyleRegistry` | 可注册新风格 |
| 事件类型 | `core/events.py:EventType` | 可扩展事件总线 |
| 翻译 | `i18n/translations.py` | 可添加新语言 |

## 10. 代码行数分布

| 模块 | 行数 | 占比 |
|------|------|------|
| main.py (MainWindow) | 2206 | 37% |
| player/ | ~1316 | 22% |
| input_manager.py | 964 | 16% |
| core/ | 599 | 10% |
| ui/ | ~447 | 8% |
| i18n/ | ~250 | 4% |
| 其他 | ~167 | 3% |

---

## 11. 继续重构的方法建议

> **当前约束**: main.py 大量使用动态控件构建 + 运行时 i18n 绑定 (`apply_language()` 逐控件 `.setText()`)。
> 任何重构方案需保留这些动态特性。

### 方法 A: Mixin 模式分离 (推荐首选 - 低风险)

**目标**: 将大类按职责拆分为多个 Mixin 类，不改变控件构建方式

**优势**:
- 最小改动，低风险
- 保留动态控件构建和 i18n 绑定
- 代码组织更清晰，易于定位

**步骤**:
1. 创建 `ui/mixins/` 目录
2. 按功能分离:
   - `SettingsMixin` - save/load_settings (~200行)
   - `HotkeyMixin` - 热键注册 (~30行)
   - `PlaybackMixin` - 播放控制 (~100行)
   - `LanguageMixin` - 翻译绑定 (~100行)
3. MainWindow 多重继承这些 Mixin

**示例**:
```python
# ui/mixins/settings_mixin.py
class SettingsMixin:
    def save_settings(self):
        # 使用 self.xxx 控件 (保持不变)
        ...

# main.py (~1700行，减少 ~500行)
from ui.mixins import SettingsMixin, HotkeyMixin, PlaybackMixin

class MainWindow(QWidget, SettingsMixin, HotkeyMixin, PlaybackMixin):
    def __init__(self):
        super().__init__()
        self._init_ui()  # 控件构建保留在 main.py
```

**效果**: main.py 减少到 ~1700 行，逻辑分散到 mixins

### 方法 B: UI 设计器分离 (第二阶段 - 中风险)

**目标**: 将**静态布局**移到 `.ui` 文件，保留动态部分在代码中

**风险警告**:
- ⚠️ 动态创建的控件 (如 ComboBox 选项、动态按钮) 仍需代码构建
- ⚠️ `apply_language()` 的 i18n 绑定需手动迁移到 `retranslateUi()`
- ⚠️ 需要同时维护 `.ui` 文件和代码中的动态部分

**适用部分** (可静态化):
- 基础布局框架 (QVBoxLayout, QHBoxLayout, QTabWidget)
- 固定控件 (按钮、标签、分组框)

**不适用部分** (需保留代码):
- 运行时翻译绑定
- 动态填充的 ComboBox
- 根据配置显示/隐藏的控件

**步骤**:
1. 使用 Qt Designer 创建 `mainwindow.ui` (仅静态框架)
2. 使用 `pyuic6 -x mainwindow.ui -o ui_mainwindow.py`
3. MainWindow 继承生成的类 + 代码补充动态部分
4. 重写 `retranslateUi()` 实现 i18n

**效果**: main.py 可从 ~1700 行减少到 ~1000 行 (假设已完成方法 A)

### 方法 C: MVP/MVC 架构重构 (第三阶段 - 高工作量)

**目标**: 完全分离视图和逻辑

**架构**:
```
View (main.py)         - 纯 UI，无业务逻辑
    ↓
Presenter (presenter.py) - 业务逻辑，操作 View 接口
    ↓
Model (models.py)      - 数据模型
```

**步骤**:
1. 定义 `IMainView` 接口（所有 UI 操作抽象）
2. 创建 `MainPresenter` 处理业务逻辑
3. MainWindow 实现 IMainView，只做 UI 渲染

**示例**:
```python
# interfaces.py
class IMainView(Protocol):
    def set_speed(self, value: float): ...
    def get_octave(self) -> int: ...
    def show_message(self, text: str): ...

# presenter.py
class MainPresenter:
    def __init__(self, view: IMainView, config: ConfigManager):
        self.view = view
        self.config = config

    def on_start(self):
        cfg = self._collect_config()
        # 业务逻辑...
        self.view.show_message("Started")

# main.py
class MainWindow(QWidget, IMainView):
    def __init__(self):
        self.presenter = MainPresenter(self, get_config())
        self.btn_start.clicked.connect(self.presenter.on_start)
```

**效果**: main.py 减少到 ~400 行，可测试性大幅提升

### 方法 D: QML 替代 (长期愿景 - 不推荐近期采用)

**目标**: 使用 QML 声明式 UI

**为什么不推荐近期采用**:
- ❌ 与现有 QtWidgets 架构差异过大
- ❌ 需要重写整个 UI 层
- ❌ 改变依赖栈 (需要 Qt Quick)
- ❌ 团队需要学习 QML 语法
- ❌ 现有 i18n 机制需完全重构

**仅作为长期方向**: 如果未来需要跨平台 (移动端) 或需要更现代的 UI，可考虑。

---

## 12. 推荐执行路径

| 阶段 | 方法 | 工作量 | 风险 | main.py 行数 |
|------|------|--------|------|-------------|
| **阶段 1** | 方法 A (Mixin) | 低 | 低 | 2206 → ~1700 |
| 阶段 2 | 方法 B (UI 设计器) | 中 | 中 | ~1700 → ~1000 |
| 阶段 3 | 方法 C (MVP) | 高 | 中 | ~1000 → ~400 |
| (长期) | 方法 D (QML) | 很高 | 高 | 完全重构 |

**建议执行顺序**:
1. **立即可做**: 方法 A (Mixin) - 最小改动，将方法分组到 mixin 类
2. **评估后做**: 方法 B (UI 设计器) - 需评估哪些控件可静态化
3. **按需做**: 方法 C (MVP) - 当需要单元测试覆盖时
4. **暂不考虑**: 方法 D (QML) - 仅作为长期技术储备

---

## 13. 审核备注

| 级别 | 问题 | 状态 |
|------|------|------|
| 中 | 原版推荐路径自相矛盾 | ✅ 已修正优先级排序 |
| 中 | 方法 A 未说明动态控件/i18n 风险 | ✅ 已添加风险警告 |
| 中 | 方法 D 不符合低风险重构目标 | ✅ 已标注为长期愿景 |
| 低 | 基线行数不一致 (2206 vs 2271) | 使用实测值 2206 |

---

*Generated by /ai-project-sum*
*Reviewed: 2026-01-02*
