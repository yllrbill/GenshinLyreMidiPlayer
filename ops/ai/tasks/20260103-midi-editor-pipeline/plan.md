# 执行计划: MIDI 编辑管线

## 概述

| 阶段 | 目标 | 预计文件 | 风险 |
|------|------|----------|------|
| Phase 1 | 钢琴卷帘可视化 + 播放 | ~500 行 | 中 |
| Phase 2 | 基础编辑 (选择/移动/删除) | ~300 行 | 中 |
| Phase 3 | 高级编辑 (添加/批量操作) | ~400 行 | 高 |
| Phase 4 | 超音域处理预览 | ~200 行 | 低 |

> **核心约束**: 独立模块，不影响现有播放流程；使用 PyQt6 + mido

## Phase 1: 钢琴卷帘可视化 + 播放

### P1-1: 创建编辑器模块目录

**目标**: `ui/editor/`

```
ui/editor/
├── __init__.py
├── piano_roll.py      # PianoRollWidget (QGraphicsView)
├── note_item.py       # NoteItem (QGraphicsRectItem)
├── timeline.py        # TimelineWidget (顶部时间轴)
├── keyboard.py        # KeyboardWidget (左侧键盘)
└── editor_window.py   # EditorWindow (主窗口/对话框)
```

---

### P1-2: PianoRollWidget

**文件**: `ui/editor/piano_roll.py`

**类结构**:
```python
class PianoRollWidget(QGraphicsView):
    """钢琴卷帘主视图"""

    sig_note_selected = pyqtSignal(list)  # 选中的音符列表
    sig_playback_position = pyqtSignal(float)  # 播放位置 (秒)

    def __init__(self, parent=None):
        self.scene = QGraphicsScene()
        self.notes: List[NoteItem] = []
        self.pixels_per_beat = 50  # 水平缩放
        self.pixels_per_note = 10  # 垂直缩放 (每个半音)
        self.playhead: QGraphicsLineItem  # 播放头

    def load_midi(self, midi_data: mido.MidiFile):
        """加载 MIDI 并创建音符图形项"""

    def set_zoom(self, h_zoom: float, v_zoom: float):
        """设置缩放比例"""

    def set_playhead_position(self, time_sec: float):
        """更新播放头位置"""

    def wheelEvent(self, event):
        """Ctrl+滚轮缩放"""
```

**预计**: ~150 行

---

### P1-3: NoteItem

**文件**: `ui/editor/note_item.py`

**类结构**:
```python
class NoteItem(QGraphicsRectItem):
    """单个音符的图形表示"""

    def __init__(self, note: int, start_time: float, duration: float, velocity: int):
        self.note = note          # MIDI 音高 (0-127)
        self.start_time = start_time  # 起始时间 (秒)
        self.duration = duration  # 时值 (秒)
        self.velocity = velocity  # 力度
        self.selected = False
        self.out_of_range = False  # 超音域标记

    def paint(self, painter, option, widget):
        """绘制音符（普通/选中/超音域不同颜色）"""

    def mousePressEvent(self, event):
        """选中处理"""

    def mouseMoveEvent(self, event):
        """拖拽移动（Phase 2）"""
```

**预计**: ~80 行

---

### P1-4: TimelineWidget

**文件**: `ui/editor/timeline.py`

**类结构**:
```python
class TimelineWidget(QWidget):
    """顶部时间轴，显示小节/拍号"""

    sig_seek = pyqtSignal(float)  # 点击跳转

    def __init__(self, parent=None):
        self.bpm = 120
        self.time_signature = (4, 4)
        self.pixels_per_beat = 50

    def paintEvent(self, event):
        """绘制刻度和小节线"""

    def mousePressEvent(self, event):
        """点击跳转"""
```

**预计**: ~60 行

---

### P1-5: KeyboardWidget

**文件**: `ui/editor/keyboard.py`

**类结构**:
```python
class KeyboardWidget(QWidget):
    """左侧钢琴键盘，显示音符名"""

    def __init__(self, parent=None):
        self.pixels_per_note = 10
        self.note_range = (21, 108)  # A0 to C8

    def paintEvent(self, event):
        """绘制黑白键"""
```

**预计**: ~50 行

---

### P1-6: EditorWindow

**文件**: `ui/editor/editor_window.py`

