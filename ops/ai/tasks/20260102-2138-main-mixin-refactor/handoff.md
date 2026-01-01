# Handoff - 20260102-2138-main-mixin-refactor

## Status: DONE (Phase 1 + Phase 2)

## Summary
Phase 1 Mixin refactoring + Phase 2 Tab Builder extraction completed.

## Metrics

| Phase | main.py lines | Target | Status |
|-------|---------------|--------|--------|
| Original | 2206 | - | - |
| Phase 1 (Mixin) | 1556 | ≤1600 | ✅ |
| Phase 2 (Tab Builder) | 1039 | ≤1100 | ✅ |
| Phase 2 i18n Fix | 1047 | - | ✅ |
| Phase 2 Placeholder i18n | 1050 | - | ✅ |

| New File | Lines | Description |
|----------|-------|-------------|
| ui/tab_builders.py | 575 | Tab building functions |
| ui/mixins/ (合计) | 910 | Mixin classes |
| i18n/translations.py | 173 | Translation dictionary (+5 keys total) |

## Evidence Index

| File | Path | Description |
|------|------|-------------|
| context_pack.md | evidence/context_pack.md | Low-token summary for Planner |
| diff.patch | evidence/diff.patch | File change summary (new files, line counts) |
| tests.log | evidence/tests.log | Regression test results (14/14 passed) |
| execute.log | evidence/execute.log | Execution steps and commands |

## What Was Done

### Phase 1 (Mixin)
1. Created `ui/mixins/` directory with 6 Mixin classes
2. Extracted methods from MainWindow to appropriate Mixins
3. Updated MainWindow to use multiple inheritance
4. Fixed missing imports and accidentally deleted functions
5. Ran regression tests (14/14 passed)
6. Audited risk assessment with user

### Phase 2 (Tab Builder)
1. Created `ui/tab_builders.py` with 5 builder functions
2. Extracted Tab construction logic from main.py `init_ui()`
3. Builder functions: `build_main_tab`, `build_keyboard_tab`, `build_shortcuts_tab`, `build_style_tab`, `build_errors_tab`
4. Widgets still attached to `window.xxx` for later reference
5. Syntax check: OK
6. Import check: OK

## Risk Assessment (Audited)

| Risk | Status | Note |
|------|--------|------|
| config_mixin vs settings_preset_mixin | VERIFIED | Field drift risk noted as tech debt |
| MRO conflicts | VERIFIED | No method name overlaps |
| try_focus_window duplicate | FIXED | Removed from main.py |
| apply_language signal | VERIFIED | Correct resolution |

## Technical Debt

**Field Drift Risk**:
- `save_settings` (config_mixin:75) uses flat structure
- `_collect_current_settings` (settings_preset_mixin:138) uses nested structure
- Short-term: No change to avoid regression
- Long-term: Consider unifying

## Clarifications
- `list_windows()` in main.py: MUST keep (used by `refresh_windows()`)
- `try_focus_window()` in main.py: DELETED (duplicate of `player/thread.py`)

## Next Actions (Optional)
1. ~~Phase 2: Tab widget extraction~~ ✅ DONE
2. Unify config field structure (tech debt cleanup) - 已在 20260102-2142 完成
3. Add LyreAutoPlayer to git tracking

## Phase 2 Key Risks

| Risk | Mitigation |
|------|------------|
| Tab order change | 保持原顺序: Main/Keyboard/Shortcuts/Input Style/Errors |
| Widget reference loss | 所有控件仍挂在 window.xxx |
| Signal connection | 部分信号在 tab_builders.py 内连接（如 cmb_preset, chk_quick_* 等），部分保留在 main.py |
| Import path | `from core import ...` + `from keyboard_layout import ...` (绝对) + `from .constants import ROOT_CHOICES` (相对) |

## Phase 2 Known Issues (Tech Debt)

| Issue | Severity | Status | Note |
|-------|----------|--------|------|
| i18n 遗漏 | LOW | ✅ FIXED | 7 个硬编码标签已抽取为 window.lbl_*，纳入 apply_language() |
| 验证证据 | LOW | ✅ FIXED | Phase 2 i18n 验证结果已写入 tests.log |
| Placeholder 文本 | LOW | ✅ FIXED | custom1/My custom style 占位符已纳入翻译 |

### Phase 2 i18n Fix Details

**Changes Made**:
1. `i18n/translations.py`: +3 translation keys (range_min, range_max, range_to)
2. `ui/tab_builders.py`: 7 labels changed to use `window.lbl_*` pattern with `tr()` calls
3. `main.py`: +8 lines in `apply_language()` for new label translations

