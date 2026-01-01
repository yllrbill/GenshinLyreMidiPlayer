---
description: 会话交接：归档旧HANDOFF、写入新交接文档、沉淀骨架
---

## 会话交接流程

本命令根据**当前会话的完整上下文**，执行以下操作：
1. **归档**旧 HANDOFF 到 handoff-archive.md
2. **写入**新 HANDOFF（私有+公开）
3. **沉淀**长期内容到骨架文件

**CRITICAL**: 你可以访问本次会话的完整对话历史，请基于实际发生的操作和发现来更新文档。

---

## 执行顺序（必须按序执行）

### Phase 0: 归档旧 HANDOFF（写入新 HANDOFF 之前）

**归档文件位置**:
- 私有归档: `.claude/private/handoff-archive.md`
- 公开归档: `analydocs/handoff-archive.md`

**归档逻辑**:
1. 读取当前 HANDOFF（如存在）:
   - 私有: `.claude/private/HANDOFF.md`
   - 公开: `analydocs/HANDOFF.md`
2. 从旧 HANDOFF 提取摘要，**追加到对应归档文件顶部**（时间倒序）
3. 归档条目格式:

```markdown
---
## Archive: Session N (YYYY-MM-DD)

### TL;DR
<3-8 条要点>

### Key Verified Facts
<1-5 条本次新增的已验证事实>

### Blockers Change
- 新增: <新阻塞点>
- 解除: <已解决阻塞>

### Critical Next Steps
<最关键 3 条>

### Evidence References
- <路径/命令（公开版必须脱敏）>

---
```

4. **私有归档**: 可保留更多细节，但密钥值写为 `<REDACTED_KEY>`
5. **公开归档**: 严格脱敏（密钥/绝对路径全部替换）
6. **文件不存在时**: 创建新文件并写入第一条归档

---

## 文件写入策略

### 私有文件 (写入 .claude/private/)

以下文件写入私有目录，**不提交到 git**，包含完整敏感信息：

| 文件 | 路径 | 内容 |
|------|------|------|
| HANDOFF.md | `.claude/private/HANDOFF.md` | 完整交接文档（含敏感信息） |
| handoff-archive.md | `.claude/private/handoff-archive.md` | 历史会话归档（追加模式） |

### 公开文件 (脱敏后写入原位置)

以下文件写入原位置，**需要脱敏**：

| 文件 | 路径 | 脱敏规则 |
|------|------|----------|
| HANDOFF.md | `analydocs/HANDOFF.md` | 脱敏版本（移除密钥、路径等敏感信息） |
| handoff-archive.md | `analydocs/handoff-archive.md` | 脱敏归档（追加模式） |
| 35-tool-guide.md | `.claude/rules/35-tool-guide.md` | 增量更新（无敏感信息） |
| 40-excluded-paths.md | `.claude/rules/40-excluded-paths.md` | 增量更新（无敏感信息） |

### 脱敏规则

在写入公开文档时：

1. **密钥字符串**: 替换为 `<REDACTED_KEY>` 或 `"***"`
2. **完整路径**: 替换为相对路径或 `<PROJECT_ROOT>/...`
3. **API Key**: 绝对不能出现
4. **哈希值**: 可以保留（非敏感）

---

### 文件 1: .claude/private/HANDOFF.md (私有完整版)

**完整覆盖/更新**，基于本次会话实际内容：

1. **读取当前文件** 获取格式和历史 Session 编号
2. **回顾本次会话**：
   - 用户请求了什么？
   - 执行了哪些操作？
   - 发现了哪些新事实？
   - 遇到了哪些阻塞？
   - 下一步应该做什么？
3. **写入新内容**，包含以下章节：

