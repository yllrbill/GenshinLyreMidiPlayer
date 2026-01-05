# Handoff - MIDI Editor Pipeline

## Session 13 (2026-01-05) - BPM/Tempo Preservation Fixes

### Goals
修复审计发现的 BPM/tempo 保存问题和 KeyList 滚动同步问题。

### Issues Fixed

| Severity | Issue | Root Cause | Fix |
|----------|-------|------------|-----|
| HIGH | 保存后重载小节刻度不拉长 | `_sync_timeline_tempo()` 覆盖多段 tempo | 仅当 `len(tempo_events) <= 1` 时调用 |
| HIGH | 保存时 tempo map 不保留 | 总是重建 tempo_events | BPM 未改动时复用 `_tempo_events_tick` |
| MEDIUM | 跨曲加载 bar_durations 污染 | 未清空旧数据 | load_midi() 开头清空 |
| MEDIUM | KeyList 拖动滚动同步问题 | blockSignals 阻止信号 | 移除 blockSignals |
| MEDIUM | 滚动条宽度不一致 | KeyList 固定 12px | 移除 QSS width |
| LOW | 音符丢弃日志模糊 | 无分类信息 | 区分 accidental vs octave |

### Evidence Index

| File | Path | Purpose |
|------|------|---------|
| context_pack.md | evidence/context_pack.md | 低 token 摘要 |
| diff.patch | evidence/diff.patch | 当前改动 (178 行) |
| execute.log | evidence/execute.log | 执行日志 |

### Verification Steps

1. **拉长小节后保存重载**
   ```
   打开 MIDI → 选择小节 → 右键调整时长 → Ctrl+S 保存 → 关闭 → 重新打开
   预期: 被拉长的小节刻度保持拉长状态
   ```

2. **播放自动翻页同步**
   ```
   打开 MIDI → 点击播放 → 观察红色播放头移动到可视区右侧 80% 时
   预期: KeyList 与 PianoRoll 同时翻页
   ```

3. **音符丢弃日志**
   ```
   打开含黑键的 MIDI → 播放
   预期: 日志显示 "Dropped N notes (accidental/black-key=X, octave-conflict=Y)"
   ```

### Current Status
- **状态**: 待验收
- **代码修改**: 已完成，语法验证通过
- **需要用户**: 手动测试验收步骤

### Next Steps
1. 用户执行验收测试
2. 验收通过后 git commit
3. 若验收失败，根据反馈调整

---

## Previous Sessions

### Session 12 (Commit: 62f4743)
Variable bar length system implementation.

### Session 11 (Commit: bd39a79)
Bar duration bug fixes (6 issues).

### Session 10 (Commit: 7b73a5d)
Bug fixes + duration adjust + auto-jitter.
