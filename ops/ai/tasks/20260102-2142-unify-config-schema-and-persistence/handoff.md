# Handoff - 20260102-2142-unify-config-schema-and-persistence

## Status: DONE

## Summary
统一了 `save_settings()` 与 `_collect_current_settings()` 的配置字段结构，采用嵌套格式（error_config, eight_bar_config），并添加了旧扁平格式兼容性处理。

## Changes

### config_mixin.py (299 → 337 行, +38 行)
- `save_settings()`: 重写为复用 `_collect_current_settings()`，消除重复逻辑
- `load_settings()`: 重写为读取嵌套结构，添加 `_migrate_settings()` 兼容处理
- 新增 `_migrate_settings()`: 旧扁平格式自动迁移到嵌套格式

### settings_preset_mixin.py (248 → 295 行, +47 行)
- `_collect_current_settings()`: 补齐 soundfont_path, last_midi_path, eight_bar_config
- `_apply_settings_dict()`: 添加 eight_bar_config 应用逻辑

## Unified Settings Structure

```json
{
  "version": 1,
  "language": "...",
  "root_note": 60,
  "octave_shift": 0,
  "transpose": 0,
  "speed": 1.0,
  "press_ms": 25,
  "countdown_sec": 2,
  "keyboard_preset": "...",
  "use_midi_duration": false,
  "play_sound": false,
  "velocity": 90,
  "input_style": "mechanical",
  "enable_diagnostics": false,
  "soundfont_path": "",
  "last_midi_path": "",
  "input_manager": {},
  "custom_styles": [],
  "error_config": {
    "enabled": false,
    "errors_per_8bars": 1,
    "wrong_note": false,
    "miss_note": false,
    "extra_note": false,
    "pause_error": false,
    "pause_min_ms": 300,
    "pause_max_ms": 800
  },
  "eight_bar_config": {
    "enabled": false,
    "mode": "warp",
    "pattern": "skip2_pick1",
    "speed_min": 90,
    "speed_max": 110,
    "timing_min": 90,
    "timing_max": 110,
    "duration_min": 90,
    "duration_max": 110,
    "show_indicator": true
  }
}
```

## Backward Compatibility

`_migrate_settings()` 处理以下迁移：
- `countdown` → `countdown_sec`
- `error_enabled`, `error_freq`, ... → `error_config.enabled`, `error_config.errors_per_8bars`, ...
- `eight_bar_enabled`, `eight_bar_mode`, ... → `eight_bar_config.enabled`, `eight_bar_config.mode`, ...
- 默认值：`version=1`, `transpose=0`

## Verification

- Syntax check: OK
- Import check: OK
- Regression tests: 14/14 passed (证据: LyreAutoPlayer/.claude/state/regression/mixin_refactor_20260102.json)

## Files Modified

| File | Before | After | Delta |
|------|--------|-------|-------|
| config_mixin.py | 299 | 337 | +38 |
| settings_preset_mixin.py | 248 | 295 | +47 |

## Technical Notes

1. `save_settings()` 现在直接调用 `_collect_current_settings()` 获取统一结构
2. 兼容性迁移在 `load_settings()` 入口执行，对后续代码透明
3. `custom_styles` 仍单独处理（需要访问 style_manager）

---
*Completed: 2026-01-02 21:50*
