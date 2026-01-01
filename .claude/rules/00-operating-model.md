# Operating Model

## Core Principles

- **Plan-first**：先进入 Plan 模式，不改文件、不跑危险命令，先读仓库给出 ≤10 条最小实施计划（影响文件 + 风险点 + 验收命令）
- **Continuity-first**：优先读仓库文档恢复上下文，少问人
- **Deterministic**：任何扫描/选择/遍历必须排序（sorted）并写明选择规则
- **Minimal change**：只做完成目标所需的最小修改，不做大重构
- **Fail-closed**：证据/验收缺失就标记 UNKNOWN/FAIL，不"猜测通过"
- **Evidence-first**：重要结论必须给出可复跑三件套（输入路径 + 命令 + 输出/证据路径）
- **Research-first**：遇到不确定或需要权威依据时，优先使用 WebSearch/WebFetch 查询官方文档/一手来源，将结论与来源 URL 记录到 HANDOFF/Runbook
- **Skeleton-first**：配置文件优先放入 `.claude/` 骨架目录，仅 Claude Code 强制要求的文件放根目录

## 仓库模板目录树（可复用骨架）

```
project/
├─ AUTHORIZATION.md
├─ README.md
├─ CLAUDE.md                         # 项目级永续指令 (Claude Code 强制根目录)
├─ .gitignore
├─ .mcp.json                         # MCP 配置 (Claude Code 强制根目录)
│
├─ .claude/
│  ├─ settings.json                  # 共享配置：权限模式/hooks
│  ├─ settings.local.json            # 本地覆盖 (不提交)
│  │
│  ├─ commands/                      # 项目自定义 /xxx 命令
│  │  ├─ bootstrap.md                # /bootstrap：启动/恢复/盘点/计划
│  │  ├─ triage.md                   # /triage：错误定位/最小复现
│  │  ├─ repro.md                    # /repro：生成可复跑脚本+命令
│  │  ├─ verify.md                   # /verify：验收清单/证据链/一致性
│  │  ├─ handoff.md                  # /handoff：写交接文档
│  │  ├─ voteplan.md                 # /voteplan：多源搜索+评分投票
│  │  ├─ reflectloop.md              # /reflectloop：沙箱执行闭环
│  │  ├─ thinking.md                 # /thinking：智能路由
│  │  ├─ modelrouter.md              # /modelrouter：模型路由与追踪
│  │  └─ <domain>/                   # 命令子目录 (可选)
│  │     └─ <sub-command>.md
│  │
│  ├─ skills/                        # Skills (Claude-only 能力模块)
│  │  ├─ <skill-name>-core/          # Skill 目录 (必须加 -core 后缀避免命令冲突)
│  │  │  ├─ SKILL.md                 # Skill 定义 (必须有 frontmatter)
│  │  │  ├─ ROUTING.md               # 路由规则 (可选)
│  │  │  ├─ CHECKLIST.md             # 验收清单 (可选)
│  │  │  ├─ patterns.yaml            # 扫描 Patterns (可选)
│  │  │  ├─ *.ps1                    # 验证脚本 (可选)
│  │  │  ├─ templates/               # 模板文件 (可选)
│  │  │  └─ examples/                # 示例文件 (可选)
│  │  ├─ voteplan-core/              # 多源搜索+评分投票
│  │  ├─ reflectloop-core/           # 沙箱执行闭环
│  │  ├─ thinking-router/            # 智能路由
│  │  ├─ websearch/                  # 聚合搜索+难度自适应 (唯一事实源)
│  │  └─ modelrouter-core/           # 自动模型路由+复杂度判断
│  │
│  ├─ agents/                        # Subagents (专才分工, 独立上下文)
│  │  ├─ re-recon.md                 # 只读侦察/结构扫描/入口定位
│  │  ├─ debugger.md                 # 复现-定位-修复 (可写/可跑测试)
│  │  └─ auditor.md                  # 证据链/门禁/回归审计 (偏只读)
│  │
│  ├─ rules/                         # 模块化规则 (可按路径生效)
│  │  ├─ 00-operating-model.md       # 操作模型
│  │  ├─ 10-triage-discipline.md     # Triage 规则
│  │  ├─ 50-failure-latch.md         # 失败锁存机制
│  │  ├─ 65-thinking-envelope.md     # Envelope 规范
│  │  ├─ 70-mcp-cus.md               # MCP 搜索规则
│  │  ├─ 90-handoff-format.md        # 交接文档格式
│  │  └─ 95-command-skill-naming.md  # 命令/Skill 命名规范
│  │
│  ├─ state/                         # 运行时状态 (工件存储)
│  │  ├─ thinking/                   # /thinking 命令工件
│  │  │  ├─ blocker.latest.yaml
│  │  │  ├─ plan.latest.yaml
│  │  │  └─ research.latest.yaml
│  │  ├─ reflectloop/                # /reflectloop 命令工件
│  │  │  ├─ reflectloop.latest.yaml
│  │  │  └─ runs/<run_id>/
│  │  ├─ modelrouter/                # /modelrouter 命令工件
│  │  │  ├─ session.latest.yaml
│  │  │  └─ history/<YYYYMMDD>/
│  │  ├─ planvote-search/<vote_id>/  # /voteplan 搜索结果
│  │  ├─ voteplan.<vote_id>.yaml     # /voteplan 最终输出
│  │  └─ private/                    # 私有隔离目录 (不提交)
│  │
│  ├─ private/                       # 敏感文件 (不提交)
│  │  ├─ secrets/                    # API 密钥模板
│  │  └─ analyzetools_sensitive/     # 敏感分析工具
│  │
│  ├─ session_notes/                 # 会话笔记 (可选, 可归档)
│  └─ _archive/                      # 归档文件
│
├─ analydocs/                        # 项目文档
│  ├─ CONTEXT.md                     # 项目背景/资产/术语
│  ├─ TARGETS.md                     # 目标二进制/模块/入口/版本
│  ├─ RUNBOOK.md                     # 常用命令 (build/test/run/debug)
│  ├─ ACCEPTANCE.md                  # 验收标准 (可脚本化)
│  ├─ EVIDENCE_SPEC.md               # 证据包规范 (文件/哈希/日志)
│  └─ HANDOFF.md                     # 本次会话写这里：下一次直接续跑
│
├─ analyzetools/                     # 分析工具
│  ├─ repro/                         # 最小复现脚本
│  ├─ verify/                        # 验收/一致性检查脚本
│  └─ tools/                         # 小工具：哈希/符号提取/日志规整
│
└─ analyzedata/
   ├─ inputs/                        # 输入资产 (dump/样本/日志/配置)
   ├─ outputs/                       # 输出产物 (patch/report/bundle)
   └─ scratch/                       # 临时/可删 (不进证据链)
```

