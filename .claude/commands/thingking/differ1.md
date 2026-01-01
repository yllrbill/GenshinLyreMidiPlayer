---
description: Step drift only - Compare actual steps vs research-recommended steps
argument-hint: [optional: path to plan file]
---

## Step Differ (E only)

Compare actual execution steps against research-recommended approach.

### Inputs
- Actual trail from session (or from /thingking output)
- Research pack (from /thingking_web or provided file)
- Optional plan file: $ARGUMENTS

### Delta Classification

For each discrepancy, classify as:
- **MISSING**: Research recommends, we lack
- **EXTRA**: We did, research doesn't mention
- **WRONG_ORDER**: Both have it, sequence differs
- **WRONG_TOOL**: Same goal, different method

### Output Structure

```yaml
step_delta:
  plan_source: <file path or "session">
  research_source: <URL or file path>
  comparison_timestamp: <ISO8601>

  items:
    - id: SD-<seq>
      delta_type: <MISSING|EXTRA|WRONG_ORDER|WRONG_TOOL>
      description: <concise description>
      actual:
        step: <what we did/planned>
        location: <file:line or step ID>
      research:
        step: <what sources recommend>
        source: <URL>
      evidence:
        type: <DOC|LOG|CODE|OBSERVATION>
        ref: <specific reference>
      impact: <HIGH|MEDIUM|LOW>
      impact_reason: <why this impact level>
      fix:
        action: <proposed correction>
        effort: <TRIVIAL|SMALL|MEDIUM|LARGE>
        risk: <LOW|MEDIUM|HIGH>

  summary:
    total_deltas: <N>
    by_type:
      MISSING: <count>
      EXTRA: <count>
      WRONG_ORDER: <count>
      WRONG_TOOL: <count>
    by_impact:
      HIGH: <count>
      MEDIUM: <count>
      LOW: <count>
    priority_fixes:
      - <SD-id>: <one-line fix summary>
```

### Hard Rules

1. **Deterministic**: Items sorted by impact DESC, then delta_type alphabetically
2. **Evidence-first**: Each delta must cite specific source
3. **Fail-closed**: If no research pack available, output MISSING_RESEARCH_PACK error

### Summary

```
---
STEP DELTA: <total> items | HIGH:<n> MED:<n> LOW:<n>
TOP FIX: <SD-id> | <delta_type> | <one-line description>
NEXT: Run /planplus1 to generate patches
---
```
