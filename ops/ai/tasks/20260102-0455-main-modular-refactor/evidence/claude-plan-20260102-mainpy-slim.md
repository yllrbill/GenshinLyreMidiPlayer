# Claude Plan: main.py 精简执行计划

> 时间戳: 2026-01-02
> 项目: main-modular-refactor
> 目标: main.py 3825 行 → 400-800 行

---

## 执行概览

| 阶段 | 内容 | 预计减少 | 风险 |
|------|------|----------|------|
| Phase A | P1 常量抽取 | ~25 行 | 低 |
| Phase B | PlayerThread 迁移 | ~827 行 | 中 |
| Phase C | FloatingController 迁移 | ~393 行 | 中 |
| Phase D | 数据类+工具函数迁移 | ~348 行 | 中 |
| Phase E | UI Tab 拆分 | ~1050 行 | 高 |
| Phase F | 设置持久化合并 | ~224 行 | 中 |
| **总计** | - | **~2867 行** | - |

---

## Phase A: P1 常量抽取 (立即执行)

### A1. 时间常量抽取

**影响文件**: `LyreAutoPlayer/main.py`

**添加常量** (在导入后、类定义前):
```python
# === Timing Constants ===
DEFAULT_TEMPO_US = 500000      # 默认 tempo (微秒/拍)
DEFAULT_BPM = 120              # 默认 BPM
DEFAULT_BEAT_DURATION = 0.5    # 默认拍时长 (秒)
DEFAULT_BAR_DURATION = 2.0     # 默认小节时长 (秒)
DEFAULT_SEGMENT_BARS = 8       # 8小节为一段
```

**替换位置**:
- L318: `tempo = 500000` → `tempo = DEFAULT_TEMPO_US`
- L427: `500000` → `DEFAULT_TEMPO_US`
- L521: `bar_duration = 2.0` → `bar_duration = DEFAULT_BAR_DURATION`
- L729: `beat_duration = 0.5` → `beat_duration = DEFAULT_BEAT_DURATION`
- L745: `0.5` → `DEFAULT_BEAT_DURATION`
- L750: `2.0` → `DEFAULT_BAR_DURATION`
- L751: `0.5` → `DEFAULT_BEAT_DURATION`
- L1111: `2.0` → `DEFAULT_BAR_DURATION`

**验收**:
```powershell
cd LyreAutoPlayer && .venv/Scripts/python.exe -m py_compile main.py
```

### A2. 预设常量抽取

**添加常量**:
```python
# === Preset Constants ===
PRESET_ITEMS = [("21-key", "21-key"), ("36-key", "36-key")]
```

**替换位置**:
- L1852-1853: 预设下拉框初始化
- L2004-2005: 键盘 Tab 预设下拉框

---

## Phase B: PlayerThread 迁移

### B1. 验证 player/thread.py 完整性

**检查**: `LyreAutoPlayer/player/thread.py` 是否包含完整 PlayerThread

**验收**:
```powershell
cd LyreAutoPlayer && .venv/Scripts/python.exe -c "from player import PlayerThread; print('OK')"
```

### B2. 删除 main.py 中的 PlayerThread

**操作**: 删除 L506-1332 (约 827 行)

**替换为**:
```python
from player import PlayerThread
```

**验收**:
```powershell
cd LyreAutoPlayer && .venv/Scripts/python.exe -m py_compile main.py
```

---

## Phase C: FloatingController 迁移

### C1. 验证 ui/floating.py 完整性

**检查**: `LyreAutoPlayer/ui/floating.py` 是否包含完整 FloatingController

**验收**:
```powershell
cd LyreAutoPlayer && .venv/Scripts/python.exe -c "from ui import FloatingController; print('OK')"
```

### C2. 删除 main.py 中的 FloatingController

**操作**: 删除 L1336-1728 (约 393 行)

**替换为**:
```python
from ui import FloatingController
```

---

## Phase D: 数据类+工具函数迁移

### D1. 迁移目标