### 目录职责

| 目录 | 职责 | 提交到 git |
|------|------|-----------|
| `.claude/commands/` | 用户可调用的 /xxx 命令 | ✅ |
| `.claude/skills/` | Claude-only 能力模块 (必须加 -core 后缀) | ✅ |
| `.claude/agents/` | Subagents 定义 | ✅ |
| `.claude/rules/` | 模块化规则 | ✅ |
| `.claude/state/` | 运行时状态/工件存储 | ❌ (或选择性提交) |
| `.claude/private/` | 敏感文件 | ❌ |
| `.claude/session_notes/` | 会话笔记 | ✅ (可选) |
| `analydocs/` | 项目文档、交接、验收标准 | ✅ |
| `analyzetools/` | 分析脚本、复现、验收工具 | ✅ |
| `analyzedata/inputs/` | 输入资产 | ✅ |
| `analyzedata/outputs/` | 输出产物 | ✅ |
| `analyzedata/scratch/` | 临时文件 | ❌ |

### 命令/Skill 命名规范

**重要**：避免命令和 Skill 同名导致冲突。

| 类型 | 位置 | 命名规则 |
|------|------|----------|
| Command | `.claude/commands/<name>.md` | 用户直接调用名 (e.g., `voteplan`) |
| Skill | `.claude/skills/<name>-core/SKILL.md` | 加 `-core` 后缀 (e.g., `voteplan-core`) |

详见：`.claude/rules/95-command-skill-naming.md`

### .gitignore 必须包含

```
# Claude Code 本地配置
.claude/settings.local.json
.claude/projects/

# 运行时状态 (可选择性提交)
.claude/state/
.claude/state/private/

# 敏感文件
.claude/private/

# MCP 配置 (含 API 密钥引用)
.mcp.json

# 临时文件
analyzedata/scratch/
```

## 会话开始
1. 运行 /bootstrap 盘点状态
2. 读取 analydocs/HANDOFF.md 恢复上下文
3. 确定本次目标后再动手

## 会话结束
1. 运行 /verify 验收
2. 运行 /handoff 更新交接文档
3. 确保 analydocs/HANDOFF.md 已更新

## 分工原则
- 侦察/探索 → re-recon subagent
- 修复/实现 → debugger subagent
- 审计/验收 → auditor subagent
