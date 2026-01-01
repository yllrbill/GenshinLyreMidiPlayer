---
description: 生成最小复现：把当前问题固化成 analyzetools/repro/ 下可一键运行的脚本
allowed-tools: Read, Grep, Glob, LS, Bash, Write, Edit
argument-hint: [goal]
---

目标：$ARGUMENTS

要求：
- 生成 1 个最小复现脚本（优先 Python 或 PowerShell），放到 analyzetools/repro/
- 脚本必须把输入从 analyzedata/inputs 读取，输出写到 analyzedata/outputs
- 在 analydocs/RUNBOOK.md 追加"复现命令"