| 类/函数 | 原位置 | 目标位置 |
|---------|--------|----------|
| ErrorType | L157-194 | `player/errors.py` |
| ErrorConfig | L197-227 | `player/errors.py` |
| KeyEvent | L229-241 | `player/scheduler.py` |
| build_available_notes | L243-263 | `player/quantize.py` |
| get_octave_shift | L265-270 | `player/quantize.py` |
| quantize_note | L272-303 | `player/quantize.py` |
| NoteEvent | L306-310 | `player/midi_parser.py` |
| midi_to_events_with_duration | L313-348 | `player/midi_parser.py` |
| PlayerConfig | L350-376 | `player/config.py` |
| list_windows | L379-391 | `core/utils.py` (新建) |
| try_focus_window | L394-403 | `core/utils.py` |
| calculate_bar_and_beat_duration | L406-449 | `player/bar_utils.py` |
| plan_errors_for_group | L452-504 | `player/errors.py` |

### D2. 执行步骤

1. 验证 player/*.py 已包含这些定义
2. 在 main.py 添加导入
3. 删除 main.py 中的重复定义

---

## Phase E: UI Tab 拆分 (高风险)

### E1. 创建 Tab 模块结构

```
LyreAutoPlayer/ui/
├── __init__.py
├── floating.py          # 已存在
├── constants.py         # 已存在
├── tabs/
│   ├── __init__.py
│   ├── main_tab.py      # Tab 1: 主设置
│   ├── keyboard_tab.py  # Tab 2: 键盘
│   ├── shortcuts_tab.py # Tab 3: 快捷键
│   ├── style_tab.py     # Tab 4: 输入风格
│   └── errors_tab.py    # Tab 5: 错误设置
└── widgets/
    ├── __init__.py
    └── factories.py     # UI 工厂函数
```

### E2. UI 工厂函数 (P2)

**文件**: `LyreAutoPlayer/ui/widgets/factories.py`

```python
def create_spinbox(min_val, max_val, default, suffix=""):
    sp = QSpinBox()
    sp.setRange(min_val, max_val)
    sp.setValue(default)
    if suffix:
        sp.setSuffix(suffix)
    return sp

def create_double_spinbox(min_val, max_val, default, decimals=2):
    sp = QDoubleSpinBox()
    sp.setRange(min_val, max_val)
    sp.setValue(default)
    sp.setDecimals(decimals)
    return sp

def create_combo(items, default_data=None):
    cmb = QComboBox()
    for text, data in items:
        cmb.addItem(text, data)
    if default_data:
        for i in range(cmb.count()):
            if cmb.itemData(i) == default_data:
                cmb.setCurrentIndex(i)
                break
    return cmb

def create_label(text, suffix=":"):
    return QLabel(f"{text}{suffix}")
```

---

## Phase F: 设置持久化合并

### F1. 合并 save_settings/load_settings

**目标**: 将 L3464-3688 (224行) 合并到 `core/config.py`

**接口**:
```python
# core/config.py
class ConfigManager:
    def save_to_file(self, settings_dict: dict) -> None
    def load_from_file(self) -> dict
    def apply_to_ui(self, ui_refs: dict, settings: dict) -> None
    def collect_from_ui(self, ui_refs: dict) -> dict
```

---

## 验收检查点

### 每阶段必做

1. `python -m py_compile main.py` 通过
2. `python main.py` 可启动
3. 基本功能测试：加载 MIDI、播放、停止

### 最终验收

- [ ] main.py < 800 行
- [ ] 所有模块语法检查通过
- [ ] 程序可正常启动
- [ ] MIDI 播放功能正常
- [ ] 浮动面板功能正常
- [ ] 错误模拟功能正常
- [ ] 8-bar 变速功能正常
- [ ] 设置保存/加载正常

---

## 回滚策略

每阶段开始前：
```powershell
git stash push -m "before-phase-X"
```

阶段失败时：
```powershell
git stash pop
```

---

*Created: 2026-01-02*
*Task: 20260102-0251-main-modular-refactor*
