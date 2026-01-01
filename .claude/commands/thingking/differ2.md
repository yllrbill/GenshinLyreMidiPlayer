---
description: Pitfall diff only - Compare actual pitfalls hit vs research-warned pitfalls
argument-hint: [optional: path to session log or blocker card]
---

## Pitfall Differ (F only)

Compare pitfalls encountered during execution against research-warned pitfalls.

### Inputs
- Actual pitfalls from session (errors, blocks, unexpected behaviors)
- Research pack pitfall warnings
- Optional session log: $ARGUMENTS

### Pitfall Categories

- **HIT**: Actually encountered during execution
- **WARNED**: Research sources warned about
- **OVERLAP**: Both hit and warned
- **UNIQUE_HIT**: Hit but not warned (unknown unknowns)
- **UNIQUE_WARN**: Warned but not hit (avoided or not yet encountered)

### Output Structure

```yaml
pitfall_delta:
  session_source: <file path or "current session">
  research_source: <URL or file path>
  comparison_timestamp: <ISO8601>

  hit_pitfalls:
    - id: PH-<seq>
      pitfall: <what we encountered>
      when: <step ID or timestamp>
      symptoms:
        - <error message or behavior>
      impact:
        severity: <BLOCKING|DEGRADED|MINOR>
        time_lost: <estimate if known>
        recovery: <how we recovered, if at all>

  warned_pitfalls:
    - id: PW-<seq>
      pitfall: <what sources warn about>
      source: <URL>
      applies_to_us: <YES|NO|MAYBE>
      applicability_reason: <why it does/doesn't apply>
      prevention: <recommended prevention>

  overlap:
    - hit_id: <PH-id>
      warn_id: <PW-id>
      match_quality: <EXACT|SIMILAR|RELATED>
      could_have_avoided: <YES|NO|PARTIAL>
      lesson: <what we learn from this match>

  unique_hits:
    - id: <PH-id>
      pitfall: <what we hit but sources didn't warn>
      novel_insight: <is this worth documenting?>
      suggested_warning: <how to warn future sessions>

  unique_warnings:
    - id: <PW-id>
      pitfall: <sources warn but we didn't hit>
      status: <AVOIDED|NOT_REACHED|NOT_APPLICABLE>
      reason: <why we didn't hit it>

  guardrails:
    - id: GR-<seq>
      guardrail: <preventive measure>
      prevents: <which pitfall ID(s)>
      implementation:
        type: <CHECK|VALIDATION|CONSTRAINT|FALLBACK>
        location: <where to add>
        effort: <TRIVIAL|SMALL|MEDIUM>
      priority: <HIGH|MEDIUM|LOW>

  summary:
    total_hit: <count>
    total_warned: <count>
    overlap_count: <count>
    unique_hits_count: <count>
    unique_warnings_count: <count>
    avoidable_hits: <count that overlap shows we could have avoided>
```

### Hard Rules

1. **Deterministic**: Pitfalls sorted by severity/priority DESC
2. **Evidence-first**: Each hit must cite specific error/log; each warning must cite URL
3. **Fail-closed**: If session has no recorded failures, output NO_PITFALLS_RECORDED

### Guardrail Priority Scoring

```
Priority = Severity * (1 + WasWarned) * (1 - Effort/3)
Where:
- Severity: BLOCKING=3, DEGRADED=2, MINOR=1
- WasWarned: 1 if in overlap, 0 if unique hit
- Effort: TRIVIAL=0, SMALL=1, MEDIUM=2
```

### Summary

```
---
PITFALL DELTA: <hit> hit | <warned> warned | <overlap> overlap
AVOIDABLE: <n> pitfalls could have been avoided with research
TOP GUARDRAIL: <GR-id> | <guardrail one-line> | prevents <pitfall>
NEXT: Run /planplus1 to generate patch plan
---
```