**Labels Converted**:
- `lbl_speed_min`, `lbl_speed_max` (Speed variation)
- `lbl_timing_min`, `lbl_timing_max` (Timing variation)
- `lbl_dur_min`, `lbl_dur_max` (Duration variation)
- `lbl_pause_to` (Pause range separator "~")

**Verification**: 3/3 tests passed (see evidence/tests.log phase2_i18n_fix section)

### Phase 2 Placeholder i18n Fix Details

**Changes Made**:
1. `i18n/translations.py`: +2 translation keys (placeholder_style_name, placeholder_style_desc)
2. `ui/tab_builders.py`: 2 lines modified - `setPlaceholderText()` calls now use `tr()`
3. `main.py`: +3 lines in `apply_language()` for placeholder refresh

**Placeholders Converted**:
- `txt_style_name.setPlaceholderText()`: "custom1" → tr("placeholder_style_name")
- `txt_style_desc.setPlaceholderText()`: "My custom style" → tr("placeholder_style_desc")

**Translations**:
- placeholder_style_name: EN="custom1", ZH="自定义1"
- placeholder_style_desc: EN="My custom style", ZH="我的自定义风格"

**Verification**: 2/2 tests passed (see evidence/tests.log phase2_placeholder_i18n section)

### Speed Step Change (10% → 5%)

**Changes Made**:
1. `ui/mixins/playback_mixin.py`: 速度步长 `0.1` → `0.05` (lines 125, 127, 132, 134)
2. `i18n/translations.py`: "Speed ±10%" → "Speed ±5%" (中英文, lines 160-161)
3. `ui/floating.py`: 速度显示精度 `.1f` → `.2f` (lines 192, 221, 225)

**Affected Features**:
- F7/F8 快捷键速度调节
- 悬浮面板速度按钮
- 快捷键 Tab 文案显示

**Verification**: Syntax check passed

---

## Post-Phase 2 Enhancements (Playback + Octave Range + 8-Bar)

### Octave Range (Manual/Auto) + Floating Controls
**Summary**:
- 新增“音域阈值模式(自动/手动)”开关，默认手动。
- 新增音域阈值 Min/Max 输入，主界面与悬浮窗双向同步。
- 自动模式按“root+预设音域/键盘可用范围”取值。

**Files**:
- `ui/tab_builders.py`: 增加 `chk_octave_range_auto` + `sp_octave_min/max`
- `ui/floating.py`: 悬浮窗增加音域模式与范围输入
- `main.py`: 绑定信号 + 语言文案
- `ui/mixins/config_mixin.py`: 读取/保存/迁移 `octave_range` + `octave_range_auto`
- `ui/mixins/settings_preset_mixin.py`: presets 读写 + reset defaults
- `player/config.py`: 新增 `octave_min_note`, `octave_max_note`, `octave_range_auto`
- `i18n/translations.py`: 新增 `octave_range_mode`, `octave_range_auto`, `octave_range`

### Octave Policy Mapping Update
**Behavior**:
- `octave` 策略改为“多次 ±12”挪移，直到落入阈值范围。
- 同键冲突：若存在未移位音则丢弃移位音；若全为移位音仅保留最长。

**Files**:
- `player/quantize.py`: `octave` 映射改为循环落入范围
- `player/thread.py`: 同键冲突规则 + `shifted` 标记优化

### Playback Timing Order (Speed → 8-Bar)
**Behavior**:
1) 人性化（offset/stagger/时值变化）
2) 速度缩放
3) 八小节变速映射（warp/beat_lock）

**Files**:
- `player/thread.py`: 时间/时值映射顺序调整；8-bar 计算基于缩放后的时间轴
- `player/thread.py`: `_setup_eight_bar` 对 bar/beat duration 按 speed 缩放

### Pause-at-Bar Reliability
**Behavior**:
- 生成“每小节 pause_marker”事件用于暂停，避免提前/延迟停。
- 暂停时强制释放所有按键（含本地音效 All Notes Off）。

**Files**:
- `player/thread.py`: 插入 `pause_marker` 事件，暂停时释放按键

### 8-Bar Pattern: Continuous
**Behavior**:
- 新增“持续变化”模式，每段都应用 8-bar 变速。

**Files**:
- `ui/tab_builders.py`: 新增下拉项 `continuous`
- `player/thread.py`: pattern 处理新增 `continuous`
- `i18n/translations.py`: 新增 `pattern_continuous`
- `style_manager.py`: 文档注释更新

