---
description: Patch plan from diffs - Generate actionable patches from all delta analyses
argument-hint: [optional: constraints or focus area]
---

## Patch Plan Generator (from deltas)

Generate concrete patches from goal, step, and pitfall deltas.

### Inputs
- Goal delta (from /goaldiffer)
- Step delta (from /differ1)
- Pitfall delta (from /differ2)
- Optional constraints: $ARGUMENTS

### Patch Types

- **GOAL_ADJUST**: Change goal/success criteria
- **STEP_ADD**: Add missing step
- **STEP_REMOVE**: Remove unnecessary step
- **STEP_REORDER**: Change step sequence
- **STEP_REPLACE**: Replace step with better approach
- **GUARDRAIL_ADD**: Add pitfall prevention

### Output Structure

```yaml
patch_plan:
  timestamp: <ISO8601>
  constraints: <from arguments or defaults>

  input_deltas:
    goal_delta_source: <file or "session">
    step_delta_count: <N>
    pitfall_delta_count: <N>

  patches:
    - id: PATCH-<seq>
      type: <GOAL_ADJUST|STEP_ADD|STEP_REMOVE|STEP_REORDER|STEP_REPLACE|GUARDRAIL_ADD>
      priority: <P0|P1|P2|P3>
      closes_delta:
        - delta_id: <GC-id|SD-id|PH-id|GR-id>
          delta_type: <GOAL|STEP|PITFALL>

      description: <what this patch does>
      rationale: <why this patch is needed>

      before:
        state: <current state description>
        location: <file:line or plan step>
      after:
        state: <desired state after patch>
        changes:
          - <specific change 1>
          - <specific change 2>

      implementation:
        commands:
          - <exact command to execute>
        files:
          - path: <file path>
            operation: <CREATE|MODIFY|DELETE>
            changes: <what changes in this file>

      verification:
        - check: <verification command or condition>
          expected: <what success looks like>
          on_fail: <what to do if verification fails>

      rollback:
        - step: <how to undo this patch>
          command: <rollback command if applicable>

      dependencies:
        requires: [<PATCH-id list>]
        blocks: [<PATCH-id list>]

      effort: <TRIVIAL|SMALL|MEDIUM|LARGE>
      risk: <LOW|MEDIUM|HIGH>
      evidence_strength: <0-3>

  priority_matrix:
    P0_critical:
      - <PATCH-id>: <one-line description>
    P1_high:
      - <PATCH-id>: <one-line description>
    P2_medium:
      - <PATCH-id>: <one-line description>
    P3_low:
      - <PATCH-id>: <one-line description>

  dependency_graph:
    - <PATCH-id> -> <PATCH-id>

  summary:
    total_patches: <N>
    by_type:
      GOAL_ADJUST: <count>
      STEP_ADD: <count>
      STEP_REMOVE: <count>
      STEP_REORDER: <count>
      STEP_REPLACE: <count>
      GUARDRAIL_ADD: <count>
    by_priority:
      P0: <count>
      P1: <count>
      P2: <count>
      P3: <count>
    estimated_total_effort: <SUM of effort scores>
    highest_risk_patch: <PATCH-id>
```

### Priority Assignment Rules

```
P0 (Critical): Closes BLOCKING pitfall OR HIGH impact goal conflict
P1 (High): Closes HIGH impact step delta OR multiple MEDIUM deltas
P2 (Medium): Closes MEDIUM impact deltas OR adds guardrails
P3 (Low): Closes LOW impact deltas OR optimizations
```

### Hard Rules

1. **Deterministic**: Patches sorted by priority, then by delta count closed DESC
2. **Evidence-first**: Each patch must cite which delta(s) it closes
3. **Fail-closed**: If no deltas provided, output NO_DELTAS_AVAILABLE
4. **Verification required**: Every patch must have verification step
5. **Rollback required**: Every patch with risk >= MEDIUM must have rollback

### Summary

```
---
PATCHES: <total> | P0:<n> P1:<n> P2:<n> P3:<n>
CLOSES: <goal deltas> goal | <step deltas> step | <pitfall deltas> pitfall
CRITICAL PATH: <PATCH-id> -> <PATCH-id> -> ...
FIRST ACTION: <PATCH-1 one-line description>
NEXT: Run /newplan to generate final execution plan
---
```
