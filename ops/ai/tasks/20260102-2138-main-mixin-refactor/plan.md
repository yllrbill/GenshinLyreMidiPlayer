# 执行计划: main.py Mixin/Controller 重构

## 概述

| 阶段 | 方法 | 起始行数 | 目标行数 | 风险 |
|------|------|----------|----------|------|
| Phase 1 | Mixin 抽离 | 2206 | ≤1600 | 低 |
| Phase 2 | Tab Builder 函数 | ≤1600 | ≤1100 | 低-中 |
| Phase 3 | .ui 布局 | ≤1100 | ≤800 | 中 |

> **核心约束**: 控件仍在 main.py 构建 (`self.xxx = QWidget()`)，Mixin 仅抽离逻辑方法

## Phase 1: Mixin/Controller 抽离 (~610 行)

### P1-0: 创建目录结构

**目标目录**: `ui/mixins/`

**说明**: 先建立 mixin 目录，后续按模块拆分文件。

---

### P1-1: LanguageMixin (~50 行)

**目标文件**: `ui/mixins/language_mixin.py`

**实际方法** (基于 main.py，行号仅参考):
- `on_language_changed(index)` - 语言切换回调
- 语言相关的辅助逻辑

**保留在 main.py**:
- `apply_language()` - 因直接访问 ~100 个控件的 setText()

**示例结构**:
```python
from i18n import set_language, get_language

class LanguageMixin:
    def on_language_changed(self, index: int):
        """Handle language combobox change."""
        lang = self.cmb_language.itemData(index)
        if lang:
            self.lang = lang
            set_language(lang)
            self.apply_language()  # 调用 main.py 中的方法
```

**预计削减**: ~30-50 行 (辅助逻辑)

---

### P1-2: SettingsPresetMixin (~100 行)

**目标文件**: `ui/mixins/settings_preset_mixin.py`

**实际方法** (基于 main.py，行号仅参考):
- `_rebuild_settings_preset_combo()` - 重建设置预设下拉框
- `on_apply_settings_preset()` - 应用选中的设置预设
- `on_reset_defaults()` - 重置为默认值
- `on_preset_changed(index)` - keyboard preset 切换
- `on_kb_preset_changed(index)` - keyboard tab preset 同步

**示例结构**:
```python
class SettingsPresetMixin:
    def _rebuild_settings_preset_combo(self):
        """Rebuild settings preset dropdown."""
        # ...

    def on_apply_settings_preset(self):
        """Apply selected settings preset to UI."""
        # ...

    def on_reset_defaults(self):
        """Reset all settings to defaults."""
        # ...

    def on_preset_changed(self, index: int):
        """Called when main tab keyboard preset combo box changes."""
        self.cmb_preset_kb.blockSignals(True)
        self.cmb_preset_kb.setCurrentIndex(index)
        self.cmb_preset_kb.blockSignals(False)
        self._build_keyboard_display()

    def on_kb_preset_changed(self, index: int):
        """Called when keyboard tab preset combo box changes."""
        self.cmb_preset.blockSignals(True)
        self.cmb_preset.setCurrentIndex(index)
        self.cmb_preset.blockSignals(False)
        self._build_keyboard_display()
```

**预计削减**: ~80-100 行

---

### P1-3: ConfigMixin (~200 行)

**目标文件**: `ui/mixins/config_mixin.py`

**实际方法** (基于 main.py，行号仅参考):
- `collect_cfg()` - 收集当前 UI 配置为 PlayerConfig
- `save_settings()` - 保存到 settings.json
- `load_settings()` - 从 settings.json 加载
- `_collect_ui_values()` - 辅助方法

**注意**: 这些方法访问 `self.xxx` 控件，但逻辑可抽离

**示例结构**:
```python
import json
from pathlib import Path
from player import PlayerConfig

class ConfigMixin:
    def collect_cfg(self) -> PlayerConfig:
        """Collect current UI values into PlayerConfig."""
        return PlayerConfig(
            bpm=self.sp_bpm.value(),
            speed=self.sl_speed.value() / 100.0,
            octave_shift=self.cmb_octave.currentIndex() - 2,
            keyboard_preset=str(self.cmb_preset.currentData()),
            # ... 其他字段
        )

    def save_settings(self):
        """Save current settings to settings.json."""
        settings = {
            "language": self.cmb_language.currentData(),
            "bpm": self.sp_bpm.value(),
            "keyboard_preset": self.cmb_preset.currentData(),
            # ...
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

    def load_settings(self):
        """Load settings from settings.json."""
        if not SETTINGS_FILE.exists():
            return
        # ...
```

**预计削减**: ~150-200 行

---

