# Astra Orchestration — Delegation, Brief Shapes & Verification

## Parallel split

When a task divides cleanly into pieces, the main loop **splits it and runs
the pieces at the same time**, each with its own brief, lane and output
file. Splitting is part of directing: do not hand one delegate a job that
three could finish in a third of the time (for example running a `Sol` writer,
an `Opus` `medium` localized UI/PG unit on disjoint files, and a `Hydrogen`
read-only sweep in parallel across three independent pools!).

Split when all of these hold:

- **Independent.** No piece needs another piece's result to start.
- **Disjoint writes.** No two pieces write the same file (hard rule 10);
  otherwise give each its own worktree and name an integration unit.
- **Own acceptance.** Each piece has a check the main loop can run on its
  own.
- **Worth it.** The time saved exceeds the extra briefs and reviews. As a
  guide, a piece under about ten minutes of delegate time is not split off.

Read-only pieces run beside a single writer: building a test corpus,
measuring the old behaviour, reviewing a finished part, searching the
codebase, drafting the next unit's brief inputs. Look for these first when
the writing itself cannot be divided.

Do not split when the pieces touch the same files, when each depends on the
one before, when the work is timing-sensitive on one machine (benchmarks,
tests with short time limits, resource-limit probes), or when the pool is
past its "move" threshold (then spread across pools by headroom instead of
widening inside one).

Before launching, state the split in `.orchestration/orchestration-checkpoint.md`: the
pieces, the lane and files of each, what joins them and who integrates. Ramp
width from a few agents, not the full fleet. In the report to the operator,
say how many agents ran and why the work was or was not split.

## Brief shape per tier

How tightly to write depends on who reads it.

- **Opus delegate (`medium` / `high`, fairly loose).** State the goal and why
  it matters, the context it cannot discover on its own, the constraints and
  acceptance criteria. Leave the route to it; over-specifying an Opus brief
  removes the judgment it is there for. Use `medium` for PG/HTTP pipelines,
  restricted data, localized UI/prompt quality and open-ended architectural
  debugging; use `high` for escalation, cross-family review of Google-authored
  (or fallback GPT-authored) work, and peer architecture/security questions.
- **Sonnet (`high`, restricted data, network, installs, or Codex outage).**
  Name the files, steps, output format, boundaries and stop condition. Give
  each agent one task.
- **gpt-6.2-sol (detailed, complete).** Write numbered steps, exact paths
  and commands, the acceptance check for each step, edge cases and scope, and
  explicitly forbid committing (`do not commit`). Use **`high` by default** and
  **`xhigh`** for higher requirements, reasoning- or science-heavy sensitive
  work and escalation. Set an evidence target for standard code debugging and
  keep open architectural decisions with the main loop. Warn when local ports
  (`listen EPERM`) or browser caches are blocked in sandbox so Sol writes
  tests without assuming port access inside `codex exec`.
- **gemini-4-neon (peer reviewer / document judgment / second eye / Sol
  fallback).** Use `high` for independent cross-family review and
  re-review of GPT/Claude work, high-stakes document/PDF judgments, peer
  questions from Astra, and `Sol xhigh` ladder fallback when Codex is down.
  Use `medium` for a scoped second eye or `Sol high` ladder fallback when
  Codex is down. Give a bounded brief, an exact file list, commit/diff range
  and acceptance criteria, omitting author reasoning on reviews. Scope any verification tools to the brief, provide exact paths, and allow ~15 minutes. Route normal code implementation to the primary execution lane.
- **gemini-4-hydrogen (bounded).** This model takes extra reasoning steps and
  repeats tool calls before it settles, which uses up requests. Bound it:
  name the deliverable, the scope and the stop condition, and set the
  thinking level explicitly (`high` for media, PDFs, screenshots and wide
  reading; `medium` for lightweight lookups or ladder fallbacks; `low` only as
  the luna bulk fallback; `minimal` errors). For media, require a timestamp or
  page/image name on every item. For search, require the source URL beside
  each claim. Its weak
  spot is Terminal-Bench-Science at `medium` and below: keep scientific
  or long agentic terminal work at `high` or above.
