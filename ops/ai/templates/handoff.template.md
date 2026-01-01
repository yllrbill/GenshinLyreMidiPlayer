# Handoff - <TASK_ID>

## Goal
(原始目标，从 request.md 提取)

## Scope Done / Not Done
- Done:
  - (从 plan.md 或 execute.log 推断已完成的步骤)
- Not Done:
  - (未完成的步骤，标注原因)

## Changes (file list)
(从 diff.patch 提取，sorted)
- path/to/file1.py
- path/to/file2.md

## Commands Run (with evidence links)
1. `command1` → [execute.log](evidence/execute.log)
2. `command2` → [tests.log](evidence/tests.log)

## Tests/Verification
- (测试结果摘要)
- Evidence: [tests.log](evidence/tests.log)

## Evidence Index

| File | Location | Status | Description |
|------|----------|--------|-------------|
| execute.log | evidence/ | ✅/❌ | 执行日志摘要 |
| tests.log | evidence/ | ✅/❌ | 测试输出 |
| diff.patch | evidence/ | ✅/❌ | 变更补丁 |
| context_pack.md | evidence/ | ✅/❌ | Context Pack |
| review_report.md | evidence/ | ✅/❌ | Code Review |

## Sensitive Data (if any)

<!-- 如果任务涉及敏感数据，取消注释以下内容 -->
<!--
本任务涉及敏感数据，原始文件在本地：
- `private/tasks/<TASK_ID>/raw_execute.log`
- `private/tasks/<TASK_ID>/raw_*.dmp`

脱敏版已放入 evidence/，可安全共享。
-->

## Scratch Files (if any)

<!-- 临时脚本说明 -->
<!--
| File | Purpose | Upgrade? |
|------|---------|----------|
| scratch/tmp_test.py | 一次性测试 | ❌ |
| scratch/extract_data.py | 数据提取 | ✅ 升格到 analyzetools/ |
-->

## Next Steps (priority)
1. (根据测试结果或阻塞点)
2. ...

## Risks/Notes
- (bullet list)

---

*Completed: YYYY-MM-DD*
