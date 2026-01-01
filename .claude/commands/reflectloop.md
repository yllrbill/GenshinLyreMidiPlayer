---
description: 可复跑沙箱执行器 - 在隔离环境中执行 plan.latest.yaml
argument-hint: [--mode auto|worktree|copy] [--max-retries N]
---

# /reflectloop Command

> **唯一事实源**: [.claude/skills/reflectloop-core/SKILL.md](../skills/reflectloop-core/SKILL.md)
>
> 本文件仅作为调用入口（thin wrapper），所有契约、协议、错误码定义请参见 Skill 文档。

## 快速开始

```powershell
# 默认执行（使用 plan.latest.yaml）
python -X utf8 analyzetools/reflectloop_sandbox.py

# 指定 plan 文件
python -X utf8 analyzetools/reflectloop_sandbox.py --plan custom_plan.yaml

# 强制使用复制模式
python -X utf8 analyzetools/reflectloop_sandbox.py --mode copy
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--plan` | `.claude/state/thinking/plan.latest.yaml` | Plan 文件路径 |
| `--mode` | `auto` | 沙箱模式: auto, worktree, copy |
| `--max-retries` | `2` | 最大重试次数（调用方控制） |

## 验收测试

```powershell
python -X utf8 analyzetools/verify/verify_reflectloop.py
```

## 相关文档

- [SKILL.md](../skills/reflectloop-core/SKILL.md) - 唯一事实源（契约、错误码、Secret-Safe）
- [ROUTING.md](../skills/reflectloop-core/ROUTING.md) - 集成规则
- [reflectloop-envelope.md](../rules/reflectloop-envelope.md) - 规范附录

---

*Thin wrapper - 详细规范请参见 Skill 文档*
