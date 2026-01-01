# Task Request: main.py 进一步分离

## TASK_ID
20260102-0513-main-further-separation

## Created
2026-01-02 05:13

## Goal
按照推荐拆分顺序，将 main.py 从当前 1961 行进一步精简到 ~100 行。

## Reference
计划详情见: `ops/ai/tasks/20260102-0455-main-modular-refactor/plan.md` 的 "可进一步分离清单（基于 main-summary）" 章节

## 推荐拆分顺序 (12 步)

### P0 - 基础 (先做)
1. **通用工具与常量** → `core/constants.py`
2. **设置持久化** → `core/persistence.py`

### P1 - 核心功能
3. **全局热键** → `ui/hotkeys.py`
4. **播放控制** → `ui/playback_controller.py`

### P2 - UI 拆分
5. **UI Tab 拆分** → `ui/tabs/` (体积最大，最关键)
6. **语言/翻译绑定** → `ui/language_binding.py`
7. **预设与风格** → `ui/style_controller.py`
8. **配置收集与应用** → `core/settings_collector.py`

### P3 - 辅助功能
9. **错误与 8-bar 同步器** → `ui/sync_helpers.py`
10. **键盘显示/窗口/日志** → `ui/display_helpers.py`
11. **文件/音色操作** → `ui/file_handlers.py`

### P4 - 可选
12. **测试/调试入口** → `ui/debug_helpers.py`

## Success Criteria
- [ ] main.py 行数 < 200 行
- [ ] 所有模块通过 py_compile 检查
- [ ] 应用可正常启动
- [ ] 现有功能无回归

## Dependencies
- 前置任务: 20260102-0455-main-modular-refactor (DONE)
