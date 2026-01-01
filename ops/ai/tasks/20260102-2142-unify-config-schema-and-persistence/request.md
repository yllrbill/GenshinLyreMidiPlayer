# Task: 20260102-2142-unify-config-schema-and-persistence

## Goal
统一 `save_settings()` 与 `_collect_current_settings()` 的字段结构，消除字段漂移与嵌套/扁平不一致。

## Scope
- `LyreAutoPlayer/ui/mixins/config_mixin.py`
- `LyreAutoPlayer/ui/mixins/settings_preset_mixin.py`
- 必要的常量/工具模块

## Non-Goals
- 不重构 UI
- 不改业务逻辑
- 不影响已通过的回归行为

## Constraints
- 保持向后兼容：已有配置文件可兼容加载
- 最小改动原则
- 回归测试必须通过

## Acceptance Criteria
- [ ] 单一配置结构（扁平或嵌套）统一
- [ ] 新增字段映射表或常量（如需要）
- [ ] 已有配置可兼容加载
- [ ] 回归测试 14/14 通过

## Background
来自 Task `20260102-2138-main-mixin-refactor` 的技术债务：
- `save_settings` (config_mixin:75) 使用扁平结构
- `_collect_current_settings` (settings_preset_mixin:138) 使用嵌套结构
- 当时为避免影响回归测试而推迟处理

## Planner Inputs
1. ops/ai/tasks/20260102-2142-unify-config-schema-and-persistence/request.md (本文件)
2. LyreAutoPlayer/ui/mixins/config_mixin.py
3. LyreAutoPlayer/ui/mixins/settings_preset_mixin.py
4. ops/ai/tasks/20260102-2138-main-mixin-refactor/handoff.md (技术债务来源)

---
*Created: 2026-01-02 21:42*
