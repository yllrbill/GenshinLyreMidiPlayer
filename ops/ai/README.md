# Dual-Agent Workflow (ChatGPT Planner + Claude Executor)

## Roles
- **ChatGPT = Planner (决策层)**：只产出 plan.md / patch.diff / 验收标准，不直接改仓库、不跑命令。
- **Claude Code = Executor (执行层)**：按 plan 落地改代码、跑命令、产证据、写 handoff，并更新 STATE.md。

## Ground Rules
- **Single Source of Truth**: repo files under `ops/ai/**`
- **Deterministic**: 任何遍历/选择都必须 sorted，并说明规则
- **Evidence-first**: 每步要可复跑 + 可验收（日志、diff、测试输出）
- **Fail-closed**: 验收失败必须停下并写 BLOCKED

## Minimal Handoff Set (Planner should read)
- `ops/ai/state/STATE.md`
- `ops/ai/context/REPO_MAP.md` (if exists)
- `ops/ai/tasks/<TASK_ID>/request.md`
- `ops/ai/tasks/<TASK_ID>/handoff.md`
- `ops/ai/tasks/<TASK_ID>/evidence/*` (logs + diff.patch)

## Directory Structure

```
ops/ai/
├─ README.md              # 本文件：双代理协议说明
├─ state/
│  └─ STATE.md            # 当前项目状态（中期更新）
├─ context/
│  ├─ REPO_MAP.md         # 仓库地图（可定期更新）
│  ├─ DECISIONS.md        # ADR/关键决策记录
│  └─ PROMPTS.md          # 新会话开场&收尾提示词
├─ templates/
│  ├─ request.template.md
│  ├─ plan.template.md
│  ├─ handoff.template.md
│  └─ context_pack.template.md
└─ tasks/
   └─ <TASK_ID>/
      ├─ request.md
      ├─ plan.md
      ├─ patch.diff
      ├─ handoff.md
      └─ evidence/
         ├─ execute.log
         ├─ tests.log
         ├─ diff.patch
         └─ context_pack.md
```

## Workflow

### 1. New Task
1. Planner 读 STATE.md + REPO_MAP.md
2. Planner 产出 request.md + plan.md (+ patch.diff)
3. Executor 读 request.md + plan.md，给出执行计划

### 2. Execute
1. Executor 按 plan 逐步执行
2. 每步产出证据到 evidence/
3. 遇到失败 → STOP + 写 BLOCKED 到 handoff.md

### 3. Close
1. Executor 写 handoff.md
2. Executor 更新 STATE.md
3. Planner 可读 handoff.md 继续下一轮

---

*Created: 2026-01-01*
