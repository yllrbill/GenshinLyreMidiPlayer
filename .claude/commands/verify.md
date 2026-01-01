---
description: 验收与证据：生成/更新 manifest，跑最小验收清单，并更新 analydocs/ACCEPTANCE.md 状态
allowed-tools: Bash(python:*), Read, Write, Edit, Glob, LS
---

你的任务：
1) 运行：python analyzetools/verify/manifest.py
2) 如果 analydocs/ACCEPTANCE.md 没有可执行验收命令，补一个"最小验收命令"块（UNKNOWN -> 明确 PASS/FAIL 条件）
3) 把验收结果（PASS/FAIL/UNKNOWN）写入 analydocs/ACCEPTANCE.md，并在 analydocs/HANDOFF.md 记录本次 verify 的输出路径