```markdown
# Private Handoff - <日期> (Session N 交接)

> 此文件为私有交接文档，不提交到 git。

## TL;DR (≤10行)
<本次会话的关键结论，编号列表>

## Verified Facts
<已验证的事实，附证据路径/哈希/命令>

## Blockers (当前阻塞点)
<主要阻塞 + 已排除方法 + 未尝试方法>

## Next Steps (≤7步)
<推荐的下一步执行步骤，含命令>

## Acceptance Status
<验收清单状态: PASS/FAIL/UNKNOWN>

## Files Touched (Session N)
<读取/新增/修改的文件列表>

## Repro/Verify (可复跑命令)
<验证关键结论的命令>
```

---

### 文件 2: analydocs/HANDOFF.md (公开脱敏版)

**写入脱敏后的版本**：

1. **复制私有版本内容**
2. **应用脱敏规则**
3. **保留分析性内容**

---

### 文件 3: .claude/rules/35-tool-guide.md

**增量更新**，基于本次会话新发现：

1. **读取当前文件**
2. **如有新发现**：在对应章节添加新内容
3. **如无新发现**：保持不变

---

### 文件 4: .claude/rules/40-excluded-paths.md

**增量更新**，基于本次会话新排除：

1. **读取当前文件** 获取当前 EP-N 编号
2. **如有新排除**，添加新条目：
   ```markdown
   ### EP-N: <方案名称>
   - **排除时间**: <日期> Session N
   - **原因**: <简短原因>
   - **详情**: <具体细节>
   - **证据**: <证据路径或命令输出>
   ```
3. **如无新排除**：保持不变

---

---

### Phase 3: 骨架沉淀（长期内容写入骨架文件）

**沉淀规则**: 当本次会话产生"稳定、需要长期复用"的信息时，**必须**沉淀到对应骨架文件，不要只写在 HANDOFF。

| 内容类型 | 沉淀目标 |
|----------|----------|
| 固定的运行手册步骤/常用命令 | `analydocs/RUNBOOK.md` |
| 长期适用的排障结论/工具用法 | `.claude/rules/35-tool-guide.md` |
| 项目背景/资产/术语（新增） | `analydocs/CONTEXT.md` |
| 目标模块/入口/版本（新增） | `analydocs/TARGETS.md` |
| 固定的验收标准/命令 | `analydocs/ACCEPTANCE.md` |
| 已排除的失败方案 | `.claude/rules/40-excluded-paths.md` |

**判断标准**:
- 是否会在未来会话中重复使用？→ 沉淀
- 是否已验证且稳定？→ 沉淀
- 仅为本次会话临时状态？→ 只写 HANDOFF

**无新增长期内容时**: 骨架文件保持不变，不做无意义改动。

---

## 执行步骤

1. **Phase 0: 归档旧 HANDOFF** → 写入 handoff-archive.md
2. **读取现有文件**
3. **分析本次会话上下文**
4. **Phase 1: 写入私有 HANDOFF.md**
5. **Phase 2: 写入公开 HANDOFF.md**（脱敏）
6. **Phase 3: 骨架沉淀**:
   - 更新 35-tool-guide.md（仅当有新发现）
   - 更新 40-excluded-paths.md（仅当有新排除）
   - 更新其他骨架文件（按沉淀规则判断）
7. **输出交接摘要**

```markdown
## 交接完成

### 更新的文件
| 文件 | 状态 | 内容 |
|------|------|------|
| .claude/private/handoff-archive.md | 已追加/新建 | Session N-1 归档 |
| analydocs/handoff-archive.md | 已追加/新建 | Session N-1 归档 (脱敏) |
| .claude/private/HANDOFF.md | 已更新 | Session N 完整交接 (私有) |
| analydocs/HANDOFF.md | 已更新 | Session N 脱敏交接 (公开) |
| .claude/rules/35-tool-guide.md | <已更新/无变化> | <新增内容摘要> |
| .claude/rules/40-excluded-paths.md | <已更新/无变化> | <新增 EP-N 摘要> |
| analydocs/RUNBOOK.md | <已更新/无变化> | <骨架沉淀内容> |
| analydocs/CONTEXT.md | <已更新/无变化> | <骨架沉淀内容> |

### 下次会话启动命令
/bootstrap
```