### P1-4: PlaybackMixin (~150 行)

**目标文件**: `ui/mixins/playback_mixin.py`

**实际方法** (基于 main.py，行号仅参考):
- `on_start()` - 开始播放
- `on_stop()` - 停止播放
- `on_toggle_play_pause()` - F5 热键触发的切换
- `_on_playback_finished()` - 播放完成回调
- `_on_progress_update()` - 进度更新

**示例结构**:
```python
class PlaybackMixin:
    def on_start(self):
        """Start playback."""
        if not self.current_file:
            self.append_log("[WARN] 请先选择 MIDI 文件")
            return
        cfg = self.collect_cfg()
        self.thread = PlayerThread(cfg)
        self.thread.sig_log.connect(self.append_log)
        self.thread.sig_finished.connect(self._on_playback_finished)
        self.thread.start()
        # ...

    def on_stop(self):
        """Stop playback."""
        if self.thread and self.thread.isRunning():
            self.thread.stop()
        # ...

    def on_toggle_play_pause(self):
        """Toggle between play/pause states (for F5 hotkey)."""
        # ...
```

**预计削减**: ~100-150 行

---

### P1-5: HotkeysMixin (~50 行)

**目标文件**: `ui/mixins/hotkeys_mixin.py`

**实际方法** (基于 main.py，行号仅参考):
- `_register_global_hotkeys()` - 注册 F5-F12 热键
- `_cleanup_hotkeys()` - closeEvent 中的清理

**实际热键** (F5-F12，非 Ctrl 组合):
- F5: toggle play/pause (`sig_toggle_play_pause`)
- F6: stop (`sig_stop`)
- F7: speed down (`sig_speed_down`)
- F8: speed up (`sig_speed_up`)

**示例结构**:
```python
try:
    import keyboard as kb
    _keyboard_available = True
except ImportError:
    _keyboard_available = False

class HotkeysMixin:
    def _register_global_hotkeys(self):
        """Register global hotkeys using keyboard library (F5-F12)."""
        if not _keyboard_available:
            self.append_log("[WARN] 全局热键不可用: keyboard 库未安装")
            return

        try:
            # F5: Toggle (start/pause/resume)
            kb.on_press_key('f5', lambda e: self.sig_toggle_play_pause.emit(), suppress=True)
            # F6: Stop
            kb.on_press_key('f6', lambda e: self.sig_stop.emit(), suppress=True)
            # F7: Speed-
            kb.on_press_key('f7', lambda e: self.sig_speed_down.emit(), suppress=True)
            # F8: Speed+
            kb.on_press_key('f8', lambda e: self.sig_speed_up.emit(), suppress=True)
            self.append_log("[OK] 全局热键已注册(F5-F12)")
        except Exception as ex:
            self.append_log(f"[WARN] 热键注册失败: {ex}")

    def _cleanup_hotkeys(self):
        """Cleanup global hotkeys on window close."""
        if _keyboard_available:
            try:
                kb.unhook_all()
            except:
                pass
```

**预计削减**: ~40-50 行

---

### P1-6: LogsMixin (~30 行)

**目标文件**: `ui/mixins/logs_mixin.py`

**实际方法** (基于 main.py，行号仅参考):
- `append_log(msg)` - 添加日志到 txt_log

**示例结构**:
```python
class LogsMixin:
    def append_log(self, msg: str):
        """Append message to log widget with auto-scroll."""
        self.txt_log.append(msg)
        # Auto-scroll to bottom
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
```

**预计削减**: ~20-30 行

---

### Phase 1 验证

- main.py 行数 ≤ 1600
- 基础功能可用（启动、语言切换、播放/停止、日志输出、热键 F5-F12）

---

## Phase 2: Tab Builder 函数抽离 (~400 行)

> **约束变更**: 按审计建议，改为"Tab Builder 函数"而非独立 QWidget，保持控件在 main.py 构建

### 实际 Tab 结构 (基于 main.py)

| Tab 索引 | 名称 | 行范围 | 估计行数 |
|----------|------|--------|----------|
| 0 | Main | 178-375 | ~200 |
| 1 | Keyboard | 377-408 | ~30 |
| 2 | Shortcuts | 410-445 | ~35 |
| 3 | Input Style | 447-635 | ~190 |
| 4 | Errors | 637-713 | ~75 |

### P2-1: 提取 Tab Builder 函数

**目标文件**: `ui/tab_builders.py`

**方式**: 将每个 Tab 的控件构建逻辑提取为返回 QWidget 的函数

