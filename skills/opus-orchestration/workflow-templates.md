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
Return: result, changed files or evidence, checks run, blockers.
```

## Independent review brief

```text
Artifact or diff and relevant file paths:
Expected behavior and acceptance criteria:
Evidence or sources available to the reviewer:
Specific risks or questions within scope:
Return: severity, precise location, expected versus observed,
steps or evidence to reproduce, and an accept or hold recommendation.
```

Supply only context the reviewer needs. Keep the author's conclusions out of the initial brief. Ask the reviewer to identify any check it could not run.

## Handoff and routing record

```text
Goal and current baseline:
Accepted decisions and unresolved decisions:
Unit | owner or lane | state | path or evidence | next check
Pool | current status | reset time with timezone | fallback
Manager verification already run:
Independent review status:
Exact next action and completion condition:
```

Record a sanitized routing note with the model, effort, scope, result and reason for retry or fallback. Keep personal data, secrets and unnecessary provider logs out of a shared record.
