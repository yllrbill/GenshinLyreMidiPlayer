---
description: WSJF-lite sorted plan - Generate final execution plan with scoring
argument-hint: [optional: max steps, time budget]
---
think harder.

## New Plan Generator (WSJF-lite)

Generate a prioritized, scored execution plan from patches and research.

### Inputs
- Patch plan (from /planplus1)
- Research pack (from /thingking_web)
- Unified goal (from /goaldiffer)
- Guardrails (from /differ2)
- Optional constraints: $ARGUMENTS

### WSJF-lite Scoring Algorithm

For each candidate step (patches + original plan items):

```
TotalScore = 5*BlockerImpact + 3*GoalAlignment + 2*EvidenceStrength - 2*Risk - Effort

Scoring Guide:
- BlockerImpact (0-3):
  0 = No unblocking effect
  1 = Enables future steps
  2 = Unblocks significant progress
  3 = Immediately unblocks critical path

- GoalAlignment (0-3):
  0 = Not aligned with unified goal
  1 = Indirectly supports goal
  2 = Directly advances goal
  3 = Critical for goal achievement

- EvidenceStrength (0-3):
  0 = Guess/assumption
  1 = Anecdotal/community suggestion
  2 = Credible blog/tutorial
  3 = Official docs/maintainer guidance

- Risk (0-2):
  0 = Low risk, easily reversible
  1 = Medium risk, some side effects
  2 = High risk, irreversible or dangerous

- Effort (0-2):
  0 = Trivial (< 5 min)
  1 = Small/Medium (5-30 min)
  2 = Large (> 30 min)

Max possible score: 5*3 + 3*3 + 2*3 - 2*0 - 0 = 30
Min possible score: 5*0 + 3*0 + 2*0 - 2*2 - 2 = -6
```

### Filtering Rules

1. **Drop if GoalAlignment = 0** (unless required for verification)
2. **Include guardrails** from pitfall delta as explicit steps
3. **Max 10 steps** (drop lowest scores if exceeds)
4. **Every step must have verification**

### Tie-Breaking

When scores are equal:
1. Lower Risk wins
2. If still tied, lower Effort wins
3. If still tied, alphabetical by action

### Output Structure

```yaml
new_plan:
  id: PLAN-<YYMMDD>-<seq>
  timestamp: <ISO8601>
  constraints:
    max_steps: <from args or 10>
    time_budget: <from args or "unlimited">
    custom: <any additional constraints>

  unified_goal:
    statement: <from goal delta>
    success_criteria:
      - <criterion>

  guardrails:
    - id: GR-<seq>
      guardrail: <preventive measure>
      check_at: <step ID(s) where to verify>

  steps:
    - id: P-<seq>
      rank: <1-N by score>
      action: <concise action description>
      rationale:
        closes: [<delta IDs this closes>]
        enables: [<step IDs this enables>]
        reason: <why this step matters>

      score:
        total: <calculated score>
        breakdown:
          blocker_impact: <0-3>
          goal_alignment: <0-3>
          evidence_strength: <0-3>
          risk: <0-2>
          effort: <0-2>
        calculation: "5*<BI> + 3*<GA> + 2*<ES> - 2*<R> - <E> = <total>"

      implementation:
        commands:
          - cmd: <exact command>
            cwd: <working directory if not default>
        files:
          - path: <file path>
            operation: <READ|WRITE|EXEC>

      verification:
        - check: <command or condition>
          expected: <success indicator>
          timeout: <max wait time if applicable>

      rollback:
        - step: <undo action>
          condition: <when to rollback>

      depends_on: [<P-id list>]
      blocked_by: [<P-id list of incomplete deps>]

      source:
        type: <PATCH|ORIGINAL|GUARDRAIL|RESEARCH>
        ref: <PATCH-id, original step, GR-id, or URL>

  execution_order:
    critical_path:
      - <P-id>: <action summary>
    parallel_groups:
      - group: <1-N>
        steps: [<P-id list that can run in parallel>]

  dropped_items:
    - original: <what was dropped>
      reason: <why dropped>
      score: <score if calculated>

  summary:
    total_steps: <N>
    max_possible: <N if constrained>
    score_range:
      highest: <P-id>: <score>
      lowest: <P-id>: <score>
    risk_profile:
      high_risk_steps: <count>
      total_risk_score: <sum of risk values>
    estimated_effort:
      trivial: <count>
      small_medium: <count>
      large: <count>
```

### Hard Rules

1. **Deterministic**: Steps MUST be sorted by TotalScore DESC, ties by Risk ASC, then Effort ASC
2. **Evidence-first**: Every step must cite evidence source (URL, file, or delta ID)
3. **Fail-closed**: If no patches/inputs available, output INSUFFICIENT_INPUT error
4. **Secret-safe**: Never include API keys or credentials in plan
5. **Verification required**: Every step must have explicit verification
6. **Max 10 steps**: Hard limit unless user specifies otherwise

### Validation Checks

Before outputting plan, verify:
- [ ] All steps have verification commands
- [ ] High-risk steps have rollback procedures
- [ ] Dependencies form a DAG (no cycles)
- [ ] Guardrails are placed at appropriate points
- [ ] Score calculations are correct

### Summary

```
---
PLAN: <PLAN-id> | <step count> steps | Goal: <one-line>
SCORE RANGE: <highest> to <lowest>
CRITICAL PATH: P-1 (<score>) -> P-2 (<score>) -> ...
FIRST STEP: P-1 | <action> | verify: <verification command>
RISK: <high risk count> high-risk steps | Total risk: <sum>
---

## Quick Start

1. Run: <P-1 first command>
2. Verify: <P-1 verification>
3. Continue to P-2...
```
