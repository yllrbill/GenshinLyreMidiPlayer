# /repo-audit - 文件修改审计报告

> 输出本次会话的文件修改审计报告，列出所有变更文件及其行号范围。

## 用法

```
/repo-audit
```

## 功能

1. **只读审计** - 不修改任何文件
2. **全覆盖** - tracked/untracked、staged/unstaged 全部覆盖
3. **可复跑** - 输出完整命令和证据
4. **精确行号** - 从 git diff hunk header 提取变更行范围

## 输出内容

- **定位信息**: 工作目录、仓库根、当前分支、HEAD
- **总览表**: 状态、路径、staged、行范围摘要
- **逐文件细节**: 每个文件的 diff 和行号范围
- **完整 Patch**: git diff 和 git diff --cached 全文

## 执行步骤

1. `git rev-parse --show-toplevel` - 获取仓库根
2. `git status --porcelain=v1 -uall` - 获取变更清单
3. `git diff --unified=0 -- <path>` - 获取每个文件的 unstaged 变更
4. `git diff --cached --unified=0 -- <path>` - 获取每个文件的 staged 变更
5. 生成审计报告

## 输出格式

```markdown
# 文件修改审计报告

## 定位信息
| 项目 | 值 |
|------|-----|
| 工作目录 | ... |
| 仓库根目录 | ... |

## 变更总览
| 状态 | 路径 | Staged | 行范围 |
|------|------|--------|--------|
| M | file.py | No | -10,3 +10,5 |

## 逐文件细节
### [M] file.py
...

## 完整 Patch
...
```

---

调用 Skill: `repo-audit-core`
