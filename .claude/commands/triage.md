---
description: 故障定位：从日志/报错/复现命令出发，给出最小复现与定位路径
allowed-tools: Read, Grep, Glob, LS, Bash, WebSearch, WebFetch
argument-hint: [error/log/command]
---

输入：$ARGUMENTS

你的任务：
1) 把 $ARGUMENTS 归类（编译/运行/崩溃/逻辑错误/逆向证据不一致）
2) 找到最小复现入口（命令 + 输入文件）
3) 给出定位路径：优先"可观察证据"（日志、返回码、哈希变化）
4) 产出：scripts/repro/ 下应新增或更新的复现脚本建议
