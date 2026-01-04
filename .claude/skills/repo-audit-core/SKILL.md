---
name: repo-audit-core
description: 会话文件修改审计报告 - 只读分析所有变更文件并输出可复跑报告
allowed-tools: Bash(*), Read(*), Glob(*)
---

# Repo Audit Skill

> 输出"本次会话的文件修改审计报告"，列出所有被修改/新增/删除/重命名的文件，并给出每个文件的修改内容与变更行范围（行号）。

## 硬规则

1. **只读操作** - 只做读取/分析/汇总，不修改任何文件、不运行写入磁盘的命令
2. **覆盖所有变更类型**：
   - tracked: Modified / Added / Deleted / Renamed / Copied
   - untracked: 新建但未加入 git 的文件
   - staged 与 unstaged 都要覆盖
3. **可复跑、可核对** - 必须输出仓库根路径、工作目录、使用的命令及其输出依据
4. **行号精确** - 使用 `git diff --unified=0` 从 hunk header 提取变更行范围
5. **确定性输出** - 按路径字典序排序

## 触发条件

当用户请求：
- "审计报告"
- "文件变更审计"
- "repo audit"
- "变更清单"
- "本次改了什么"
- "修改了哪些文件"

## 执行流程

### Phase 1: 定位信息

```bash
# 输出当前工作目录
pwd

# 输出仓库根目录
git rev-parse --show-toplevel

# 输出当前分支
git branch --show-current

# 输出 HEAD commit
git rev-parse --short HEAD
```

**输出格式**：
```yaml
location:
  cwd: <pwd output>
  repo_root: <git rev-parse --show-toplevel output>
  branch: <current branch>
  head: <HEAD commit short hash>
```

### Phase 2: 采集变更清单

```bash
# 完整状态（含 untracked）
git status --porcelain=v1 -uall

# unstaged 变更文件列表
git diff --name-status

# staged 变更文件列表
git diff --cached --name-status

# 仅 untracked 文件列表
git ls-files --others --exclude-standard
```

**状态码解析**：

| 状态码 | 含义 |
|--------|------|
| M | Modified (已修改) |
| A | Added (新增到暂存区) |
| D | Deleted (已删除) |
| R | Renamed (重命名) |
| C | Copied (复制) |
| ?? | Untracked (未跟踪) |
| !! | Ignored (被忽略) |

### Phase 3: 逐文件 Diff 分析

对每个变更文件执行：

#### 3.1 Unstaged 变更

```bash
git diff --unified=0 -- <path>
```

#### 3.2 Staged 变更

```bash
git diff --cached --unified=0 -- <path>
```

#### 3.3 Untracked 文件

**判断文件类型**：
```bash
# 检查是否为二进制
file --mime-type <path> | grep -q 'text/' && echo "TEXT" || echo "BINARY"
```

**文本文件处理**：
- 行数 ≤ 300: 输出完整内容
- 行数 > 300: 输出前 200 行 + 后 100 行 + 截断说明

```bash
wc -l < <path>
head -n 200 <path>
tail -n 100 <path>
```

**二进制文件处理**：
```bash
# 输出文件大小
stat --printf="%s" <path>  # Linux
stat -f%z <path>           # macOS
(Get-Item <path>).Length   # PowerShell

# 输出 SHA256
sha256sum <path>           # Linux
shasum -a 256 <path>       # macOS
certutil -hashfile <path> SHA256  # Windows
```

### Phase 4: 行号范围提取

从 diff hunk header 提取行号：

**Hunk Header 格式**：
```
@@ -a,b +c,d @@
```

| 字段 | 含义 |
|------|------|
| `-a` | 原文件起始行号 |
| `b` | 删除的行数 (省略时为 1) |
| `+c` | 新文件起始行号 |
| `d` | 新增的行数 (省略时为 1) |

**提取命令**：
```bash
git diff --unified=0 -- <path> | grep '^@@' | sed 's/@@ //' | sed 's/ @@.*//'
```

**解析示例**：
```
@@ -10,3 +10,5 @@  → 删除 10-12 行，新增 10-14 行
@@ -25 +25,0 @@    → 删除第 25 行，新增 0 行
@@ -0,0 +1,50 @@  → 新文件，1-50 行全部新增
```

### Phase 5: 输出报告

#### A) 总览表

```markdown
## 变更总览

| 状态 | 相对路径 | 绝对路径 | Staged | 行范围摘要 |
|------|----------|----------|--------|------------|
| M | src/main.py | /repo/src/main.py | Yes | -10,3 +10,5; -50,1 +50,2 |
| A | new_file.txt | /repo/new_file.txt | Yes | +1,100 |
| D | old_file.txt | /repo/old_file.txt | No | -1,50 |
| ?? | scratch.py | /repo/scratch.py | - | (untracked, 25 lines) |
```

#### B) 逐文件细节

每个文件一个小节：

```markdown
### [M] src/main.py

**状态**: Modified
**路径**: /repo/src/main.py

#### Staged 变更
无

#### Unstaged 变更

**Hunk 1**: -10,3 +10,5
- 删除范围: 第 10-12 行
- 新增范围: 第 10-14 行

```diff
@@ -10,3 +10,5 @@
-old line 1
-old line 2
-old line 3
+new line 1
+new line 2
+new line 3
+new line 4
+new line 5
```

**Hunk 2**: -50,1 +50,2
- 删除范围: 第 50 行
- 新增范围: 第 50-51 行

```diff
@@ -50,1 +50,2 @@
-old single line
+new line A
+new line B
```
```

