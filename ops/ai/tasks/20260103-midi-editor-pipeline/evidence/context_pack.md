# Context Pack for 20260103-midi-editor-pipeline

## 1. Goal
实现钢琴卷帘 MIDI 编辑器：可视化 + 可编辑 + 可预听，分 4 阶段渐进实现。

## 2. What's Done
- ui/editor/*.py (6 files, ~745 行): PianoRollWidget, NoteItem, TimelineWidget, KeyboardWidget, EditorWindow
- main.py: _select_version(), _open_editor() 集成编辑器入口
- i18n/translations.py: 新增 original_file, select_version, select_version_prompt
- 保存目录: midi-change/ + index.json 索引
- 版本选择: last_modified 逆序、默认最新、取消加载最新

## 3. Current Blocker / Decision Needed
- 无阻塞
- 需决策: Phase 2 实现顺序
  - A: 先做选择 (点击/框选/Ctrl+A)
  - B: 先做移动 (拖拽)
  - C: 一起做 (选择+移动+删除+复制粘贴)

## 4. Evidence Index
| File | Path | Summary |
|------|------|---------|
| execute.log | evidence/ | Phase 1.5 完成，语法检查 OK |
| tests.log | evidence/ | N/A (无自动测试) |
| diff.patch | evidence/ | ops/ai 骨架更新 |

## 5. Minimal Files to Read
1. ops/ai/tasks/20260103-midi-editor-pipeline/request.md - 任务定义
2. ops/ai/tasks/20260103-midi-editor-pipeline/handoff.md - 当前进度
3. LyreAutoPlayer/ui/editor/piano_roll.py - 钢琴卷帘核心
4. LyreAutoPlayer/ui/editor/note_item.py - 音符图形项
5. LyreAutoPlayer/ui/editor/editor_window.py - 主窗口

## 6. Next Actions Candidates
- [ ] A: 实现 Phase 2 音符选择 (单击/框选/Ctrl+A)
- [ ] B: 实现 Phase 2 音符移动 (拖拽改时间/音高)
- [ ] C: 实现 Phase 2 音符删除 + 复制粘贴 (Delete/Ctrl+C/V)

---
*Generated: 2026-01-03*
