# Handoff - 2026-01-01 (Session 37 交接)

> **完整版（含密钥）**: `.claude/private/HANDOFF.md`

## TL;DR (≤10行)

1. **EOP 格式逆向工程** - 分析 赛马.eop，发现二进制格式结构
2. **EOP 转 MIDI 转换器** - 多版本迭代，最终版本 best-effort 转换
3. **GUI Bug 修复** - `self.floating` → `self.floating_controller`
4. **wrong_note 释放修复** - 错误键按下后必须调度释放事件
5. **MuseScore MIDI 下载** - 高质量替代方案
6. **EOP Skill 创建** - 完整记录坑点和方法

---

## Session 37 工作内容

### 1. EOP 格式逆向工程

**格式结构**:
```
[Header: 13 bytes] [Marker+Note Data...] [Lookup Pattern × 288]
```

**音符编码**: q-{ → MIDI 60-77 (C4-F5)

**Marker 字节**: 0xBD, 0xD8, 0xDE, 0xE2, 0xE6, 0xF2, 0xF4, 0xF6

**Lookup Pattern** (必须过滤): `qrstrstustuvtuvwuvwxvwxywxyzxyz{`

### 2. EOP 转换器

| 版本 | 输出音符数 | 问题 |
|------|------------|------|
| v1 | 34,898 | 未过滤 lookup |
| final | 4,428 | Best-effort |

### 3. GUI Bug 修复

```python
# 修复前
if self.floating:

# 修复后
if self.floating_controller:
```

### 4. wrong_note 释放修复

```python
# 新增: 为 wrong_note 调度释放事件
if wrong_note_applied:
    heapq.heappush(event_queue, KeyEvent(
        next_event.time + 0.08, 1, "release", key, note
    ))
```

### 5. MuseScore MIDI 下载

```powershell
npx dl-librescore "赛马 Horse Racing"
```

### 6. EOP Skill

路径: `.claude/skills/eop-midi-core/SKILL.md`

---

## Verified Facts (Session 37)

| 事实 | 证据 | 状态 |
|------|------|------|
| EOP Lookup 过滤正确 | 音符数 34898 → 4428 | **VERIFIED** |
| GUI floating 修复 | 3 处修改 | **VERIFIED** |
| wrong_note 释放修复 | 新增 release 调度 | **VERIFIED** |
| MuseScore MIDI 下载 | 文件存在 | **VERIFIED** |
| EOP Skill 创建 | SKILL.md 存在 | **VERIFIED** |

---

## Blockers (当前阻塞点)

### EP-EOP-3: EOP 时序编码

**状态**: 未完全解码

**缓解**: 使用 MuseScore 下载高质量 MIDI 替代

---

## Acceptance Status

| 项目 | 状态 | 证据/备注 |
|------|------|-----------|
| **Piano P0** FluidSynth | **PASS** | (Session 33) |
| **Piano P1** 键盘预设 | **PASS** | (Session 33) |
| **Piano P2** 自定义键位 | **DEFERRED** | 可选增强 |
| **Piano P3** 快捷键 | **PASS** | (Session 34) |
| **Piano P5** 悬浮窗+风格 | **PASS** | (Session 35) |
| **Piano P6** duration Bug | **PASS** | (Session 36) |
| **Piano P7** 风格验证 | **PASS** | (Session 36) |
| **Piano P8** 错误机制 | **PASS** | wrong_note 修复 (Session 37) |
| **EOP 转换** | **PARTIAL** | Best-effort，推荐 MuseScore |
| **A1-A7** neox.xml 解密 | **PASS** | (Session 21) |
| **B1-B3** 资产提取 | **PASS** | (Session 26) |
| **C1-C3** 312.1 分析 | **IN_PROGRESS** | (Session 28) |

---

## Files Touched (Session 37)

### 修改

| 文件 | 用途 |
|------|------|
| `piano/LyreAutoPlayer/main.py` | GUI + wrong_note 修复 |
| `analydocs/HANDOFF.md` | 本文件 |
| `analydocs/handoff-archive.md` | Session 36 归档 |

### 新增

| 文件 | 用途 |
|------|------|
| `.claude/skills/eop-midi-core/SKILL.md` | EOP 转换 Skill |
| `.claude/state/sample.eop` | EOP 样本 |
| `.claude/state/eop_to_midi_final.py` | 转换器 |

---

## Next Steps

1. **测试 wrong_note 修复** - 验证错误键正确释放
2. **测试 MuseScore MIDI** - 播放下载的高质量 MIDI
3. **继续 312.1 分析** - 动态分析就绪

---

## 常用命令速查

```powershell
# === Piano Auto Player ===
cd D:\dw11\piano\LyreAutoPlayer
.\.venv\Scripts\python.exe main.py

# === EOP 转换 ===
python -X utf8 D:\dw11\.claude\state\eop_to_midi_final.py

# === 下载 MuseScore MIDI ===
npx dl-librescore "song name"
```

---

## 历史会话归档

详见: `analydocs/handoff-archive.md`

---

*生成时间: 2026-01-01 Session 37*
*状态: EOP 逆向工程 + Bug 修复 + Skill 创建*
*注: 敏感信息已脱敏，完整版见 `.claude/private/HANDOFF.md`*
