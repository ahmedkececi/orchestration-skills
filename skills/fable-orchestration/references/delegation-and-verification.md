# Fable Orchestration — Delegation, Brief Shapes & Verification

## Parallel split

When a task divides cleanly into pieces, the main loop **splits it and runs
the pieces at the same time**, each with its own brief, lane and output
file. Splitting is part of directing: do not hand one delegate a job that
three could finish in a third of the time.

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
tests with short time limits, resource-limit probes run alone), or when the
pool is past its "move" threshold (then spread across pools by headroom
instead of widening inside one).

Before launching, state the split in `.orchestration/orchestration-checkpoint.md`: the pieces, the lane
and files of each, what joins them and who integrates. Ramp width from a
few agents, not the full fleet. In the report to the operator, say how many
agents ran and why the work was or was not split.

## Brief shape per tier

How tightly to write depends on who reads it.

- **Opus (fairly loose).** State the goal and why it matters, the context it
  cannot discover on its own, the constraints, and what done looks like. Leave
  the route to it. Over-specifying an Opus brief removes the judgment it is
  there for.
- **Sonnet (restricted data, network or Codex unavailable).** Use
  `high` for restricted data under hard rule 7, required network access
  or package installs, or when Codex is full or down. Name the files,
  steps, output format, boundaries and stop condition. Give each agent one task.
- **gpt-6.2-sol (detailed, complete).** Write numbered steps, exact paths
  and commands, the acceptance check for each step, edge cases and scope, and
  explicitly forbid committing (`do not commit`).
  Use `high` by default and `xhigh` for higher-requirement, reasoning- or science-heavy sensitive
  work and escalation. Set an evidence target for standard code debugging
  and keep open architectural decisions with the main loop.
- **gpt-6.2-astra (peer question).** Give it the problem, the evidence, the
  options you see and where you are unsure, and ask for what you may be
  missing. Do not hand it your conclusion to confirm. Treat the answer as a
  peer review and disagree on evidence. **`medium` effort** by default;
  `high`, `xhigh` or `max` only when the question justifies it or the operator
  asks. Because astra drains the ChatGPT
  pool fastest, send one well-built question, not three loose ones, and do
  the reading that leads up to the question on another lane.
- **gemini-4-hydrogen (bounded).** This model takes extra reasoning steps and
  repeats tool calls before it settles, which uses up requests. Bound it:
  name the deliverable, the scope and the stop condition, and set the
  thinking level explicitly. Use `high` for media, PDFs and wide reading,
  `medium` for lightweight lookups or where the ladder specifies it, and
  `low` only as the luna bulk fallback. `minimal` returns an error.
  For media, require a timestamp or page number on every item so the result
  can be spot checked. For search, require the source URL beside each claim.
  Its weak spot is Terminal-Bench-Science at `medium` and below: keep scientific
  or long agentic terminal work at `high` or above.
- **gemini-4-neon (reviewer).** Use `high` for review and
  re-review. Give it a bounded brief, a file list and the acceptance criteria.
  Scope any verification tools to the brief, provide exact paths, and allow
  about 15 minutes. Route implementation to the execution lane.
- **deepseek-flash (explicit, cache-shaped).** Write it like a Sonnet brief
  with a strict output schema. Put everything shared across the fan-out
  (rules, examples, reference material) first and identical in every request,
  and the per-item part last: repeated input is billed at a small fraction of
  new input, so prompt order is most of the bill. Set reasoning effort
  explicitly. Its benchmark claims are vendor-reported; treat its output as
  unverified until checked. Check the configured endpoint's current rates
  before deferring work for a possible discount.
- **Terra / Haiku / gpt-6-luna (bulk).** One mechanical rule set, stated exactly,
  with two or three input and output examples. Split the data into batches
  small enough that a bad batch is cheap to redo, have each batch write to its
  own output file, and sample the results before merging. Never ask this tier
  to decide what the rules should be.

Long briefs go in a file; the prompt points at the file.

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
work to gemini-4-neon `high`. Send Google-authored work to
gpt-6.2-astra `medium`, or to Opus `high` if Codex is down. In an Astra-led
handover, the Astra main-loop check is separate from independent review.
If Opus is unavailable, a Neon `high` second eye on Google-authored work
is same-family. Use gemini-4-neon `medium` for a scoped second eye. Deepseek-flash checks only bulk or low-stakes
output. Label a same-family review as such in the final report.

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
