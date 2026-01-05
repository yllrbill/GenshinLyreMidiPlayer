# Plan: 20260103-midi-editor-pipeline

## Goal/Scope
完成 Session 13 的 BPM/tempo 保留修复验收，确保保存/重载与播放滚动一致性，不引入新的编辑回归。

## Constraints/Assumptions
- 保持 PyQt6 + mido 现有流程不变；模块独立，不影响现有播放逻辑。
- time_signature denominator 使用实际值（4=四分音符），避免指数化导致小节线密度翻倍。
- 已有修复在本次计划中以验证为主，失败才进入修复。

## 完成摘要
| 任务 | 状态 | 详情 |
| --- | --- | --- |
| mido denominator 验证 | ✅ | 实测 mido 使用实际值，非指数 |
| 修复 denom_log 错误 | ✅ | `ui/editor/editor_window.py:1354-1366` |
| 语法验证证据 | ✅ | tests.log 6/6 模块导入成功 |
| Stretch 归零证据 | ✅ | commit 2789fbe，line 1027-1028 |
| bar_boundaries_sec 链路 | ✅ | config:54 → playback_mixin:49 → editor:2168 → thread:102,445,676 |
| clip=True 行号 | ✅ | editor:572,679 / midi_parser:33 / thread:433,746 |
| 关键修复 | ✅ | mido MetaMessage('time_signature') 期望实际 denominator 值（4=四分音符），原代码错误地转为指数（4→2），导致保存后重载小节线密度翻倍 |

## 实施计划
1. 复核完成摘要与修复点，确认无重复检查项。
2. 执行验收测试：拉长小节→保存→重载；播放自动翻页观察 KeyList 同步；播放含黑键记录日志分类。
3. 若验收失败，定位到 `ui/editor/editor_window.py`、`ui/editor/key_list_widget.py`、`player/thread.py` 或 `midi_parser` 修复并回归。
4. 验收通过后补齐测试记录并提交。

## Acceptance Checklist
- [ ] 拉长小节→保存→重载，确认小节刻度保持
- [ ] 播放自动翻页时 KeyList 与 PianoRoll 同步
- [ ] 黑键/超音域丢弃日志包含分类（accidental/black-key 或 octave-conflict）
- [x] time_signature denominator 保持实际值，重载后小节线密度不翻倍
- [x] 基础导入验证记录（tests.log 6/6 模块导入成功）

## Risks/Dependencies
- 保存/重载路径涉及 tempo map 与 time_signature 写回，需注意与 mido 兼容性
- 验收失败可能需要跨 `editor_window.py` 与 `thread.py` 协同调整

---
*Generated: 2026-01-06 01:10*
