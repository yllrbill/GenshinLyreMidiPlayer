---
description: Blocker snapshot + evidence chain (A+B) - Local analysis only
argument-hint: [optional: one-line blocker context]
---
think harder.

## Envelope Output (REQUIRED FIRST)

**Every output MUST start with envelope:**

```yaml
envelope:
  command: thingking
  timestamp: <ISO8601>
  status: OK|ERROR
  error_code: <null|INSUFFICIENT_CONTEXT|MISSING_EVIDENCE>
  missing_inputs: []
  artifacts_read: []
  artifacts_written:
    - .claude/state/thinking/blocker.latest.yaml
    - .claude/state/thinking/trail.latest.yaml
  next: "/thingking_web '<search query based on root cause>'"
```

**If status = ERROR: Output envelope then STOP. No further content.**

---

## A. Blocker Card

Generate a compact Blocker Card for: "$ARGUMENTS"

### Output Structure

```yaml
blocker_id: B-<YYMMDD>-<hash6>  # hash6 = sha1(summary+first_evidence)[0:6]
timestamp: <ISO8601>
summary: <one-line blocker description>
category: <ENV|TOOL|DATA|LOGIC|PERMISSION|EXTERNAL>
needs: [RESEARCH]  # REQUIRED: what next steps are needed
evidence:
  - type: <error|log|observation>
    source: <file_path:line | command>
    content: <exact error message or observation>
    hash: <SHA256 if file, null if command output>
attempts:
  - step: <what was tried>
    result: <FAIL|PARTIAL|BLOCKED>
    reason: <why it failed>
root_cause_hypothesis:
  - hypothesis: <what might be wrong>
    confidence: <HIGH|MEDIUM|LOW>
    evidence_for: <supporting facts>
    evidence_against: <contradicting facts>
```

## B. Evidence Chain

Build a complete evidence chain from session start to blocker.

### Trail Structure

```yaml
trail:
  complete: <true|false>
  steps:
    - step_id: T-<seq>
      timestamp: <relative or absolute>
      action: <what was done>
      command: <exact command if applicable>
      files_touched:
        - path: <file path>
          operation: <READ|WRITE|EXEC>
      result: <SUCCESS|FAIL|PARTIAL>
      new_evidence: <what was learned>
      decision_rationale: <why this step was chosen>

branch_points:
  - step_id: <T-seq where alternative existed>
    chosen: <what was done>
    alternatives:
      - option: <what could have been done>
        why_not: <reason it was rejected>
        retrospect: <would it have been better? YES|NO|UNKNOWN>
```

## Artifact Output (REQUIRED)

After generating output, write to state files:

```powershell
# Blocker Card → .claude/state/thinking/blocker.latest.yaml
# Trail → .claude/state/thinking/trail.latest.yaml
```

The `needs` field in blocker.latest.yaml determines what `/thinking` routes to next:
- `needs: [RESEARCH]` → `/thingking_web`

## Hard Rules

1. **Envelope first**: Output MUST start with envelope block
2. **Deterministic**: All lists sorted alphabetically or by timestamp
3. **Evidence-first**: Every claim must have a source (file:line, command, or observation)
4. **Fail-closed**: If evidence is missing, mark as UNKNOWN, never guess
5. **No external calls**: This command uses only local context
6. **needs required**: Blocker Card MUST include `needs` array
7. **hash-based ID**: Use content hash for blocker_id suffix (enables cross-session alignment)
8. **STOP on ERROR**: If envelope.status = ERROR, output envelope then stop immediately

## Output Format

1. Output envelope (REQUIRED FIRST)
2. If status = OK, output blocker card and trail YAML
3. Write blocker.latest.yaml to `.claude/state/thinking/`
4. Write trail.latest.yaml to `.claude/state/thinking/`
5. Summarize:

```
---
BLOCKER: <B-id> | <category> | <one-line>
TRAIL: <step count> steps | <branch point count> branch points
ROOT CAUSE: <top hypothesis> (<confidence>)
NEEDS: <needs array>
ARTIFACTS: blocker.latest.yaml, trail.latest.yaml
NEXT: /thingking_web "<search query>"
---
```
