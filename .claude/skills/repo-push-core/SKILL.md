---
name: repo-push-core
description: 安全自动提交流程 - commit + push + 主分支合并（含敏感文件检查）
allowed-tools: Bash(*), Read(*), Write(*)
---

# Repo Push Skill

> 在当前仓库根目录执行"安全自动提交流程"，兼容 Windows PowerShell / WSL bash。

## 触发条件

当用户请求：
- "提交并推送"
- "自动提交"
- "repo push"
- "commit and push"
- "同步到远端"

## 执行流程

### Phase 1: 证据收集

```bash
# 输出当前目录和仓库根
pwd
git rev-parse --show-toplevel

# 输出工作区状态（机器可读格式）
git status --porcelain=v1 -uall
```

**输出格式**：
```yaml
evidence:
  cwd: <pwd output>
  repo_root: <git rev-parse output>
  status_lines: <line count>
  status_raw: |
    <git status output>
```

### Phase 2: 无变更检查

```bash
# 检查是否有变更
git status --porcelain=v1 -uall | wc -l
```

**如果输出为 0**：
```yaml
result:
  status: NO_CHANGES
  message: "工作区无变更，无需提交"
```
→ **退出**

### Phase 3: 同步远端

```bash
# 先拉取远端变更
git pull --rebase --autostash
```

**检查是否处于 merge/rebase 状态**：
```bash
# 检查 .git 目录下的状态文件
git rev-parse --git-dir | xargs -I{} sh -c 'test -d "{}/rebase-merge" -o -d "{}/rebase-apply" -o -f "{}/MERGE_HEAD" && echo "IN_PROGRESS" || echo "CLEAN"'
```

**如果处于 merge/rebase**：
```yaml
result:
  status: MERGE_IN_PROGRESS
  message: "仓库处于 merge/rebase 状态，请先手动解决"
  suggestion: "运行 git rebase --continue 或 git merge --abort"
```
→ **退出**

### Phase 4: 敏感文件检查

检查以下模式的文件是否在暂存区或未跟踪文件中：

| 模式 | 说明 |
|------|------|
| `.env` | 环境变量文件 |
| `.env.*` | 环境变量变体 |
| `*key*` | 密钥文件 |
| `*token*` | Token 文件 |
| `*secret*` | Secret 文件 |
| `*credential*` | 凭证文件 |
| `*service-account*.json` | GCP 服务账号 |
| `id_rsa*` | SSH 私钥 |
| `*.pem` | 证书私钥 |
| `*.p12` | PKCS12 证书 |
| `.mcp.json` | MCP 配置（含 API key 引用）|

**检查命令**：
```bash
# 获取所有待提交文件（含未跟踪）
git status --porcelain=v1 -uall | cut -c4- | grep -iE '\.env($|\.)|(key|token|secret|credential)|service-account.*\.json|id_rsa|\.pem$|\.p12$|\.mcp\.json$'
```

**如果发现敏感文件**：
```yaml
result:
  status: SENSITIVE_FILES_DETECTED
  message: "检测到敏感文件，已停止提交"
  sensitive_files:
    - <file1>
    - <file2>
  suggestion: |
    请检查以下选项：
    1. 添加到 .gitignore 并移除：git rm --cached <file>
    2. 确认是安全的模板文件后手动提交
```
→ **退出**

### Phase 5: 提交

```bash
# 添加所有变更
git add -A

# 生成提交信息（跨平台兼容）
# Windows PowerShell:
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; git commit -m "autosave: $ts"

# Unix/WSL:
git commit -m "autosave: $(date '+%Y-%m-%d %H:%M:%S')"
```

**如果 commit 失败（无变更）**：
```yaml
result:
  status: NOTHING_TO_COMMIT
  message: "没有需要提交的变更"
```
→ **退出**

### Phase 6: 推送当前分支

```bash
git push -u origin HEAD
```

**如果推送失败**：
```yaml
result:
  status: PUSH_FAILED
  message: "推送失败"
  error: <error message>
  suggestion: |
    可能原因：
    1. 远端有新提交 → git pull --rebase
    2. 分支保护规则 → 检查仓库设置
    3. 权限不足 → 检查凭证
```
→ **退出**

### Phase 7: 主分支合并（可选）