**示例结构**:
```python
def build_main_tab(window: "MainWindow") -> QWidget:
    """Build the Main tab and attach widgets to window."""
    tab = QWidget()
    layout = QVBoxLayout(tab)

    # File selection group
    grp_file = QGroupBox()
    window.grp_file = grp_file  # 保持 main.py 的引用方式
    # ...

    return tab

def build_keyboard_tab(window: "MainWindow") -> QWidget:
    """Build the Keyboard tab."""
    # ...

def build_shortcuts_tab(window: "MainWindow") -> QWidget:
    """Build the Shortcuts tab."""
    # ...

def build_style_tab(window: "MainWindow") -> QWidget:
    """Build the Input Style tab."""
    # ...

def build_errors_tab(window: "MainWindow") -> QWidget:
    """Build the Errors tab."""
    # ...
```

**main.py 调用方式**:
```python
from ui.tab_builders import (
    build_main_tab, build_keyboard_tab, build_shortcuts_tab,
    build_style_tab, build_errors_tab
)

class MainWindow(QWidget, ...):
    def _init_ui(self):
        # ...
        self.tabs = QTabWidget()
        self.tabs.addTab(build_main_tab(self), "Main")
        self.tabs.addTab(build_keyboard_tab(self), "Keyboard")
        self.tabs.addTab(build_shortcuts_tab(self), "Shortcuts")
        self.tabs.addTab(build_style_tab(self), "Input Style")
        self.tabs.addTab(build_errors_tab(self), tr("tab_errors", self.lang))
```

**预计削减**: ~400 行 (将 Tab 构建逻辑移到 tab_builders.py)

### Phase 2 验证

- main.py 行数 ≤ 1100
- Tab 切换正常
- apply_language() 仍能访问所有控件

---

## Phase 3: .ui 静态布局 (可选)

> ⚠️ **风险警告**: 仅适用于固定布局，动态控件仍需代码构建

### P3-1: 适用部分

- 主窗口框架布局
- Tab 容器结构
- 固定分组框 (QGroupBox)
- 固定标签 (QLabel)

### P3-2: 不适用部分

- 运行时翻译绑定 (`apply_language()`)
- 动态填充的 ComboBox
- 根据配置显示/隐藏的控件
- 信号槽连接

### P3-3: 步骤

1. Qt Designer 创建 `mainwindow.ui` (仅静态框架)
2. `pyuic6 -x mainwindow.ui -o ui_mainwindow.py`
3. MainWindow 继承生成的类
4. 代码补充动态部分
5. 重写 `retranslateUi()` 调用 `apply_language()`

---

## 执行顺序

```
Phase 1 (低风险，先做)
├── P1-0: 创建目录结构
├── P1-3: ConfigMixin (最大，先做)
├── P1-4: PlaybackMixin
├── P1-2: SettingsPresetMixin
├── P1-5: HotkeysMixin
├── P1-1: LanguageMixin
└── P1-6: LogsMixin (最小)

Phase 2 (Tab Builder 函数)
└── P2-1: 提取 5 个 Tab Builder 函数

Phase 3 (可选，评估后决定)
├── P3-1: 框架布局
└── P3-2: 固定控件
```

---

## 验收命令

```powershell
# 1. 行数检查
wc -l d:/dw11/piano/LyreAutoPlayer/main.py
# Phase 1: 预期 ≤ 1600
# Phase 2: 预期 ≤ 1100

# 2. 语法检查
cd d:/dw11/piano/LyreAutoPlayer
python -m py_compile main.py
python -m py_compile ui/mixins/*.py

# 3. 导入检查
python -c "from main import MainWindow; print('OK')"

# 4. 启动测试
python main.py
# 预期: 窗口正常显示

# 5. 功能测试
# - 切换语言 → UI 文本更新
# - 加载 MIDI → 播放正常
# - 热键 F5-F12 响应正常
# - 键盘预设切换正常
```

---

## 审计修正记录

| 问题 | 修正 |
|------|------|
| Phase 2 Tab 拆分与约束冲突 | 改为 Tab Builder 函数，控件仍挂在 main.py |
| Tab 命名与实际不一致 | 更正为 Main/Keyboard/Shortcuts/Input Style/Errors |
| PresetsMixin 方法不匹配 | 重命名为 SettingsPresetMixin，使用实际方法名 |
| HotkeysMixin 示例错误 | 更正为 F5-F12 + on_press_key |
| LanguageMixin 削减不明确 | 降低预期，保留 apply_language 在 main.py |
| 概述表与验证目标不一致 | 统一为 ≤1600/≤1100/≤800 |
| 行号硬编码可能误导 | 改为"行号仅参考" |

---

*计划创建时间: 2026-01-02*
*审计修正时间: 2026-01-02*
*基于用户提供的详细重构路径 + 审计反馈*
