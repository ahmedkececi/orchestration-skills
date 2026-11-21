# Delegation and verification — Neon orchestration

Reference companion to [SKILL.md](../SKILL.md).

## Parallel split

When a task divides cleanly into pieces, the main loop **splits it and runs
the pieces at the same time**, each with its own brief, lane and output
file. Splitting is part of directing: do not hand one delegate a job that
three could finish in a third of the time.

Split when all of these hold:

- **Independent.** No piece needs another piece's result to start.
- **Disjoint writes.** No two pieces write the same file (hard rule 10);
  otherwise give each its own worktree (`git worktree` for Codex, or Swarm
  `workspace:"share"`/`"branch"`) and name an integration unit.
- **Own acceptance.** Each piece has a check the main loop can run on its
  own.
- **Worth it.** The time saved exceeds the extra briefs and reviews. As a
  guide, a piece under about ten minutes of delegate time is not split off
  (for Codex/agy sub-processes; sharded visual reviews across Swarm workers
  are worth splitting when 20+ screenshots exceed a single bounded turn).

Read-only pieces run beside a single writer: building a test corpus,
measuring the old behaviour, reviewing a finished part, searching the
codebase, drafting the next unit's brief inputs. Look for these first when
the writing itself cannot be divided.

Do not split when the pieces touch the same files, when each depends on the
one before, when the work is timing-sensitive on one machine (benchmarks,
tests with short time limits, resource-limit probes, or a local Vite dev
server reading the same `src/` files while a writer edits them), or when the
pool is past its "move" threshold (then spread across pools by headroom
instead of widening inside one).

Before launching, state the split in `.orchestration/orchestration-checkpoint.md`: the
pieces, the lane and files of each, what joins them and who integrates. Ramp
width from a few agents, not the full fleet. In the report to the operator,
say how many agents ran and why the work was or was not split.

## Brief shape per tier

How tightly to write depends on who reads it.

- **gpt-6.2-sol (detailed, complete).** Write numbered steps, exact paths
  and commands, the acceptance check for each step, edge cases and scope, and
  explicitly forbid committing (`do not commit`). Use **`high` by default** and
  **`xhigh`** for higher requirements, reasoning- or science-heavy sensitive
  work and escalation. Set an evidence target for standard code debugging and
  keep open architectural decisions with the main loop. Warn when local ports
  (`listen EPERM`) or browser caches are blocked in sandbox so Sol writes
  tests without assuming port access inside `codex exec`.
- **gpt-6.2-astra (peer question or cross-family review of Google code).**
  At **`medium` effort**. For a peer question, give
  it the problem, the evidence, the options you see and where you are unsure,
  and ask what may be missing — never hand it your conclusion to confirm.
  For cross-family review of Google-authored work, pass `-s read-only`, exact
  file list, diffs/commits and acceptance criteria without author reasoning.
  Because astra drains the ChatGPT pool fastest, send one well-built
  question/audit rather than three loose ones, and do preliminary reading on
  Hydrogen.
- **gemini-4-hydrogen (bounded).** This model takes extra reasoning steps and
  repeats tool calls before it settles, which uses up requests. Bound it:
  name the deliverable, the scope and the stop condition, and set the
  thinking level explicitly (`high` for media, PDFs, screenshots and wide
  reading; `medium` for lightweight lookups or ladder fallbacks; `low` only as
  the luna bulk fallback; `minimal` errors). Provide exact paths and make referenced files available to the runner. For media, require a timestamp or page/image name on every
  item. For search, require the source URL beside each claim.
  Its weak spot is Terminal-Bench-Science at `medium` and below: keep
  scientific or long agentic terminal work at `high` or above.
- **gemini-4-neon (reviewer / second eye / Sol fallback).**
  Use `high` for independent review and re-review of GPT/Claude work (and as
  `Sol xhigh` ladder fallback or last-resort same-family second opinion only
  when both Codex and Claude are unavailable), and `medium` for a scoped
  second eye or `Sol high` ladder fallback when Codex is unavailable. Give a
  bounded brief, an exact file list, commit/diff range, and acceptance
  criteria, omitting the author's reasoning on reviews. Scope any verification
  tools to the brief, provide exact paths, and allow ~15 minutes. Route
  normal code implementation to `gpt-6.2-sol`, not here.
- **deepseek-flash (explicit, cache-shaped).**
  Write with a strict output schema. Put everything shared across the fan-out
  (rules, examples, reference material) first and identical in every request,
  and the per-item part last so prompt caching saves cost/tokens. Set highest
  reasoning effort and `max_tokens >= 2048`. Treat vendor claims as unverified
  until sampled. Publishable material only (exclude personal data and secrets).
- **Terra / Luna / Haiku (bulk).** One mechanical rule set, stated exactly,
  with two or three input and output examples. Split the data into batches
  small enough that a bad batch is cheap to redo, have each batch write to its
  own output file, and sample the results before merging. Never ask this tier
  to decide what the rules should be.
- **Opus delegate / Mythos/Fable advisor / Sonnet.** Opus (`medium`): goal, context,
  constraints, acceptance criteria (fairly loose). Sonnet (`high`): explicit
  files, steps, boundaries, one task per agent. Mythos/Fable (`medium`, advisor
  only): single peer question on the hardest calls.

Long briefs go in a file (`<work-dir>/<unit>/brief-*.md`); the
delegate prompt or Swarm message points at the file and carries the `LANE:`
summary.

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

For a cross-family check, send Claude- or GPT-authored
work to a fresh isolated `gemini-4-neon` `high` (Swarm worker or the configured Gemini runner).
Send Google-authored work (or skill/policy/script changes authored by the Neon
main loop) to `gpt-6.2-astra` `medium` (`codex exec -s read-only`), or to Opus
`high` if Codex is unavailable. When the Neon main loop inspects GPT work
itself before or after delegation, record the main loop's read/test run
separately from the fresh `gemini-4-neon` `high` reviewer's report so no
reasoning leaks between author, main loop, and independent reviewer. If both
Codex and Claude are unavailable, a fresh Neon `high` second eye on
Google-authored work is **same-family** and must be labeled as such in the
final report. Use `gemini-4-neon` `medium` for a scoped second eye on GPT or
Claude artifacts (or `gpt-6.2-astra` `medium` on Google artifacts).
`deepseek-flash` checks only bulk or low-stakes output.

### Independent review rules and Test Integrity Invariant

- **`BLOCKER` vs `NIT` severity classification.** Every finding in an independent review is classified as either **`BLOCKER`** (defect, regression, or spec/security/data violation — blocks acceptance) or **`NIT`** (non-blocking style or preference note — never triggers rework on its own).
- **Max 2 review rounds (circuit breaker).** After 2 failed review rounds on a unit, escalate one tier with full evidence; if already at the highest eligible tier, stop and escalate to the operator with root cause and evidence rather than looping indefinitely.
- **High-stakes tie-breaker.** If the coordinator and independent cross-family reviewer disagree on a high-stakes, security, or irreversible finding, never silently override — consult a 3rd authorized model family or present both positions with evidence to the operator for decision.
- **Test Integrity Invariant.** Workers must never weaken, skip, or delete existing test assertions to make a suite pass unless explicitly required by the acceptance criteria. Independent reviewers must explicitly inspect test-file diffs and verify the relevant regression check ran cleanly.