#### C) 完整 Patch（可选）

```markdown
## 完整 Patch

### Unstaged Diff
```diff
<git diff 完整输出>
```

### Staged Diff
```diff
<git diff --cached 完整输出>
```
```

## 非 Git 仓库处理

如果 `git rev-parse --show-toplevel` 失败：

```yaml
warning:
  status: NOT_GIT_REPO
  message: "当前目录不是 git 仓库"
  fallback: "使用文件系统时间戳进行差分分析"
```

**备选方案**：
1. 使用 `find` 按修改时间列出最近变更的文件
2. 对比文件 mtime 与会话开始时间
3. 尽量模拟 hunk 格式输出

```bash
# 列出最近 N 分钟内修改的文件
find . -type f -mmin -<minutes> -not -path './.git/*' | sort
```

## 输出示例

```markdown
# 文件修改审计报告

生成时间: 2026-01-05 15:30:00

## 定位信息

| 项目 | 值 |
|------|-----|
| 工作目录 | d:\dw11\piano |
| 仓库根目录 | d:\dw11\piano |
| 当前分支 | main |
| HEAD | abc1234 |

## 变更总览

| 状态 | 相对路径 | Staged | 行范围摘要 |
|------|----------|--------|------------|
| M | LyreAutoPlayer/main.py | No | -25,3 +25,8 |
| M | LyreAutoPlayer/ui/editor.py | Yes | -100,10 +100,15 |
| ?? | new_script.py | - | (new, 45 lines) |

共 3 个文件变更

---

### [M] LyreAutoPlayer/main.py

**状态**: Modified (unstaged)
**绝对路径**: d:\dw11\piano\LyreAutoPlayer\main.py

#### Unstaged 变更

**Hunk 1**: @@ -25,3 +25,8 @@
- 删除范围: 第 25-27 行 (3 行)
- 新增范围: 第 25-32 行 (8 行)

```diff
@@ -25,3 +25,8 @@
-    old_code()
-    more_old()
-    final_old()
+    new_code()
+    more_new()
+    even_more()
+    additional()
+    extra_line()
+    another_extra()
+    yet_another()
+    last_line()
```

---

### [??] new_script.py

**状态**: Untracked (new file)
**绝对路径**: d:\dw11\piano\new_script.py
**文件大小**: 1,234 bytes
**行数**: 45 行

#### 文件内容

```python
#!/usr/bin/env python3
"""New script for testing."""

def main():
    print("Hello, World!")
    # ... (完整内容)

if __name__ == "__main__":
    main()
```

---

## 完整 Patch

### Unstaged Diff

```diff
diff --git a/LyreAutoPlayer/main.py b/LyreAutoPlayer/main.py
index abc1234..def5678 100644
--- a/LyreAutoPlayer/main.py
+++ b/LyreAutoPlayer/main.py
@@ -25,3 +25,8 @@
...
```

### Staged Diff

```diff
diff --git a/LyreAutoPlayer/ui/editor.py b/LyreAutoPlayer/ui/editor.py
...
```
```

## 跨平台兼容

### Windows PowerShell

```powershell
# 文件大小
(Get-Item <path>).Length

# SHA256
(Get-FileHash <path> -Algorithm SHA256).Hash

# 文件类型判断（简化）
$ext = [System.IO.Path]::GetExtension(<path>)
$binaryExts = @('.exe', '.dll', '.bin', '.zip', '.tar', '.gz', '.7z', '.rar', '.jpg', '.png', '.gif', '.pdf', '.doc', '.xls')
if ($binaryExts -contains $ext) { "BINARY" } else { "TEXT" }
```

### Unix/WSL bash

```bash
# 文件大小
stat --printf="%s" <path>

# SHA256
sha256sum <path> | cut -d' ' -f1

# 文件类型判断
file --mime-type <path> | grep -q 'text/' && echo "TEXT" || echo "BINARY"
```

## 安全约束

1. **绝不修改任何文件** - 只读操作
2. **绝不执行写入命令** - 禁止 `git add`, `git commit`, `rm`, `mv` 等
3. **敏感内容处理** - 如果文件内容包含明显的密钥/token 模式，在报告中标记 `[SENSITIVE - REDACTED]`

## 敏感内容检测模式

```regex
# API Key 模式
(api[_-]?key|apikey)\s*[:=]\s*['"][^'"]{20,}['"]

# Token 模式
(token|secret|password)\s*[:=]\s*['"][^'"]+['"]

# AWS 密钥
AKIA[0-9A-Z]{16}

# 私钥
-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----
```

如果检测到敏感内容，输出：

```markdown
**注意**: 此文件可能包含敏感信息，内容已脱敏

```
[SENSITIVE CONTENT - 3 potential secrets detected]
Line 15: api_key = "[REDACTED]"
Line 28: token = "[REDACTED]"
Line 45: password = "[REDACTED]"
```
```

## 错误处理

### Git 不可用

```yaml
error:
  status: GIT_NOT_AVAILABLE
  message: "git 命令不可用"
  suggestion: "请安装 git 或检查 PATH 环境变量"
```

### 权限错误

```yaml
error:
  status: PERMISSION_DENIED
  message: "无法读取文件 <path>"
  suggestion: "检查文件权限"
```

---

*创建时间: 2026-01-05*
*优先级: LOW (只读审计)*
