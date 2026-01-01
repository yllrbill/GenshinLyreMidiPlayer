# Private Files (隔离区)

此目录用于存放**可能含敏感信息的原始副产物**，内容**永不提交到 Git**。

## 三落点架构

```
ops/ai/tasks/<TASK_ID>/
├── evidence/          # 可提交、可审计（必须脱敏）
│   ├── execute.log
│   ├── tests.log
│   ├── diff.patch
│   └── context_pack.md
├── scratch/           # 不提交、临时、可丢弃
│   └── tmp_*.py
└── (request.md, plan.md, handoff.md)

private/tasks/<TASK_ID>/
└── raw_*              # 永不提交（可能含敏感信息）
```

## 两段式流程：Raw → Sanitized

| 阶段 | 位置 | 提交 | 说明 |
|------|------|------|------|
| Raw | `private/tasks/<TASK_ID>/raw_*` | ❌ | 原始输出，可能含敏感信息 |
| Sanitized | `ops/ai/tasks/<TASK_ID>/evidence/*` | ✅ | 脱敏后的摘要/片段 |

**规则**：
1. 任何不确定是否敏感的输出 → 先放 `private/`
2. 需要共享 → 产一份**脱敏版**到 `evidence/`
3. `handoff.md` 中注明两边的路径

## 常见副产物分类

| 类型 | 放哪 | 原因 |
|------|------|------|
| 内存 dump (.dmp) | `private/tasks/<id>/` | 可能含敏感数据 |
| 抓包 HAR | `private/tasks/<id>/` | 可能含 token/cookie |
| 数据库片段 | `private/tasks/<id>/` | 可能含 PII |
| 日志原文 | `private/tasks/<id>/raw_*.log` | 可能含路径/账号 |
| 日志摘要 | `evidence/*.log` | 只留关键失败段 |
| 二进制提取物 | `private/tasks/<id>/` | 可能含密钥 |
| 临时测试脚本 | `scratch/tmp_*.py` | 一次性使用 |
| 可复用脚本 | 升格到 `analyzetools/` | 长期资产 |

## 脚本升格标准

临时脚本满足任意一条，从 `scratch/` 升格到正式位置：

- [ ] 以后还会用（复现 bug、回归测试）
- [ ] 能当作验收/门禁的一部分
- [ ] 不含敏感信息，或已参数化（读 env/配置）

## Git 行为

```gitignore
# private/ 下只跟踪 .gitignore 和 README.md
private/*
!private/.gitignore
!private/README.md
!private/tasks/
private/tasks/*
```

## 安全提醒

1. **.gitignore 只阻止未追踪文件**：已提交的敏感文件需要：
   ```bash
   git rm --cached <file>
   git commit -m "Remove sensitive file from tracking"
   # 如果泄露到远程，需清理历史 + 轮换密钥
   ```

2. **推荐上 gitleaks**：pre-commit 扫描，拦截疑似密钥

3. **加密后提交（可选）**：如需版本化敏感副产物，用 SOPS/age 加密

## Handoff 中如何引用

```markdown
## Evidence
- 脱敏日志: [execute.log](evidence/execute.log)
- Raw（本地）: `private/tasks/<TASK_ID>/raw_execute.log`

## Sensitive Data
本任务涉及敏感数据，原始文件在 `private/tasks/<TASK_ID>/`：
- raw_memory.dmp
- raw_network.har
```

---

*此目录由 Dual-Agent Workflow 骨架创建*
