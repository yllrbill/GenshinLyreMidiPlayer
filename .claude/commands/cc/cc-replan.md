---
description: Generate new plan by merging Goal Delta + Patch List with a deterministic scoring algorithm
argument-hint: [optional: constraints like time budget]
---
think harder.

Input: Delta Matrix (goal delta + patch list + step delta + pitfall delta)

## Replan Algorithm (deterministic)

Score each candidate task (original plan steps + patches) with:
- BlockerImpact: 0-3 (unblocks immediately?)
- GoalAlignment: 0-3 (directly advances unified goal?)
- EvidenceStrength: 0-3 (3=official docs/logs, 2=credible blog, 1=anecdote)
- Risk: 0-2 (2=high risk / irreversible)
- Effort: 0-2 (2=large)

TotalScore = 5*BlockerImpact + 3*GoalAlignment + 2*EvidenceStrength - 2*Risk - Effort

Rules:
1) Drop tasks with GoalAlignment=0 unless needed for verification.
2) Must include guardrails from Pitfall Delta as explicit steps.
3) Sort by TotalScore desc; break ties by lower Risk then lower Effort.
4) Add dependencies explicitly (A -> B).
5) Every step must have a verification command/check.

## Output: New Plan

### Unified Goal

### Constraints

### Guardrails (from pitfalls)

### Plan Steps (ordered)
For each:
- Step ID:
- Action:
- Rationale (what delta closes):
- Commands / Files:
- Verification:
- Rollback:
