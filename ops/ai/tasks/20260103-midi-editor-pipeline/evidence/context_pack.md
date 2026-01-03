# Context Pack - 20260103-midi-editor-pipeline

## Task ID
20260103-midi-editor-pipeline

## Status
DONE - Phase 1 + 1.5 + 2 + Optimization Fixes + Session 2 (2026-01-04)

## Goal
实现钢琴卷帘编辑器基础编辑功能 + 时间轴BPM/小节显示

## Key Files (按重要性排序)
| File | Lines Changed | Purpose |
|------|---------------|---------|
| ui/editor/timeline.py | +191 | 时间轴: BPM显示/小节号/拍刻度 (优化可视范围) |
| ui/editor/piano_roll.py | +34 | 钢琴卷帘: 选择/移动/网格 (scene宽度修复) |
| ui/editor/note_item.py | +41 | 音符图形: 拖拽/边界/"音符"标签 |
| ui/editor/editor_window.py | +6 | 主窗口: tempo传递到timeline |

## Phase 1.5 Timeline Features
1. BPM显示 (动态字号基于ROW_BAR)
2. 小节号显示 (基于time_signature)
3. 拍刻度线 (下拍粗线/其他细线)
4. 秒刻度保留 (不回归)

## Optimization Fixes (Final Session)
| Issue | Fix |
|-------|-----|
| `_generate_beat_ticks()` 性能 | 直接跳到可视tick范围,不从0迭代 |
| "音符"标签显示条件 | 仅蓝色普通状态 (非selected/out_of_range) |
| 网格右侧空白 | scene宽度 = max(content, scroll_offset + viewport) |
| 窗口大小变化 | 添加resizeEvent()触发网格重绘 |

## Key Methods Added
```python
# timeline.py
def _second_to_tick(self, t: float) -> int  # 秒转tick (逆向查tempo_map)
def _generate_beat_ticks(start, end) -> List[Tuple[int, bool, int]]  # 可视范围拍子

# note_item.py
def paint(painter, option, widget)  # 自定义绘制+居中"音符"标签

# piano_roll.py
def _calc_scene_width() -> float  # scroll_offset + viewport_width
def resizeEvent(event)  # 窗口大小变化时重绘
```

## Acceptance Checklist
- [x] 时间轴显示秒数刻度
- [x] 时间轴显示BPM (默认120)
- [x] 时间轴显示小节号与拍刻度线
- [x] MIDI tempo/time_signature正确解析
- [x] UI高度对齐 (corner = timeline)
- [x] 拍子生成仅限可视范围 (性能)
- [x] 音符标签仅普通状态显示
- [x] 网格覆盖滚动位置+视口
- [x] 语法检查通过

## Session 2 Changes (2026-01-04)

| Category | Changes |
|----------|---------|
| Shortcuts Help | 补全 `_show_shortcuts_help()` 所有快捷键; Space pan 模式焦点说明; Alt+Click/Drag 说明 |
| BPM/Tempo 文案 | spinbox tooltip 明确仅影响网格/导出; 右键菜单 "Set BPM (Grid/Export)"; 保存对话框提示 |
| Path Handling 文档 | STATE.md Known Issues P2 风险降级; handoff.md 多重回退策略; Search Constraints 章节 |
| 新功能 | Audio checkbox 静音预览; HumanizeCommand (H/Shift+H/Ctrl+H); floating.py 简化版 UI |

## Dependencies
- mido (MIDI解析)
- PyQt6 (GUI)
