---
description: 启动/恢复：盘点仓库状态、读取docs入口、生成计划后停止
---

## Context
First, run these commands to understand the current state:
1. `git status` - check working tree status
2. `git rev-parse --short HEAD` - get current commit hash

## Your task

### Step 1: 读取核心文档

**必须读取以下文件**（按顺序）：

#### 1.1 私有交接文档（优先）

首先尝试读取私有 HANDOFF：
```
.claude/private/HANDOFF.md
```

如果私有版本存在，**优先使用**（包含完整敏感信息）。

如果私有版本不存在，读取公开版本：
```
analydocs/HANDOFF.md
```

HANDOFF 包含：
- TL;DR (关键结论)
- Blockers (当前阻塞点)
- Next Steps (推荐执行步骤)
- Acceptance Status (验收状态)

#### 1.2 历史归档文档（新增）

**同时读取对应层级的 handoff-archive**：

- 若使用私有 HANDOFF → 读取 `.claude/private/handoff-archive.md`（如存在）
- 若使用公开 HANDOFF → 读取 `analydocs/handoff-archive.md`（如存在）
- **文件不存在时**: 记录"无归档文件"并继续

**归档用途**:
- 提取最近 1-3 条归档的关键信息
- 识别长期阻塞点（多次出现的 blocker）
- 避免重复踩坑（已排除方案）
- 检查是否有内容应沉淀到骨架但未沉淀

#### 1.3 工具指南（如存在）

```
.claude/rules/35-tool-guide.md
```

#### 1.4 已排除方案（如存在）

```
.claude/rules/40-excluded-paths.md
```

### Step 2: 读取验收标准

- `analydocs/ACCEPTANCE.md` - 核心验收标准

### Step 3: 生成本会话作战计划

基于读取的文档，输出以下格式：

```markdown
## 本会话作战计划

### 当前状态
- **核心阻塞**: <从 HANDOFF.md Blockers 提取>
- **验收状态**: <各项状态>
- **HANDOFF 来源**: <私有版本/公开版本>
- **归档状态**: <有归档 (N条)/无归档文件>

### 近期归档摘要（最近 1-3 次会话）
<从 handoff-archive.md 提取关键信息，若无归档则写"无历史归档">
- Session N-1: <TL;DR 要点>
- Session N-2: <TL;DR 要点>

### 已排除方案 (禁止重试)
<合并 40-excluded-paths.md 与归档中的失败方案>
- EP-*: <方案名称> - <排除原因>
- 归档排除: <来自历史会话的失败方案>

### 推荐执行步骤
<从 HANDOFF.md Next Steps 提取，或根据当前状态调整>

### 验收命令
<本次会话的验收命令>
```

### Step 4: 输出计划后停止

**CRITICAL**: 输出作战计划后，**停止并等待用户确认**，不自动执行。

行为：
1. 输出作战计划（Step 3 的格式）
2. **停止** - 等待用户确认或调整
3. 用户确认后，使用 TodoWrite 写入 TODO 并开始执行

**用户确认方式**:
- 用户回复"执行"/"开始"/"go" 等 → 开始执行
- 用户回复调整指令 → 修改计划后再次输出
- 用户回复具体任务 → 跳过计划，直接执行该任务

### Step 5: 执行完成摘要

执行完成后输出：

```markdown
## Bootstrap 执行完成

### 执行结果
| TODO | 状态 | 备注 |
|------|------|------|
| <任务1> | DONE/BLOCKED | <结果> |
| <任务2> | DONE/BLOCKED | <结果> |

### 新发现/变化
<本次执行中的新发现>

### 下一步
- 继续当前任务 OR
- 运行 /handoff 保存进度
```
