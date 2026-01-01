# Context Pack for <TASK_ID>

> 固定 6 段结构，每段 3-6 行，避免长篇

## 1. Goal
(目标一句话，从 request.md 提取)

## 2. What's Done
(已完成的工作，列文件路径/函数名)
- path/to/file1.py: 实现了 XXX
- path/to/file2.md: 更新了 YYY

## 3. Current Blocker / Decision Needed
(要 ChatGPT Planner 决策的点，明确写出问题)
- 问题 1: ...
- 问题 2: ...
- 需要决策: A 方案 vs B 方案

## 4. Evidence Index
| File | Path | Summary |
|------|------|---------|
| execute.log | evidence/ | (关键结果或 N/A) |
| tests.log | evidence/ | (pass/fail 数量) |
| diff.patch | evidence/ | (N files, +X/-Y lines) |

## 5. Minimal Files to Read
(最多 3-6 个文件，按重要性排序)
1. ops/ai/tasks/<TASK_ID>/request.md - 任务定义
2. ops/ai/tasks/<TASK_ID>/evidence/diff.patch - 当前改动
3. path/to/key_file.py - 核心实现

## 6. Next Actions Candidates
(2-3 条候选路径，让 Planner 选择)
- [ ] A: 继续实现 XXX 功能
- [ ] B: 先修复 YYY 问题
- [ ] C: 需要更多信息才能决定

---
*Generated: YYYY-MM-DD HH:MM*
