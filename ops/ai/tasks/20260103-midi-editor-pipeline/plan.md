# Plan: 20260103-midi-editor-pipeline

## Goal/Scope
在现有钢琴卷帘时间轴上补充节拍速度（BPM）与小节数显示，保持秒数刻度不回归。

## Constraints/Assumptions
- 仅改动编辑器模块（timeline.py / editor_window.py）
- 保持现有播放与保存流程不受影响
- 若 MIDI 无 tempo/time_signature，使用 120 BPM 与 4/4 作为默认值

## Plan Steps
1. 阅读 `LyreAutoPlayer/ui/editor/timeline.py` 和 `LyreAutoPlayer/ui/editor/editor_window.py` 的时间轴与 MIDI 解析逻辑。
2. 在 EditorWindow 中解析 MIDI 的 tempo/time_signature，并缓存供时间轴使用。
3. 扩展 TimelineWidget：新增 BPM 显示与小节/拍刻度线绘制逻辑（与秒刻度并存）。
4. 在加载 MIDI 时将 tempo/time_signature 传入时间轴，并确保 corner widget 高度与时间轴一致。
5. 做最小验证：加载含/不含 tempo 的 MIDI，确认秒数+BPM+小节数同时显示且播放头贯穿。

## Acceptance Checklist
- [ ] 时间轴持续显示秒数刻度
- [ ] 时间轴显示 BPM（或默认 120）
- [ ] 时间轴显示小节号与拍刻度线
- [ ] 读取 MIDI 时可正确更新 tempo/time_signature
- [ ] UI 高度对齐（corner widget 与时间轴一致）

## Risks/Dependencies
- 多 tempo / 多拍号 MIDI 的处理策略可能需要后续扩展

---
*Generated: 2026-01-03 22:57*