**识别默认主分支**：
```bash
# 获取 origin/HEAD 指向的分支
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'

# 如果失败，尝试常见名称
git rev-parse --verify origin/main >/dev/null 2>&1 && echo "main" || echo "master"
```

**如果当前就在主分支**：
→ Phase 5-6 已完成，**退出**

**如果在其他分支**：

```bash
# 保存当前分支名
CURRENT_BRANCH=$(git branch --show-current)
MAIN_BRANCH=<detected main branch>

# 切换到主分支
git checkout $MAIN_BRANCH

# 拉取最新
git pull --rebase

# 尝试 fast-forward 合并
git merge --ff-only $CURRENT_BRANCH
```

**如果 ff 失败，尝试 --no-ff**：
```bash
git merge --no-ff -m "Merge branch '$CURRENT_BRANCH'" $CURRENT_BRANCH
```

**如果合并有冲突**：
```bash
# 获取冲突文件列表
git diff --name-only --diff-filter=U
```

```yaml
result:
  status: MERGE_CONFLICT
  message: "合并到主分支时发生冲突"
  conflict_files:
    - <file1>
    - <file2>
  suggestion: |
    下一步：
    1. 手动解决冲突：编辑上述文件
    2. 标记已解决：git add <file>
    3. 完成合并：git commit
    4. 推送：git push

    或放弃合并：git merge --abort
```
→ **退出**

**合并成功后推送**：
```bash
git push
```

### Phase 8: 完成报告

```yaml
result:
  status: SUCCESS
  message: "自动提交流程完成"
  summary:
    branch: <current branch>
    commit: <commit hash>
    merged_to_main: <true/false>
    main_branch: <main/master>
  commands_executed:
    - git add -A
    - git commit -m "autosave: YYYY-MM-DD HH:MM:SS"
    - git push -u origin HEAD
    - <merge commands if applicable>
```

## 错误处理

### 权限错误

```yaml
result:
  status: PERMISSION_DENIED
  message: "Git 操作权限被拒绝"
  suggestion: |
    检查：
    1. SSH 密钥是否配置：ssh -T git@github.com
    2. 凭证是否有效：git credential-manager get
    3. 仓库写入权限
```

### 网络错误

```yaml
result:
  status: NETWORK_ERROR
  message: "网络连接失败"
  suggestion: "检查网络连接或代理设置"
```

## 跨平台兼容

### Windows PowerShell

```powershell
# 时间戳生成
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 检查 rebase 状态
$gitDir = git rev-parse --git-dir
$inRebase = (Test-Path "$gitDir/rebase-merge") -or (Test-Path "$gitDir/rebase-apply")
$inMerge = Test-Path "$gitDir/MERGE_HEAD"
```

### Unix/WSL bash

```bash
# 时间戳生成
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# 检查 rebase 状态
git_dir=$(git rev-parse --git-dir)
in_rebase=false
[ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ] && in_rebase=true
in_merge=false
[ -f "$git_dir/MERGE_HEAD" ] && in_merge=true
```

## 安全约束

1. **绝不自动解决冲突** - 发现冲突立即停止
2. **绝不 force push** - 禁止 `git push --force`
3. **绝不修改历史** - 禁止 `git rebase -i` 或 `git reset --hard`
4. **敏感文件阻断** - 发现敏感文件模式立即停止

## 使用示例

### 基本用法

```
用户: 帮我提交并推送
Claude: [调用 repo-push skill]
```

### 输出示例

```
=== Phase 1: 证据收集 ===
cwd: d:\dw11\piano
repo_root: d:\dw11\piano
status:
 M LyreAutoPlayer/main.py
?? new_file.txt

=== Phase 2: 变更检查 ===
检测到 2 个变更

=== Phase 3: 同步远端 ===
git pull --rebase --autostash: Already up to date.

=== Phase 4: 敏感文件检查 ===
未检测到敏感文件

=== Phase 5: 提交 ===
git add -A
git commit -m "autosave: 2026-01-05 15:30:45"
[main abc1234] autosave: 2026-01-05 15:30:45
 2 files changed, 10 insertions(+)

=== Phase 6: 推送 ===
git push -u origin HEAD
To github.com:user/repo.git
   def5678..abc1234  main -> main

=== 完成 ===
status: SUCCESS
branch: main
commit: abc1234
```

---

*创建时间: 2026-01-05*
*优先级: MEDIUM*