**类结构**:
```python
class EditorWindow(QMainWindow):
    """MIDI 编辑器主窗口"""

    def __init__(self, midi_file: str, parent=None):
        self.midi = mido.MidiFile(midi_file)
        self.piano_roll = PianoRollWidget()
        self.timeline = TimelineWidget()
        self.keyboard = KeyboardWidget()
        self.toolbar: QToolBar
        self.playback_timer: QTimer

    def _setup_ui(self):
        """布局：工具栏 + 时间轴 + (键盘 | 卷帘)"""

    def _setup_toolbar(self):
        """播放/暂停/停止按钮，缩放滑块"""

    def on_play(self):
        """开始预览播放"""

    def on_stop(self):
        """停止播放"""

    def _update_playhead(self):
        """定时器回调，更新播放头"""
```

**预计**: ~150 行

---

### Phase 1 验收

```powershell
# 语法检查
python -m py_compile ui/editor/*.py

# 导入检查
python -c "from ui.editor import EditorWindow; print('OK')"

# 功能测试
# 1. 能加载 MIDI 文件
# 2. 显示音符在正确位置
# 3. 播放时播放头移动
```

---

## Phase 2: 基础编辑

### P2-1: 音符选择

**修改**: `ui/editor/note_item.py`, `ui/editor/piano_roll.py`

**功能**:
- 单击选中 (取消其他选中)
- Ctrl+单击 多选
- 框选 (鼠标拖拽)
- Ctrl+A 全选

---

### P2-2: 音符移动

**修改**: `ui/editor/note_item.py`

**功能**:
- 拖拽改变时间 (水平)
- 拖拽改变音高 (垂直)
- 吸附到网格 (可选)
- 移动多个选中音符

---

### P2-3: 音符删除

**修改**: `ui/editor/piano_roll.py`

**功能**:
- Delete 键删除选中音符
- Backspace 键删除
- 上下文菜单 "删除"

---

### P2-4: 复制粘贴

**修改**: `ui/editor/piano_roll.py`

**功能**:
- Ctrl+C 复制选中音符
- Ctrl+V 粘贴到当前播放头位置
- Ctrl+X 剪切

---

## Phase 3: 高级编辑

### P3-1: 添加音符

**功能**:
- 双击空白处添加音符
- 默认时值 (1 拍)
- 拖拽调整时值

---

### P3-2: 批量操作

**功能**:
- 按音域筛选选中
- 移调 (+/- 半音, +/- 八度)
- 时间偏移/拉伸

---

## Phase 4: 超音域处理预览

### P4-1: 超音域标记

**修改**: `ui/editor/note_item.py`

**功能**:
- 根据当前键盘预设判断音符是否超音域
- 超音域音符用不同颜色标记

---

### P4-2: 处理预览

**功能**:
- 显示应用超音域处理后的谱面
- 对比视图 (原始 vs 处理后)

---

## 文件结构预览

```
LyreAutoPlayer/
├── ui/
│   ├── editor/
│   │   ├── __init__.py
│   │   ├── piano_roll.py      (~150 行)
│   │   ├── note_item.py       (~80 行)
│   │   ├── timeline.py        (~60 行)
│   │   ├── keyboard.py        (~50 行)
│   │   └── editor_window.py   (~150 行)
│   └── ...
├── main.py  (添加打开编辑器入口)
└── ...
```

---

## 验收命令

```powershell
# Phase 1 验收
cd d:/dw11/piano/LyreAutoPlayer
.venv/Scripts/python -m py_compile ui/editor/*.py
.venv/Scripts/python -c "from ui.editor import EditorWindow; print('OK')"

# 手动测试
.venv/Scripts/python -c "
from PyQt6.QtWidgets import QApplication
from ui.editor import EditorWindow
import sys
app = QApplication(sys.argv)
win = EditorWindow('path/to/test.mid')
win.show()
app.exec()
"
```

---

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| QGraphicsView 性能 (大型 MIDI) | 中 | 实现视口剔除，只渲染可见音符 |
| 与现有播放器冲突 | 低 | 独立模块，共享 mido 但不共享 PlayerThread |
| 复杂拖拽交互 | 中 | 分阶段实现，先基础后高级 |
| MIDI 写回 | 中 | 需要处理多轨道、控制器事件等 |

---

*计划创建时间: 2026-01-03*
*基于 handoff.md New Task Proposal*
