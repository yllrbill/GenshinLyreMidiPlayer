# Task Request: MIDI 预处理/编辑管线

## TASK_ID
20260103-midi-editor-pipeline

## Created
2026-01-03

## Goal
打开 MIDI 后进入"谱面编辑界面"，实现可视化 + 可编辑 + 可预听的钢琴卷帘编辑器。

## 核心约束
- **独立模块**: 作为 LyreAutoPlayer 的新功能模块，不影响现有播放流程
- **PyQt6**: 使用现有 GUI 框架
- **mido 兼容**: 使用现有 MIDI 库 (mido) 进行读写
- **渐进式**: 可分阶段实现，先基础编辑，后高级功能

## Core Features

### Phase 1: 基础可视化与播放
1. **钢琴卷帘显示**
   - 按时间轴水平展开音符
   - 纵轴为音高 (MIDI note number)
   - 支持缩放和滚动

2. **预览播放**
   - 播放按钮 (使用现有音效/MIDI 输出)
   - 进度条显示当前播放位置
   - 进度条可拖动跳转

### Phase 2: 基础编辑
1. **选择**
   - 单击选中音符
   - 框选多个音符
   - Ctrl+A 全选

2. **编辑**
   - 移动音符 (拖拽改变时间/音高)
   - 删除音符 (Delete 键)
   - 复制粘贴 (Ctrl+C / Ctrl+V)

### Phase 3: 高级编辑
1. **添加音符**
   - 双击空白处添加
   - 指定时值

2. **批量操作**
   - 按音域筛选选中
   - 音符移调 (±半音/±八度)
   - 时间偏移/拉伸

### Phase 4: 超音域处理预览
1. **超音域标记**
   - 高亮超出当前键盘布局范围的音符
   - 显示将应用的处理策略 (skip/drop/shift/octave)

2. **处理预览**
   - 执行超音域处理后显示变更后的谱面
   - 对比视图 (原始 vs 处理后)

## 参考
- openmusic.ai 的钢琴卷帘编辑器样式与交互
- LMMS / FL Studio 的 Piano Roll 界面

## Success Criteria
- [ ] 能加载 MIDI 并显示钢琴卷帘视图
- [ ] 能播放并显示播放位置
- [ ] 能选择和移动音符
- [ ] 能删除和复制粘贴音符
- [ ] 能显示超音域音符标记

## Dependencies
- mido (已安装)
- PyQt6 (已安装)
- 现有 LyreAutoPlayer 架构

## Technical Notes
- 可能需要自定义 QGraphicsView / QGraphicsScene 实现高性能渲染
- 考虑使用 QAbstractScrollArea 处理大型 MIDI 文件
- 播放同步需要与 PlayerThread 或独立播放器协调

## Estimated Scope
| Phase | 估计复杂度 | 描述 |
|-------|-----------|------|
| Phase 1 | 中 | 可视化 + 基础播放 |
| Phase 2 | 中 | 基础编辑 |
| Phase 3 | 高 | 高级编辑 |
| Phase 4 | 中 | 超音域预览 |

---
*Created from handoff.md New Task Proposal*
