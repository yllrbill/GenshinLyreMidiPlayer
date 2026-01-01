# Context Pack for 20260102-2142-unify-config-schema-and-persistence

> 固定 6 段结构，每段 3-6 行

## 1. Goal
统一配置字段结构与序列化契约，消除 `save_settings()` 与 `_collect_current_settings()` 之间的字段漂移。

## 2. What's Done
- (初始状态：无)

## 3. Current Blocker / Decision Needed
- 需要确认目标结构：采用扁平还是嵌套？
- 需要分析现有配置文件兼容性需求

## 4. Evidence Index
| File | Path | Summary |
|------|------|---------|
| request.md | ./ | 任务定义 |
| config_mixin.py | LyreAutoPlayer/ui/mixins/ | save_settings 扁平结构 |
| settings_preset_mixin.py | LyreAutoPlayer/ui/mixins/ | _collect_current_settings 嵌套结构 |

## 5. Minimal Files to Read
1. ops/ai/tasks/20260102-2142-unify-config-schema-and-persistence/request.md
2. LyreAutoPlayer/ui/mixins/config_mixin.py (save_settings 方法)
3. LyreAutoPlayer/ui/mixins/settings_preset_mixin.py (_collect_current_settings 方法)

## 6. Next Actions Candidates
- [ ] A: 分析两个方法的字段差异，生成对比表
- [ ] B: 确定统一结构（扁平/嵌套）并制定迁移计划

---
*Generated: 2026-01-02 21:42*
