# Workflow templates

## Work brief

```text
Goal:
Why this unit exists:
Inputs and approved data scope:
Owned files or output location:
Required behavior and constraints:
Steps, where ordering matters:
Acceptance checks and exact commands:
Stop conditions or decisions reserved for the manager:
Return (4-line contract — missing EVIDENCE counts as partial):
  STATUS: done | partial | blocked
  RESULT: concise summary and changed file paths
  EVIDENCE: exact verification commands run and key output
  NOT DONE: remaining items, skipped checks, or blockers (or "none")
```

## Independent review brief

```text
Artifact or diff and relevant file paths:
Expected behavior and acceptance criteria:
Evidence or sources available to the reviewer:
Specific risks or questions within scope:
Return: severity, precise location, expected versus observed,
steps or evidence to reproduce, checks not run, and an accept or hold recommendation.
```

Supply only context the reviewer needs. Keep the author's conclusions out of the initial brief. Ask the reviewer to identify any check it could not run.

## Handoff and routing record

Save active handoff state to `.orchestration/orchestration-checkpoint.md`:

```markdown
Goal and current baseline:
Accepted decisions and unresolved decisions:

| Unit | Owner or lane | State | Path or evidence | Next check |
| --- | --- | --- | --- | --- |
| | | | | |

| Pool | Current status | Reset time with timezone | Fallback |
| --- | --- | --- | --- |
| | | | |

Manager verification already run:
Independent review status:
Exact next action and completion condition:
```

Append a sanitized routing note to `.orchestration/orchestration-ledger.md` with the model, effort, scope, result and reason for retry or fallback. Keep personal data, secrets and unnecessary provider logs out of shared records.
