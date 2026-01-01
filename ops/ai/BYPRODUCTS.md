# Byproduct Management (副产物管理)

副产物按两条维度分流：
1. **是否需要复跑/审计** → 要不要进 Git
2. **是否可能含敏感信息** → 能不能进 Git

## 三落点架构

| 落点 | 路径 | Git | 用途 |
|------|------|-----|------|
| **evidence** | `ops/ai/tasks/<id>/evidence/` | ✅ 提交 | 可公开、可审计、已脱敏的证据 |
| **scratch** | `ops/ai/tasks/<id>/scratch/` | ❌ 忽略 | 临时脚本、一次性输出、可丢弃 |
| **private** | `private/tasks/<id>/` | ❌ 隔离 | 可能含敏感信息的原始副产物 |

```
ops/ai/tasks/<TASK_ID>/
├── request.md
├── plan.md
├── handoff.md
├── evidence/           # ✅ 可提交（必须脱敏）
│   ├── execute.log     # 关键输出摘要
│   ├── tests.log       # 测试结果
│   ├── diff.patch      # 代码变更
│   └── context_pack.md # Planner 上下文包
└── scratch/            # ❌ 不提交（临时）
    └── tmp_*.py

private/tasks/<TASK_ID>/
└── raw_*               # ❌ 永不提交（敏感）
```

## 两段式流程

```
Raw (可能敏感)          Sanitized (可共享)
─────────────────────────────────────────
private/tasks/<id>/  →  ops/ai/tasks/<id>/evidence/
    raw_execute.log  →      execute.log (只留关键段)
    raw_memory.dmp   →      memory_summary.md
    raw_network.har  →      api_calls.md (脱敏)
```

**规则**：
1. 任何不确定是否敏感 → 先放 `private/`
2. 需要共享 → 产一份脱敏版到 `evidence/`
3. `handoff.md` 中注明两边路径

## 分类决策树

```
新产物
  ├── 可能含敏感信息？
  │     ├── 是 → private/tasks/<id>/raw_*
  │     │         └── 需要共享？→ 脱敏后放 evidence/
  │     └── 否 → 继续判断
  │
  ├── 需要长期保留/审计？
  │     ├── 是 → evidence/（确保已脱敏）
  │     └── 否 → scratch/（临时）
  │
  └── 临时脚本是否要升格？
        ├── 以后还会用 → 升格到 analyzetools/
        ├── 可当验收门禁 → 升格到 analyzetools/verify/
        └── 一次性 → 留在 scratch/
```

## 常见副产物对照表

| 类型 | 落点 | 原因 |
|------|------|------|
| 内存 dump (.dmp) | private/ | 可能含敏感数据 |
| 网络抓包 (.har) | private/ | 可能含 token/cookie |
| 数据库片段 | private/ | 可能含 PII |
| 原始日志 | private/raw_*.log | 可能含路径/账号/密钥 |
| 日志摘要 | evidence/*.log | 只留关键失败段 |
| 二进制提取物 | private/ | 可能含密钥 |
| 字幕提取 (.srt) | evidence/ 或 private/ | 看内容是否敏感 |
| 临时测试脚本 | scratch/tmp_*.py | 一次性使用 |
| 可复用脚本 | analyzetools/ | 长期资产 |
| diff/patch | evidence/ | 代码变更记录 |
| 测试结果 | evidence/ | 验收证据 |
| Context Pack | evidence/ | Planner 交接 |

## 脚本升格标准

临时脚本满足**任意一条**，从 `scratch/` 升格：

- [ ] 以后还会用（复现 bug、回归测试、重复提取）
- [ ] 能当作验收/门禁的一部分
- [ ] 不含敏感信息，或已参数化（读 env/配置，不写死 secrets）

**升格目标**：
- 通用工具 → `analyzetools/tools/`
- 复现脚本 → `analyzetools/repro/`
- 验收脚本 → `analyzetools/verify/`

## Handoff 中的引用格式

```markdown
## Evidence Index

| File | Location | Status | Description |
|------|----------|--------|-------------|
| execute.log | evidence/ | ✅ | 执行日志摘要 |
| raw_execute.log | private/tasks/<id>/ | 🔒 | 原始日志（本地） |
| tests.log | evidence/ | ✅ | 测试结果 |
| diff.patch | evidence/ | ✅ | 代码变更 |

## Sensitive Data

本任务涉及敏感数据：
- Raw files: `private/tasks/<TASK_ID>/`
- 需要访问原始数据时，本地查看上述路径
```

## .gitignore 规则

```gitignore
# Task scratch (never commit)
ops/ai/tasks/**/scratch/

# Evidence files with sensitive patterns
ops/ai/tasks/**/evidence/*.raw
ops/ai/tasks/**/evidence/*secret*
ops/ai/tasks/**/evidence/*token*
ops/ai/tasks/**/evidence/*credential*
ops/ai/tasks/**/evidence/*password*

# Private isolation zone
private/*
!private/.gitignore
!private/README.md
!private/tasks/
private/tasks/*
```

## 安全闸门

### 闸 1：流程默认策略
- 不确定是否敏感 → 先放 private
- 需要共享 → 产脱敏版到 evidence

### 闸 2：工具策略
- 推荐配置 [gitleaks](https://github.com/gitleaks/gitleaks) pre-commit hook
- 提交前自动扫描疑似密钥

### 闸 3：已泄露处理
```bash
# 如果敏感文件已提交
git rm --cached <file>
git commit -m "Remove sensitive file from tracking"

# 如果已推送到远程
# 1. 清理历史（git filter-branch 或 BFG）
# 2. 轮换泄露的密钥
# 3. 通知相关方
```

---

*详细说明见：`private/README.md`*
