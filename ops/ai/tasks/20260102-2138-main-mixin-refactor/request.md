# Task Request: main.py Mixin/Controller 重构

## TASK_ID
20260102-2138-main-mixin-refactor

## Created
2026-01-02 21:38

## Goal
采用 Mixin/Controller 模式将 main.py 从 2206 行精简到 ≤1000 行，保留动态控件构建和运行时 i18n 绑定。

## 核心约束
- **保留动态特性**: 控件仍在 main.py 构建 (self.xxx = QWidget())
- **保留 i18n 绑定**: apply_language() 仍逐控件 setText()
- **不改变控件构建方式**: 仅抽离逻辑到 Mixin/Controller

## 执行计划

### Phase 1: Mixin/Controller 抽离逻辑块 (2206 → ~1500 行)

| 步骤 | 目标模块 | 预计削减 | 说明 |
|------|----------|----------|------|
| P1-1 | `ui/mixins/language_mixin.py` | ~100 行 | tr() 调用集中、语言切换回调 |
| P1-2 | `ui/mixins/presets_mixin.py` | ~80 行 | 预设加载/保存/删除/应用 |
| P1-3 | `ui/mixins/config_mixin.py` | ~200 行 | collect_cfg()、save/load_settings |
| P1-4 | `ui/mixins/playback_mixin.py` | ~150 行 | on_start/on_stop/on_pause、播放状态管理 |
| P1-5 | `ui/mixins/hotkeys_mixin.py` | ~30 行 | keyboard 热键注册/注销 |
| P1-6 | `ui/mixins/logs_mixin.py` | ~50 行 | append_log、日志格式化 |

**削减估计**: ~610 行 → main.py ~1596 行

### Phase 2: 拆 Tab 为独立 QWidget (1596 → ~1000 行)

| 步骤 | 目标模块 | 预计削减 | 说明 |
|------|----------|----------|------|
| P2-1 | `ui/tabs/basic_tab.py` | ~150 行 | 基础设置 Tab |
| P2-2 | `ui/tabs/playback_tab.py` | ~100 行 | 播放控制 Tab |
| P2-3 | `ui/tabs/style_tab.py` | ~80 行 | 风格设置 Tab |
| P2-4 | `ui/tabs/advanced_tab.py` | ~100 行 | 高级设置 Tab |
| P2-5 | `ui/tabs/about_tab.py` | ~50 行 | 关于 Tab |

**削减估计**: ~480 行 → main.py ~1116 行

### Phase 3: .ui 静态布局 (可选，1116 → ~800 行)

> ⚠️ 风险较高，仅适用于固定不变的布局部分

| 步骤 | 目标 | 预计削减 | 说明 |
|------|------|----------|------|
| P3-1 | 基础框架布局 | ~100 行 | QVBoxLayout/QHBoxLayout 嵌套 |
| P3-2 | 固定控件 | ~200 行 | 不需要动态修改的控件 |

**削减估计**: ~300 行 → main.py ~816 行

## 目标架构

```python
# main.py (~800-1000 行)
from ui.mixins import LanguageMixin, PresetsMixin, ConfigMixin, PlaybackMixin, HotkeysMixin
from ui.tabs import BasicTab, PlaybackTab, StyleTab, AdvancedTab, AboutTab
from ui.controllers import AppContext

class MainWindow(QWidget, LanguageMixin, PresetsMixin, ConfigMixin, PlaybackMixin, HotkeysMixin):
    def __init__(self):
        super().__init__()
        self.ctx = AppContext(self)      # 共享上下文
        self._init_ui()                   # 控件构建 (保留在 main.py)
        self._init_tabs()                 # Tab 组装
        self._connect_signals()           # 信号槽连接
        self.load_settings()              # 来自 ConfigMixin
        self.register_hotkeys()           # 来自 HotkeysMixin

    def _init_tabs(self):
        self.tab_basic = BasicTab(self.ctx)
        self.tab_playback = PlaybackTab(self.ctx)
        # ...

    def apply_language(self):
        # 仍逐控件 setText()，但可用 LanguageMixin 辅助
        ...
```

## Success Criteria
- [ ] main.py 行数 ≤ 1000 行
- [ ] 所有模块通过 py_compile 检查
- [ ] 应用可正常启动 (`python main.py`)
- [ ] 现有功能无回归
- [ ] apply_language() 正常工作
- [ ] 热键功能正常

## Dependencies
- 前置任务: 20260102-0513-main-further-separation (PARTIAL)

## Reference
- PROJECT_SUMMARY.md 方法 A (Mixin 模式)
- 用户提供的详细重构路径
