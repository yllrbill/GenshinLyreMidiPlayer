# Triage Discipline

## Fail-Fast Principle

**任何命令/步骤失败（非 0 退出码、异常、缺文件/权限、输出不符合预期）：立刻停止，不要尝试替代路径/绕过。**

## 失败自动进入 Plan 模式

当检测到任何 Bash/工具/步骤出现失败信号（非 0 exit、Traceback、error、permission deny、找不到文件等）时：

1. **立刻停止**，不尝试替代路径/绕过
2. **进入 Plan 行为**：只做定位与计划（允许读文件/grep/列目录），不给出新的执行命令链
3. **输出格式**：
   - 失败点（工具名称、命令、退出码）
   - 最可能原因（≤3 条，按可能性排序）
   - 最小修复方案（≤5 步，可执行命令）
   - 验收命令（≤2 条，确认修复成功）
4. **提醒用户**按 Shift+Tab 切到 ⏸ plan mode on 再继续

**CRITICAL**: 这是强制性行为约束，覆盖所有其他流程规则。失败后不得继续执行任何会修改系统状态的工具（Edit/Write/Bash）。

## Triage Mode Entry

当检测到失败时，立即进入 triage 模式：

### 1. 记录证据
```
- 完整错误消息
- 退出码
- 相关文件路径/哈希
- 执行命令（可复跑）
- 时间戳
```

### 2. 最小诊断
- 确认文件是否存在（ls/dir）
- 确认权限状态（settings.local.json）
- 记录环境信息（Python 版本、工作目录、OS）
- **禁止**猜测性修复或绕过

### 3. 研究根因
使用 **WebSearch** 和 **WebFetch** 工具：
- 搜索错误码/异常类型的官方文档
- 查找已知问题和解决方案
- 验证环境要求和依赖项
- 记录研究来源（URLs）

### 4. 提供最小修复
- 1-3 处改动（最多）
- 附带验证命令
- 说明为何修复有效
- 提供可复跑的测试命令

### 5. 更新文档
- 记录根因到 analydocs/HANDOFF.md（Blockers 章节）
- 如果修复成功，记录到 Verified Facts
- 更新 analydocs/ACCEPTANCE.md 相关验收状态

## 禁止行为

- ❌ 跳过失败，继续执行后续步骤
- ❌ 尝试"可能有效"的替代方案而不先研究
- ❌ 修改多处代码试图"顺便优化"
- ❌ 假设失败原因而不查证
- ❌ 不记录失败证据就开始修复

## 示例工作流

```markdown
## 失败检测
命令: `python -X utf8 analyzetools/test.py`
退出码: 1
错误: ModuleNotFoundError: No module named 'frida'

## Triage 步骤

### 1. 证据记录
- 错误类型: ModuleNotFoundError
- 缺失模块: frida
- Python 路径: C:\Python314\python.exe
- 时间: 2025-12-26 10:30:15

### 2. 诊断
- 确认虚拟环境: D:\dw11\venvsfrida_env\Scripts\python.exe 存在
- 确认 frida 安装: `venvsfrida_env\Scripts\pip list | grep frida` → frida 17.5.2

### 3. 根因研究
WebSearch: "ModuleNotFoundError python virtual environment"
- 原因: 使用了系统 Python 而非虚拟环境 Python
- 文档: https://docs.python.org/3/library/venv.html

### 4. 最小修复
改动 1 处:
```diff
- python -X utf8 analyzetools/test.py
+ D:\dw11\venvsfrida_env\Scripts\python.exe -X utf8 analyzetools/test.py
```

验证命令:
```powershell
D:\dw11\venvsfrida_env\Scripts\python.exe -X utf8 analyzetools/test.py
# 预期: 退出码 0
```

### 5. 文档更新
- analydocs/HANDOFF.md Blockers: 已解决 - 使用正确的 Python 路径
- analydocs/HANDOFF.md Verified Facts: 虚拟环境路径确认为 D:\dw11\venvsfrida_env\Scripts\python.exe
```

## 权限相关失败

如果失败原因是权限（如 Bash permission denied）：

1. **停止执行**
2. 记录需要的权限模式（如 `Bash(xxx:*)`）
3. **询问用户**是否添加到 settings.local.json
4. 获得用户确认后再添加权限
5. 验证权限添加成功后重新执行

## 网络/外部资源失败

如果失败涉及下载、API 调用、外部服务：

1. 使用 WebSearch 查找服务状态/已知问题
2. 使用 WebFetch 验证 URL 可达性
3. 记录网络环境（代理、防火墙）
4. 提供离线替代方案（如果可行）

## 与其他规则的协同

- 与 **00-operating-model.md** Fail-Closed 原则一致
- 与 **20-reverse-engineering.md** 证据要求一致
- 与 **90-handoff-format.md** Blockers 章节联动

---

*Triage 规则优先级: HIGHEST - 覆盖所有其他流程规则*