- **deepseek-flash (explicit, cache-shaped).**
  Write with a strict output schema. Put everything shared across the fan-out
  (rules, examples, reference material) first and identical in every request,
  and the per-item part last so prompt caching saves cost/tokens. Set highest
  reasoning effort and `max_tokens >= 2048`. Treat vendor claims as unverified
  until sampled. Publishable material only (exclude personal data and secrets).
- **Terra / Haiku / Luna (bulk).** One mechanical rule set, stated exactly,
  with two or three input and output examples. Split the data into batches
  small enough that a bad batch is cheap to redo, have each batch write to its
  own output file, and sample the results before merging. Never ask this tier
  to decide what the rules should be.

Long briefs go in a file (`<work-dir>/<unit>/brief-*.md`); the
delegate prompt points at the file and carries the `LANE:` summary.

### The return contract

Every brief, on every lane, ends by asking for the same report shape, so the
main loop reads a few lines instead of a transcript:

```
STATUS: done | partial | blocked
RESULT: the conclusion or the artifact path, in one to three lines
EVIDENCE: files changed, commands run and their exit status, or sources
NOT DONE: anything skipped, assumed or left uncertain
```

A report with no `EVIDENCE` is treated as `partial`.

## Verification ladder

| Stakes | Check |
|---|---|
| Low: reversible, easy to see when wrong (a summary, a lookup) | Main loop reads the report and one sample |
| Medium: code or data that other work builds on | Run the tests or the acceptance command; read the diff; sample 2 to 5 percent of bulk output, more if the first sample shows errors |
| High: irreversible, security-relevant, or a decision the operator will act on | An independent reviewer that did not see the author's reasoning, from a **different model family** than the author, plus the main loop's own read |

For a cross-family check:
- **GPT-authored work (`Sol`, `Terra`, `Luna`, or Astra-authored policies):**
  send to `gemini-4-neon` `high` (the configured Gemini runner), or to **`Opus` `high`**
  (`claude -p`) if Neon is unavailable. Never use another GPT model.
- **Claude-authored work (`Opus`, `Sonnet`, `Haiku`):** send to
  `gemini-4-neon` `high` (the configured Gemini runner).
- **Google-authored work (`Hydrogen`, `Neon`):** record Astra's own check as
  Management review and send independent cross-family review to **`Opus`
  `high`** (`claude -p`). Only if `Opus` `high` is unavailable, a fresh
  `gemini-4-neon` `high` second eye is **same-family** and must be labeled
  `same-family review` in the final report.
- Use `gemini-4-neon` `medium` (or `Opus` `medium` on GPT work when Neon is
  down) for a scoped second eye. `deepseek-flash` checks only bulk or
  low-stakes output.

Review and verification invariants:
- **Severity classification (`BLOCKER` / `NIT`):** Independent review findings
  classify every item as **`BLOCKER`** (defect, regression, or spec/security/data
  violation — blocks acceptance) or **`NIT`** (non-blocking style or preference
  note — never triggers rework on its own).
- **Max 2 review rounds per unit (circuit breaker):** After 2 failed review
  rounds on a unit, escalate one tier with the accumulated evidence; if already
  at the highest eligible tier, stop and escalate to the operator with root
  cause and evidence (never loop infinitely).
- **High-stakes tie-breaker:** If the coordinator and independent cross-family
  reviewer disagree on a high-stakes, security, or irreversible finding, do not
  silently override — consult a 3rd authorized model family or present both
  positions with evidence to the operator.
- **Test Integrity Invariant:** Workers must never weaken, skip, or delete
  existing test assertions to make a suite pass unless explicitly required by
  the acceptance criteria; reviewers explicitly inspect test-file diffs and
  verify the relevant regression command.
