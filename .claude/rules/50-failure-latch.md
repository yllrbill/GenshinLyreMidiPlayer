# Failure Latch Mechanism

## 目的

防止单次 Bash 失败导致的级联损伤。一旦命令失败，会话自动进入只读规划模式（plan-only mode）。

## 工作原理

### 1. PostToolUse Hook - 捕获失败
当任何 Bash 命令返回非 0 退出码时：
- 自动在 `%USERPROFILE%\.claude\latch.lock` 创建锁存文件
- 写入失败标记 `BASH_FAILED`
- 返回 exit code 2 阻止后续操作

### 2. PreToolUse Hook - 硬拦截
在执行以下工具前检查锁存文件：
- **Edit**: 编辑文件
- **Write**: 写入新文件
- **Bash**: 执行命令

如果 `latch.lock` 存在：
- 拦截工具执行 (exit code 2)
- 显示错误信息：`[LOCKED] Session in plan-only mode`
- 提示解锁命令

### 3. 恢复机制
用户手动解除锁定：

```powershell
Remove-Item $env:USERPROFILE\.claude\latch.lock -Force
```

## 锁存状态确认

### 检查是否已锁定
```powershell
Test-Path $env:USERPROFILE\.claude\latch.lock
# True = 已锁定
# False = 未锁定
```

### 查看锁存原因
```powershell
Get-Content $env:USERPROFILE\.claude\latch.lock
# 输出: BASH_FAILED
```

## 使用场景示例

### 场景 1: Bash 命令失败触发锁存
```powershell
# 用户在 Claude Code 中执行
python -c "exit(1)"

# PostToolUse Hook 自动触发:
# [LATCH] Session locked due to Bash failure

# 后续尝试 Edit/Write/Bash 均被拦截:
# [LOCKED] Session in plan-only mode. Run: Remove-Item $HOME/.claude/latch.lock
```

### 场景 2: 锁定后只能进行只读操作
```plaintext
✅ 允许的操作（只读）:
- Read (读取文件)
- Grep (搜索内容)
- Glob (列出文件)
- LS (列目录)

❌ 禁止的操作（写入/执行）:
- Edit (编辑文件)
- Write (写入文件)
- Bash (执行命令)
```

### 场景 3: 修复后解锁并继续
```powershell
# 1. 分析失败原因（只读操作）
Read analyzetools/test.py
Grep "import frida" analyzetools/*.py

# 2. 确认修复方案

# 3. 解锁会话
Remove-Item $env:USERPROFILE\.claude\latch.lock -Force

# 4. 应用修复
Edit analyzetools/test.py # 修正 import 路径
```

## 配置位置

### Hooks 配置
文件: `d:\dw11\.claude\settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ ... }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit",
        "hooks": [{ ... }]
      },
      {
        "matcher": "Write",
        "hooks": [{ ... }]
      },
      {
        "matcher": "Bash",
        "hooks": [{ ... }]
      }
    ]
  }
}
```

### 行为约束
文件: `d:\dw11\.claude\rules\10-triage-discipline.md`

- Fail-Fast 原则
- 失败自动进入 Plan 模式
- Triage Mode Entry

## 禁用此机制

如需暂时禁用失败锁存机制：

### 方法 1: 注释 hooks（永久禁用）
编辑 `d:\dw11\.claude\settings.json`，注释掉 `PostToolUse` 和 `PreToolUse` 部分。

### 方法 2: 删除锁存文件（临时解锁）
```powershell
Remove-Item $env:USERPROFILE\.claude\latch.lock -Force -ErrorAction SilentlyContinue
```

## Exit Code 语义

| Exit Code | 含义 | 工具执行结果 |
|-----------|------|-------------|
| 0 | Hook 通过 | 继续执行工具 |
| 1 | Hook 失败但继续 | 显示警告，继续执行 |
| **2** | 硬拦截 | **工具执行被阻止** |

## 与其他规则的协同

- 与 **10-triage-discipline.md** Fail-Fast 原则一致
- 与 **00-operating-model.md** Fail-Closed 原则一致
- 与 **90-handoff-format.md** Blockers 章节联动

## 验收测试

```powershell
# 测试 1: 清理初始状态
Remove-Item $env:USERPROFILE\.claude\latch.lock -Force -ErrorAction SilentlyContinue

# 测试 2: 触发失败（在 Claude Code 中）
python -c "exit(1)"

# 测试 3: 确认锁存文件已创建
Test-Path $env:USERPROFILE\.claude\latch.lock
# 预期: True

# 测试 4: 尝试 Edit/Write（应被拦截）
# 在 Claude Code 中尝试编辑文件
# 预期错误: [LOCKED] Session in plan-only mode

# 测试 5: 解锁并恢复
Remove-Item $env:USERPROFILE\.claude\latch.lock -Force
python -c "print('OK')"
# 预期: 成功执行
```

---

*创建时间: 2025-12-26*
*优先级: HIGHEST - 覆盖所有其他流程规则*
*状态: ACTIVE (hooks 已配置在 settings.json)*
