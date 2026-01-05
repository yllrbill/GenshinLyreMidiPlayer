---
name: agent-plan
description: Maintain ChatGPT persistent context in LyreAutoPlayer/ops/ai/context/agents.md and generate a Claude execution prompt in .claude/private/plan.md from a chat transcript.
---

# Agent Plan

## Purpose

Keep a single ChatGPT-owned context file up to date and produce a Claude execution prompt based on chat logs, so key constraints are not lost due to context compression.

## Trigger

Use this skill when the user mentions agent-plan, persistent ChatGPT context, agents.md, or asks to generate/update a Claude plan prompt from a chat transcript.

## Fixed Paths (do not change)

- ChatGPT context file: D:\dw11\piano\LyreAutoPlayer\ops\ai\context\agents.md
- Read-only context folder: D:\dw11\piano\LyreAutoPlayer\ops\ai\context (only agents.md can be changed)
- Claude plan file: D:\dw11\piano\.claude\private\plan.md
  - If the user provides D:\dw11\piano.claude\private\plan.md, normalize to the path above.

## Required Inputs

- A chat transcript pasted by the user, or a user-provided path to a transcript file.

## Optional Inputs

- Repository files referenced by the chat; read only the specific files needed.

## Workflow

1. Read agents.md if it exists; if missing, create it using the template below.
2. Read PROJECT_SUMMARY.md (read-only).
3. Read the user-provided chat transcript. If missing, ask the user to provide it and stop.
4. If the chat references repo files/modules, read only those files (no repo-wide scan).
5. Update agents.md:
   - Merge in new goals, durable constraints, key decisions, and open questions.
   - Preserve existing content unless explicitly superseded by the chat.
   - Keep section order stable.
6. Generate D:\dw11\piano\.claude\private\plan.md:
   - Include Main Goal, Phase Steps, Step Details (paths + change summary), Constraints.
   - Base content on the updated context + chat transcript.
7. Respond with a brief summary and the updated file paths only; do not dump full file contents.

## agents.md Template (ChatGPT)

```
# ChatGPT Context (fixed file)

## Main Goal
- ...

## Durable Constraints
- ...

## Key Context / Decisions
- ...

## Open Questions
- ...

## User Prompt
Main Goal:
Phase Steps:
Step Details (where to change, change summary):
Constraints:
```

## .claude/private/plan.md Template (Claude)

```
# Claude Prompt

## Main Goal
- ...

## Phase Steps
1. ...
2. ...
3. ...

## Step Details (where to change, change summary)
1. Where to change: <path or module>
   Change summary: ...

## Constraints
- ...
```

## Output Expectations

- Keep prompts concise and actionable.
- Use Windows-style paths (D:\dw11\piano\...).
- Ask a short clarification only when required inputs are missing or contradictory.

## Error Handling

- If the chat transcript is missing: ask the user to paste it, then stop.
- If the context folder is missing: state the path and stop; do not create extra files in that folder.
