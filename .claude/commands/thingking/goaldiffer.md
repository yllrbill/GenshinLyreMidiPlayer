---
description: Goal diff only - Compare actual goal vs research-recommended goal
argument-hint: [optional: path to plan file]
---

## Goal Differ (D only)

Compare the current plan/session goal against research-recommended end state.

### Inputs
- Actual goal from session or plan file
- Research pack recommended goal
- Optional plan file: $ARGUMENTS

### Alignment Categories

- **ALIGNED**: Goals match in scope and success criteria
- **PARTIAL**: Goals overlap but differ in scope or criteria
- **DIVERGENT**: Goals conflict or address different problems

### Output Structure

```yaml
goal_delta:
  plan_source: <file path or "session">
  research_source: <URL or file path>
  comparison_timestamp: <ISO8601>

  actual_goal:
    statement: <current goal as stated>
    success_criteria:
      - <criterion 1>
      - <criterion 2>
    scope: <what's included>
    constraints: <limitations>

  research_goal:
    statement: <recommended goal from sources>
    success_criteria:
      - <criterion from sources>
    scope: <recommended scope>
    constraints: <constraints from sources>
    source: <primary URL>

  alignment: <ALIGNED|PARTIAL|DIVERGENT>
  alignment_score: <0-100>

  conflicts:
    - id: GC-<seq>
      conflict: <specific mismatch description>
      actual_says: <what our goal implies>
      research_says: <what sources recommend>
      impact: <HIGH|MEDIUM|LOW>
      resolution:
        approach: <how to reconcile>
        favors: <ACTUAL|RESEARCH|HYBRID>
        rationale: <why this resolution>

  unified_goal:
    statement: <merged goal>
    success_criteria:
      - <merged criterion>
    changes_from_actual:
      - <what changed>
    changes_from_research:
      - <what changed>
    constraints_respected:
      - <constraint honored>
```

### Hard Rules

1. **Deterministic**: Conflicts sorted by impact DESC
2. **Evidence-first**: Research goal must cite source URL
3. **Fail-closed**: If goals cannot be compared, output INCOMPARABLE status with reason

### Summary

```
---
GOAL ALIGNMENT: <ALIGNED|PARTIAL|DIVERGENT> (<score>%)
CONFLICTS: <count> | HIGH:<n> MED:<n> LOW:<n>
UNIFIED: <one-line unified goal>
NEXT: Run /differ1 to compare steps
---
```
