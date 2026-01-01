# Task: 20260101-2137-octave-policy-feature

## Goal

将 LyreAutoPlayer 的变音策略 (accidental policy) 中的 `nearest` 选项，改为通过升高或降低一个八度来匹配音符，而不是当前的"查找最近可用音符"逻辑。

### 当前行为 (`nearest`)
当一个 MIDI 音符不在可用键位范围内时，`nearest` 策略会查找距离最近的可用音符（可能跨越多个半音）。

### 期望行为 (`octave_shift` 或替换 `nearest`)
当一个 MIDI 音符不在可用键位范围内时：
1. 尝试向上移动 1 个八度 (+12 半音)
2. 尝试向下移动 1 个八度 (-12 半音)
3. 选择能够匹配到可用音符的方向
4. 如果两个方向都无法匹配，根据策略决定是 drop 还是使用最近可用

## Constraints

- 最小改动原则：只修改必要的代码
- 保持向后兼容：不破坏现有的 `lower`, `upper`, `drop` 策略
- 保持 UI 一致性：如果添加新选项，需更新 UI 和翻译

## Acceptance Criteria

- [ ] 变音策略有明确的八度移位行为
- [ ] 播放时超出范围的音符优先通过八度移位匹配
- [ ] UI 中可选择此策略（如果是新增选项）
- [ ] 已有测试或手动验证通过

## Affected Files (Estimated)

| 文件 | 修改内容 |
|------|----------|
| `LyreAutoPlayer/main.py` | `quantize_note()` 函数逻辑 (L448-468) |
| `LyreAutoPlayer/main.py` | UI ComboBox 选项 (L1921) |
| `LyreAutoPlayer/main.py` | 翻译字典 (L152) |

## Planner Inputs

1. `ops/ai/tasks/20260101-2137-octave-policy-feature/request.md` (本文件)
2. `ops/ai/context/PLANNER_PACK.md`
3. `LyreAutoPlayer/main.py` (核心逻辑)
4. `LyreAutoPlayer/keyboard_layout.py` (八度相关函数)

## Technical Notes

### 当前 `quantize_note` 实现 (main.py L448-468)

```python
def quantize_note(note: int, available: List[int], policy: str) -> Optional[int]:
    if note in available:
        return note
    if policy == "drop":
        return None
    sorted_av = sorted(available)
    if policy == "lower":
        lowers = [n for n in sorted_av if n <= note]
        return lowers[-1] if lowers else sorted_av[0]
    if policy == "upper":
        uppers = [n for n in sorted_av if n >= note]
        return uppers[0] if uppers else sorted_av[-1]
    # nearest (default)
    best = None
    best_dist = 10**9
    for n in sorted_av:
        d = abs(n - note)
        if d < best_dist or (d == best_dist and n < best):
            best_dist = d
            best = n
    return best
```

### 建议实现方向

**选项 A**：替换 `nearest` 逻辑为八度优先
- 修改 `nearest` 的默认行为
- 无需 UI 更改

**选项 B**：新增 `octave` 策略
- 保留 `nearest`，添加新的 `octave` 选项
- 需要更新 UI 和翻译

---
*Created: 2026-01-01 21:37*
