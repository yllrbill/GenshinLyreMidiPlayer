# Modelrouter-core Integration Guide

> **唯一事实源**: [SKILL.md](./SKILL.md)

## 概述

Modelrouter-core 为 Task 工具提供模型选择建议，根据任务复杂度自动路由到 haiku/sonnet/opus。

---

## 调用方式

### 方式 1: 显式命令 (推荐)

```bash
/modelrouter analyze "<your prompt>"
```

**输出示例**:
```yaml
envelope:
  command: modelrouter
  status: OK
  model_selected: sonnet
  complexity_level: MEDIUM
  complexity_score: 35
```

### 方式 2: Skill 内部调用

在其他 Skill 的 workflow 中：

```yaml
workflow:
  - step: 0.5 (Optional) 模型路由
    action: invoke modelrouter-core with prompt
    output: complexity_level, model_selected
    skip_if: model_preference 已在 frontmatter 指定
```

### 方式 3: Task 工具前置

```
1. /modelrouter analyze "<task description>"
2. Task(model=<recommended>)
```

---

## 与其他 Skills 的集成

| Skill | 集成点 | 默认模型 | 说明 |
|-------|--------|----------|------|
| voteplan-core | 候选计划生成前 | sonnet | 搜索+评分需要中等能力 |
| reflectloop-core | 执行前 | haiku | 执行沙箱步骤，快速迭代 |
| websearch | 搜索前 | haiku | 简单搜索任务 |
| thinking-router | 路由决策时 | sonnet | 需要判断 blocker 类型 |

---

## 复杂度判定规则

### 关键词权重 (来自 patterns.yaml)

| 关键词 | 分数 | 级别 |
|--------|------|------|
| 架构, 重构, 设计 | +15 | HARD |
| 分析, 优化, 调试 | +10 | HARD |
| 添加, 修改, 更新 | +5 | MEDIUM |
| 列出, 显示, 读取 | +2 | EASY |

### 长度权重

| Prompt 长度 | 分数 |
|-------------|------|
| > 500 字符 | +10 |
| 200-500 字符 | +5 |
| < 200 字符 | +0 |

### 阈值判定

```
total = keyword_score + length_score + context_score

HARD:   total >= 50 → opus
MEDIUM: total >= 25 → sonnet
EASY:   total < 25  → haiku
```

---

## 状态存储

每次调用写入：

```
.claude/state/modelrouter/
├── session.latest.yaml       # 当前会话摘要
└── history/
    └── <YYYYMMDD>/
        └── <HHMMSS>.yaml     # 历史记录
```

**session.latest.yaml 格式**:

```yaml
envelope:
  command: modelrouter
  timestamp: 2025-12-30T12:00:00Z
  status: OK
  error_code: null

metrics:
  routing:
    complexity_level: MEDIUM
    complexity_score: 35
    model_selected: sonnet
    keyword_matches:
      - word: "分析"
        score: 10
      - word: "优化"
        score: 10
    length_score: 5
    context_score: 10

session:
  total_routings: 5
  model_distribution:
    opus: 1
    sonnet: 3
    haiku: 1
```

---

## Failure Latch 处理

当 `$HOME/.claude/latch.lock` 存在时：

1. 检测到锁定状态
2. 设置 `error_code: LATCHED`
3. **跳过状态写入**
4. **仍然返回路由结果**

```yaml
envelope:
  command: modelrouter
  status: OK
  error_code: LATCHED
  warnings:
    - "Session latched - state write skipped"

metrics:
  routing:
    model_selected: sonnet  # 路由结果仍然有效
```

---

## 使用示例

### 示例 1: 复杂任务

```bash
/modelrouter analyze "重构整个认证系统，支持 OAuth2 和 SAML，确保向后兼容"
```

**结果**: `model_selected: opus` (score >= 50)

### 示例 2: 中等任务

```bash
/modelrouter analyze "分析 SnapAny 的链接解析逻辑"
```

**结果**: `model_selected: sonnet` (score 25-49)

### 示例 3: 简单任务

```bash
/modelrouter analyze "列出所有 .py 文件"
```

**结果**: `model_selected: haiku` (score < 25)

---

## 与 voteplan-core 的对比

| 特性 | modelrouter-core | voteplan-core |
|------|-----------------|---------------|
| 目的 | 选择执行模型 | 多源搜索+投票 |
| 输入 | prompt/task | 搜索主题 |
| 输出 | model_selected | winner plan |
| 状态目录 | `.claude/state/modelrouter/` | `.claude/state/planvote-search/` |
| model_preference | haiku (自身) | sonnet (搜索需要能力) |

---

## 验收命令

```powershell
# 测试 analyze 命令
/modelrouter analyze "实现一个复杂的加密算法"
# 预期: model_selected = opus 或 sonnet

# 检查状态写入
Test-Path ".claude/state/modelrouter/session.latest.yaml"
# 预期: True

# 查看内容
Get-Content ".claude/state/modelrouter/session.latest.yaml" -TotalCount 10
```

---

*创建时间: 2025-12-30*
*唯一事实源: SKILL.md*