### Notes / Open Issue
**C1 音域未生效 + 卡顿**（待验证）:
- 若“音域阈值模式=自动”被勾选，则手动范围不生效。
- 低音可能因“同键冲突优先未移位音”被丢弃。
- 八小节变速 + 速度映射可能导致局部空档（需关闭 8-bar 验证）。

---

## Completed: Input Diagnostics (Key State Window)

**Status**: ✅ DONE

**Implementation Details**:
1. 新增 `ui/diagnostics_window.py` (~240 行)
   - `DiagnosticsWindow` 类：独立窗口，实时显示按键事件
   - `KeySource` 枚举：HOTKEY / PLAYBACK / MANUAL / UNKNOWN
   - `FilterMode` 枚举：ALL / NON_F_KEYS / NON_FUNCTION
   - 自动滚动、复制、清空功能
   - "停止时清空" 选项 (checkbox)

2. i18n 翻译 (`i18n/translations.py`)
   - 新增 17 个翻译键 (diag_window_title, diag_filter_*, show_diagnostics 等)

3. 主窗口集成 (`main.py`)
   - 新增 "诊断" 按钮 (btn_diagnostics)
   - 语言切换支持

4. Mixin 集成
   - `ui/mixins/playback_mixin.py`: 新增 `on_show_diagnostics()` 方法
   - `ui/mixins/hotkeys_mixin.py`: 热键触发时记录到诊断窗口

**Files Changed**:
| File | Lines | Description |
|------|-------|-------------|
| ui/diagnostics_window.py | +240 | 诊断窗口类 (新增) |
| ui/__init__.py | +2 | 导出 DiagnosticsWindow |
| i18n/translations.py | +17 keys | 诊断相关翻译 |
| main.py | +5 | 按钮、成员变量、信号连接 |
| ui/mixins/playback_mixin.py | +20 | on_show_diagnostics, on_stop 通知 |
| ui/mixins/hotkeys_mixin.py | +15 | _log_hotkey, 热键处理器包装 |

**Verification**:
```powershell
cd d:/dw11/piano/LyreAutoPlayer
.venv/Scripts/python -m py_compile main.py ui/diagnostics_window.py
.venv/Scripts/python -c "from main import MainWindow; print('OK')"
```

---

## New Task Proposal: MIDI 预处理/编辑管线（新文件/插件）

**Goal**:
- 打开 MIDI 后进入“谱面编辑界面”，可视化+可编辑+可预听。

**Core Features**:
- 乐谱编辑：移动/删除/添加、全选/复选、按音域筛选后批量选中。
- 快捷键：复制粘贴（Ctrl+C / Ctrl+V）。
- 预览播放：进度条可拖动，播放时显示当前播放位置。
- 调整能力：全局/分段/单音符的速度与时间调整。
- 超音域处理：执行后可看到变更后的谱面。
- 输出前确认：可编辑后再生成播放事件。

**Reference**:
- 参考 openmusic.ai 的钢琴卷帘编辑器样式与交互。

---

## Session: 2026-01-03 诊断窗口修复审计

**Status**: ✅ DONE

### 修复内容

| 文件 | 修改 | 说明 |
|------|------|------|
| ui/mixins/hotkeys_mixin.py | signal 发射 | 线程安全，避免从 keyboard 线程直接更新 Qt |
| ui/mixins/config_mixin.py | +_sync_diagnostics_state() | 统一按钮同步 + 窗口自动关闭 |
| ui/mixins/settings_preset_mixin.py | 无条件同步 | 预设应用后刷新按钮状态 |
| ui/diagnostics_window.py | KeySource try/except | 防御性处理未知 source |
| main.py | apply_language() | 语言切换同步诊断窗口 |

### 新增方法

**`_sync_diagnostics_state()`** (config_mixin.py:22-29):
```python
def _sync_diagnostics_state(self: "MainWindow"):
    """Sync diagnostics button visibility and close window if disabled."""
    enabled = getattr(self, '_enable_diagnostics', False)
    self.btn_diagnostics.setVisible(enabled)
    if not enabled and self.diagnostics_window is not None:
        self.diagnostics_window.close()
        self.diagnostics_window = None
```

### 验证命令

```powershell
# 必须使用虚拟环境 python.exe
cd /d/dw11/piano/LyreAutoPlayer
.venv/Scripts/python.exe -c "from main import MainWindow; print('OK')"
# 结果: OK
```

### 审计要点备忘
- 普通 `python` 命令会因缺少 PyQt6 失败，必须用 `.venv/Scripts/python.exe`
- `enable_diagnostics` 仅控制按钮显示，不影响诊断窗口内部功能

---
*Last Updated: 2026-01-03 (Input Diagnostics fixes)*
