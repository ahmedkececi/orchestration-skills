---
name: opus-orchestration
description: >-
  Delegation and quota-failover policy for a multi-model agent stack run on subscriptions (Claude, ChatGPT/Codex, Gemini) plus one metered API (DeepSeek), where the main loop is Claude Opus 5.5 at high or xhigh effort (the variant of fable-orchestration for when Mythos/Fable is unavailable or its applicable allowance is spent). Coordinate delegation, review, usage limits and handoffs for this manager.
---

# Orchestration & delegation policy, Opus main loop (subscription stack)

Apply the routing defaults using the providers, runners, permissions, and spending limits authorized for this project. Start with the [project profile example](project-profile.example.md) and consult the [workflow templates](workflow-templates.md) for briefs and handoffs. Treat an unconfigured lane as unavailable and use the applicable fallback. Use the model and effort identifiers supported by the installed clients.

The main loop is a manager: it thinks, decides, writes briefs, directs and reviews, and
never does the work itself, however small; Mythos/Fable, when the operator has allowance for it,
is consulted only as an advisor on the hardest calls. Work is routed by input type, data
sensitivity, difficulty and remaining quota. gpt-6.2-sol at high is the primary execution
lane (xhigh for higher requirements and escalation) for simple to medium work. Sonnet high
covers restricted data, network or package installs and Codex outages. Opus delegates at
medium cover real PG/HTTP, restricted data, localized UI or prompts and open-ended
architectural debugging. gpt-6.2-astra gives second opinions; gemini-4-hydrogen takes
video, audio and large-document intake, search-grounded lookups and wide reading;
deepseek-flash takes large bulk jobs and low-stakes checks; gpt-6.1-terra medium (pilot),
Haiku 5.5 or gpt-6-luna take bulk cleanup. Load at the start of every management session
whose main loop runs on Opus and before any task that would edit a file or run a command;
also whenever spawning sub-agents (Agent tool, Workflow agent() calls, codex, gemini or
deepseek lanes), planning any delegation, or when any provider returns a rate-limit, quota
or usage-limit error.

A routing policy for a stack with **one strong main-loop model** and
**delegate lanes across four model families**. Claude, ChatGPT/Codex and
Gemini run on subscriptions; DeepSeek runs on a paid API key.

On subscriptions, token price is not the constraint. **Allowance is.** Each
subscription is a pool that empties and refills on a schedule, and the stack
stops when the wrong pool runs dry.

Core law: **the main loop is the manager, not a worker.** It thinks, decides,
writes briefs, directs the lanes and reviews what comes back. It does not do
the work itself, however small. All execution goes to a lane that can carry
it, in the pool that can best afford it.

## The manager rule

The main loop runs the stack the way an executive runs a company. This is
the operator's standing instruction to delegate each in-scope work item in
the management session, including small tasks. Treat it as the operator's
request to delegate wherever the host accepts standing authorization. Follow
any separate approval requirements set by the host or project.

**The main loop does:**

- **Think.** Understand the request, weigh options, make the architecture and
  design decisions and the hard calls.
- **Direct.** Split the work into units, pick the lane, write the brief,
  launch and follow the delegate, decide what happens next.
- **Review.** Read the report, read the diff or a sample, run read-only
  checks (tests, type check, build, `git diff`, usage), then accept the work
  or send it back.
- **Report.** Talk to the operator and give the final synthesis.
- **Keep the management records.** Briefs, checkpoint, handover note, ledger,
  provider state, this policy and the project rule files, memory. It also
  commits accepted work: the commit is the manager's sign-off.

**The main loop does not:**

- Edit project code, content, data, tests or product documentation.
- Run pipelines, generators, migrations, installs or any command whose
  purpose is to produce or change the deliverable.
- Fix a defect it found in review, not even one line. The defect goes back
  to a lane with the evidence (same lane first, then hard rule 8).
- Read widely to get oriented. A delegate reads and returns the conclusion;
  the main loop reads only what it must judge.
- Take a unit over because the delegate is slow or has failed. It rewrites
  the brief, raises effort or escalates a tier.

**There is no "small task" exception.** A one-line change still goes to the
lightest lane that can carry it, with a brief of a few lines (the file, the
change, the check). That a delegation costs more than the edit is an
accepted cost.

**The only exceptions:**

1. The operator tells the main loop, in words, to do a named thing itself.
   That task only.
2. A step that needs the operator's approval in this conversation and cannot
   be handed over (for example an approved write to a live system). The main
   loop performs exactly the approved step; a delegate prepared it.
3. Answering the operator's question from what the main loop already knows
   or from a few targeted reads.

Before any tool call that writes a file or runs a command, ask: is this
thinking, directing, reviewing or record-keeping? If not, it is a brief.

## What changes with an Opus main loop

1. **Shared main-loop allowance.** Check whether Mythos/Fable has a separate model allowance on your plan. The main loop now spends from the shared Claude pool directly, so
   every turn it takes competes with every Claude delegate. Volume belongs in
   other pools even more strictly than under Mythos/Fable.
2. **Effort is the main loop's dial.** Run the main loop at `high` by
   default. Raise to `xhigh` for architecture, specs, irreversible decisions,
   security review and the final synthesis of a large job; drop back to
   `high` for routine orchestration (writing a brief from a known template,
   reading a report, committing). Never run the main loop at `max` without
   the operator asking.
3. **Opus as a sub-agent is the same model, not a stronger one.** An Opus
   delegate provides context isolation and parallelism for the work listed
   in hard rule 4. Use `medium` for that work and `high` for escalation.
   Reserve `xhigh` for the main loop.
4. **Mythos/Fable is an advisor, not a lane.** When the operator has Mythos/Fable allowance
   and has an authorized runner, the main loop may send Mythos/Fable **one** well-built peer
   question on a decision that is both hard and expensive to get wrong
   (architecture with long-lived consequences, a security model, a data
   migration, a contested product call). Never fan out to Mythos/Fable, never give it
   execution work, and never wait on it for routine progress. If Mythos/Fable is
   unavailable, send the same question to `gemini-4-neon` `high` first, then
   to `gpt-6.2-astra` `medium` as specified in the Failover ladders.
5. **The second-opinion rule tightens.** Opus judges alone more often than
   Mythos/Fable did, so a high-stakes call gets a peer question to astra (or Mythos/Fable,
   per point 4) as a matter of course, not only when the main loop feels
   unsure.

## The four pools

| Pool | Models in it | How it limits | Check with |
|---|---|---|---|
| **Claude** subscription | Opus (main loop and delegates), Sonnet, Haiku; Mythos/Fable when used as advisor | A five-hour window and a weekly limit, shared by all models and by chat and Claude Code. A Mythos/Fable model may have a separate allowance; check the selected model and plan. | `/usage` |
| **ChatGPT** subscription | gpt-6.2-astra, gpt-6.2-sol, gpt-6-luna | A weekly allowance shared by Work and Codex; lower plans also have a five-hour window. Astra drains it several times faster than Sol; Luna barely touches it. | `/status` in Codex |
| **Gemini** subscription | gemini-4-hydrogen, gemini-4-neon | Hydrogen uses plan-based request limits. Antigravity Neon on Google AI Pro/Ultra has a rolling five-hour window and a weekly cap. | `/stats` in Gemini CLI, Antigravity usage |
| **DeepSeek** API (metered) | deepseek-flash | Prepaid balance or the configured gateway's limits. | Provider balance or gateway quota reporting |

Consequences:

- **The main loop and every Claude delegate share one pool.** A large Opus or
  Sonnet fan-out shortens the main loop's own session. Heavy volume belongs in
  another pool.
- **The pools are independent.** Spreading a big job across them up front
  beats draining one and failing over.
- **DeepSeek draws from an API budget.** Use it for eligible bulk work
  within the balance and limits approved in the project profile.

## Routing procedure

Choose the first matching execution lane. Apply hard rule 7 before routing
and apply the final high-stakes check separately.

1. **Is it thinking, a decision, a brief, a review or the final synthesis?**
   Main loop, at `xhigh` if the call is long-lived or irreversible. Nothing
   else stays there ("The manager rule").
2. **Is it small?** Delegate to gpt-6.2-sol `high` with a brief that
   names the file, change and check. For the Opus cases in hard rule 4, go
   to the matching Opus lane. Skip this shortcut when a specialized
   input or work type below applies. Use Sonnet `high` for restricted data, required
   network access or package installs, or when Codex is full or down.
3. **Is the input video or audio, or a pile of long PDFs or screenshots to
   turn into text?** `gemini-4-hydrogen`.
4. **Is it restricted data** (secrets, credentials, personal or client data)?
   Continue through the applicable lanes using Claude only, unless the
   operator has cleared another provider.
5. **Is it mechanical work over many items?** For small and medium cleanup,
   sample the first gpt-6.1-terra `medium` job. Use Terra first for
   unrestricted batches once the sample passes. Haiku `high` covers batches
   while the pilot is pending, after a failed pilot, for restricted data or
   when Codex is down. For very large jobs use gpt-6-luna `high` or
   deepseek-flash (publishable material only).
6. **Is it wide reading that returns a conclusion** (a large codebase sweep,
   many documents, web research with sources)? `gemini-4-hydrogen`, which
   keeps that volume out of the Claude pool.
7. **Is it execution with a clear spec?** Send a step-by-step brief to
   gpt-6.2-sol `high`. Use `xhigh` for higher-requirement, reasoning- or science-heavy sensitive
   work and escalation. Apply the network and data exceptions in steps 2
   and 4 and the Opus cases in step 8.
8. **Otherwise route by task.** Use Opus `medium` only for real PG/HTTP
   requiring local ports or network access, restricted data, localized
   UI or prompt quality, and open-ended architectural debugging. Trial
   gpt-6.2-sol on three standard code-debugging jobs (see Routing ledger).
   Use Sol `high` for other simple-to-medium work and Sonnet `high` only
   under the exceptions in step 2.
9. **Is it a high-stakes call?** Add a peer question to `gpt-6.2-astra` in
   parallel, or to Mythos/Fable if the operator has it connected. This is an
   addition to the lane above, not a replacement.

## The routing table

| Work                                                                                                                        | Goes to                                                                                                         | How to call it                                                                      | Brief style                                                              |
| --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Architecture, specs, hard judgment, briefs, direction, review, final synthesis (no execution)                               | **Main loop** (Opus 5.5, `high`; `xhigh` for long-lived or irreversible calls)                                  | itself                                                                              | n/a                                                                      |
| Advice on the hardest calls, when available                                                                                 | **Mythos/Fable** (advisor only)                                                                                    | the operator's advisor connection, or one sub-agent call when the operator names it | One peer question: problem, evidence, options, where unsure              |
| Execution with a clear spec: implementation from a written design, migrations, test suites, refactors with fixed scope | **gpt-6.2-sol** (`high` by default, `xhigh` for higher-requirement, reasoning- or science-heavy sensitive work and escalation) | `codex exec -m gpt-6.2-sol`, effort `high` or `xhigh` as specified | Detailed and step by step, nothing left implicit |
| Real PG/HTTP requiring local ports or network access, restricted data that needs Opus, localized UI or prompt quality, open-ended architectural debugging | **Opus** sub-agent, `medium`. Use **gpt-6.2-sol** for the three-job standard code-debugging trial | `model: 'opus'`, effort `medium`. Use the Sol command above for the trial | Goal, context, constraints and acceptance criteria. Use a step-by-step brief for Sol |
| Simple-medium: scoped edits, pattern clones, lookups, templated work, straightforward reading and summarizing | **gpt-6.2-sol** `high`. **Sonnet** `high` only for restricted data, required network access or package installs, or when Codex is full or down | `codex exec -m gpt-6.2-sol`, effort `high`, or `model: 'sonnet'`, effort `high` | Named files, steps, output shape and boundaries |
| Second opinion, out-of-the-box thinking, an angle the main loop may be missing                                              | **gpt-6.2-astra**                                                                                                 | `codex exec -m gpt-6.2-astra`, effort `medium`                                        | The open question plus the evidence, as to a peer                        |
| Video, audio, long PDFs, screenshot sets turned into structured text                                                        | **gemini-4-hydrogen**                                                                                           | `gemini -m gemini-4-hydrogen -p`, effort `high`                                     | Bounded: what to extract, output schema, timestamp or page on every item |
| Wide reading and search-grounded lookups that return a conclusion with sources                                              | **gemini-4-hydrogen**                                                                                           | same                                                                                | The question, the scope, a stop condition, sources required              |
| Very large bulk jobs, long-prompt bulk, bulk overflow from Haiku or luna                                                    | **deepseek-flash**                                                                                              | OpenAI- or Anthropic-compatible client                                              | Exact rules, output schema, shared material first, per-item part last    |
| Independent check from a different model family | Claude or GPT wrote it → **gemini-4-neon** `high`. Google wrote it → **gpt-6.2-astra** `medium`, or **Opus** `high` if Codex is down | Neon via agy, Astra via `codex exec -m gpt-6.2-astra` at `medium`, Opus via `model: 'opus'` at `high`. See the Verification ladder | The artifact, file list and acceptance criteria. Omit the author's reasoning |
| Second eye on a scoped question | **gemini-4-neon** `medium` | agy, `--model gemini-4-neon-medium` | Name the files, the question and the evidence to check. |
| Bulk cleanup: normalizing, deduplicating, classifying, extracting | **terra (pilot) / Haiku** (small and medium). Sample the first Terra job. If it passes cleanly, use Terra first for unrestricted small and medium jobs. Use **Haiku 5.5** `high` for restricted data or when Codex is down. Use **gpt-6-luna** `high` for large jobs | `codex exec -m gpt-6.1-terra` at `medium`, `model: 'haiku'` at `high`, or `codex exec -m gpt-6-luna` at `high` | Exact rules with examples, small batches and spot checks |

Integration (merging several delegates' outputs, resolving conflicts between
them, wiring pieces together) is execution, not synthesis: the main loop
decides how the pieces fit and a lane does the merging from a brief that
states those decisions.

**Default efforts per lane** (pin them on every call; effort can change relative performance):
main loop Opus `high` (`xhigh` for long-lived calls), Opus delegates
`medium`, Sonnet `high`, Haiku `high`, gpt-6.2-sol `high` (default), Sol `xhigh` for higher-requirement, reasoning- or
science-heavy sensitive work and escalation, gpt-6.1-terra `medium`
(cleanup pilot), gpt-6.2-astra `medium`, gpt-6-luna `high`, gemini-4-hydrogen
`high`, gemini-4-neon `high` (independent review) or `medium` (second eye),
deepseek-flash at its highest reasoning
setting. Measured profile of each in "Model notes".

Reserve deepseek-flash checks for bulk or low-stakes work.

## The hard rules

1. **Always pass an explicit `model:`** on every Agent tool call, Workflow
   `agent()` call and `meta.phases` entry, and an explicit `-m` on every CLI
   lane. Omitting it inherits the main-loop model and its effort.
2. **Mythos/Fable is never a sub-agent tier.** Use it only as an advisor as defined
   above, and only when the operator has allowance for it and has connected it
   or names it for the task.
3. **Route by difficulty, then pick the lightest lane that can carry it.**
   When unsure between two tiers, take the lighter one and verify the result;
   escalate one tier on failure rather than starting high.
4. **Use gpt-6.2-sol `high` by default.** Use Sol `xhigh` for higher-requirement, reasoning- or
   science-heavy sensitive work and escalation. Reserve Opus delegates at
   `medium` for real PG/HTTP requiring local ports or network access,
   restricted data, localized UI or prompt quality, and open-ended
   architectural debugging. Trial Sol on three standard code-debugging
   jobs under the Routing ledger. Sonnet `high` covers restricted data,
   required network access or package installs, or Codex full/down. Follow
   hard rule 7 and the routing table for data and specialized lanes. The
   failover ladder also specifies Opus `high` for Sol `high`/`xhigh` and Opus `medium` for Neon
   `medium` work when their earlier fallbacks are unavailable.
5. **The main loop keeps its own context lean.** Wide reading, file dumps and
   raw data go to a delegate that returns the conclusion; the main loop reads
   what it must judge.
6. **A delegate's report is a claim.** Check the diff, run the tests or read a
   sample before reporting it as done.
7. **Data leaves only as far as it must.** Restricted data stays on Claude
   tiers unless the operator has cleared a provider for it. The hosted
   DeepSeek API gets only material the operator would be comfortable
   publishing, unless the operator says otherwise. Strip secrets from every brief regardless of destination.
8. **Two failed attempts at a tier, then escalate one tier, carrying the
   evidence**: what was tried, the failing output, the suspected cause. Never
   restart the higher tier from zero, and never loop a third
   time at the same tier with the same brief.
9. **Never buy your way past a limit.** Usage credits, plan upgrades and paid
   API keys for Claude, OpenAI or Google are operator decisions. Use the DeepSeek lane within the project profile's approved budget. Tell
   the operator before an unusually large job.
10. **One writer per file.** Parallel agents get disjoint file sets or
    separate worktrees.
11. **The main loop does not execute.** It thinks, directs, reviews and keeps
    the management records ("The manager rule"). No task is small enough to
    do itself.
12. **Review findings go back.** A defect found in review returns to a lane
    with the evidence; the main loop never patches it.

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

Before launching, state the split in the checkpoint: the pieces, the lane
and files of each, what joins them and who integrates. Ramp width from a
few agents, not the full fleet. In the report to the operator, say how many
agents ran and why the work was or was not split.

## Brief shape per tier

How tightly to write depends on who reads it.

- **Mythos/Fable (advisor).** One question, built like an astra question: the
  problem, the evidence, the options and where the main loop is unsure. Ask
  what is being missed; do not ask it to confirm a conclusion. Treat the
  answer as a peer review.
- **Opus delegate (fairly loose).** State the goal and why it matters, the context it
  cannot discover on its own, the constraints, and what done looks like. Leave
  the route to it. Over-specifying an Opus brief removes the judgment it is
  there for.
- **Sonnet (restricted data, network or Codex unavailable).** Use
  `high` for restricted data under hard rule 7, required network access
  or package installs, or when Codex is full or down. Name the files,
  steps, output format, boundaries and stop condition. Give each agent one task.
- **gpt-6.2-sol (detailed, complete).** Write numbered steps, exact paths
  and commands, the acceptance check for each step, edge cases and scope.
  Use `high` by default and `xhigh` for higher-requirement, reasoning- or science-heavy sensitive
  work and escalation. Set an evidence target for standard code debugging
  and keep open architectural decisions with the main loop.
- **gpt-6.2-astra (peer question).** Give it the problem, the evidence, the
  options you see and where you are unsure, and ask for what you may be
  missing. Do not hand it your conclusion to confirm. Treat the answer as a
  peer review and disagree on evidence. **`medium` effort**; higher only when the
  operator asks. Because astra drains the ChatGPT
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
  It can run Node-based checks with `--allow node`. Allow about 15 minutes.
  Route implementation to the execution lane.
- **deepseek-flash (explicit, cache-shaped).** Write it like a Sonnet brief
  with a strict output schema. Put everything shared across the fan-out
  (rules, examples, reference material) first and identical in every request,
  and the per-item part last: repeated input is billed at a small fraction of
  new input, so prompt order is most of the bill. Set reasoning effort
  explicitly. Its benchmark claims are vendor-reported; treat its output as
  unverified until checked. Check the configured endpoint's current rates
  before deferring work for a possible discount.
- **Terra / Haiku 5.5 / gpt-6-luna (bulk).** One mechanical rule set, stated exactly,
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
| High: irreversible, security-relevant, or a decision the operator will act on | An independent reviewer that did not see the author's reasoning, from a **different model family** than the author, plus the main loop's own read at `xhigh` |

For a cross-family check, send Claude- or GPT-authored
work to gemini-4-neon `high`. Send Google-authored work to
gpt-6.2-astra `medium`, or to Opus `high` if Codex is down. In an Astra-led
handover, the Astra main-loop check is separate from independent review.
If Opus is unavailable, a Neon `high` second eye on Google-authored work
is same-family. Use gemini-4-neon `medium` for a scoped second eye. Deepseek-flash checks only bulk or low-stakes
output. Label a same-family review as such in the final report.

## Quota levers

- **Check before a big fan-out.** Look at remaining allowance in each pool.
  If a fleet would plausibly use more than half of what is left in one pool's
  current window, split it across pools now.
- **Keep volume out of the Claude pool.** The main loop lives there now.
  Reading goes to Gemini, bulk to
  luna or DeepSeek, mechanical GPT-shaped execution to Sol. Claude delegates
  are for work that needs Claude-tier judgment.
- **Protect the main loop.** When the Claude pool runs low, the main loop
  drops to `high` effort and its own review narrows too: it is already plan,
  direction and review only (the manager rule), and now every read and
  verification run also goes to a non-Claude delegate and reports are held
  to the four-line contract.
- **Spend astra and Mythos/Fable last.** Astra is the fastest drain on the ChatGPT
  pool; preserve the Mythos/Fable advisor's remaining allowance for hard calls.
- **Effort before tier.** When a result is close but not right, raise effort
  one step on the same tier before moving up. When a lane is routine, lower
  it; high effort uses allowance faster.
- **Start heavy fleets just after a window resets**, and ramp concurrency
  from a quarter of the planned width. Bursts trip per-minute limits.

## Approaching a limit: load balancing

The aim is to keep working as long as possible with no drop in quality, and
as fast as possible within that. Act **before** a pool runs dry, not after.

1. **Read live usage, not estimates.** Claude: `get_usage` (or `/usage`);
   Codex: `/status`; agy: the run log's `status` and quota errors; DeepSeek: provider quota or balance. Price-per-task figures do not measure subscription burn.
2. **Thresholds.** Past the "move" mark, new
   delegated units go to the equivalent lane (the 1st fallback in the
   ladder below) instead of queuing on the pool; past the "stop" mark, no
   new large job starts there and running units finish. The main loop keeps
   working past both.

   | Pool | Move delegated units | Stop large jobs, write the checkpoint |
   |---|---|---|
   | Claude five-hour window | **85 %** | **90 %** (keep the checkpoint current from 85 %) |
   | Claude weekly limit | **95 %** | **95 %** |
   | Codex, agy: weekly | **95 %** | **95 %** |
   | Codex/Neon five-hour, Hydrogen daily | **85 %** | **90 %** |

   The five-hour window resets within hours, so it is used later; the weekly
   limit costs days when it runs out, so delegated work leaves it earlier.
3. **Spread by headroom.** When a fan-out has several equivalent lanes,
   split units in proportion to each pool's remaining allowance, not evenly.
   Available free capacity takes bulk first.
4. **Equivalent means equal or better on the lane's task profile**, within 3
   points on a comparable scale. See Model notes for the workspace and historical data.
   Among equivalents, take the
   lowest time per task. A model far above the lane is used only if it is
   also no slower and lighter on its pool than the next equivalent. **When
   two fallbacks are both equivalent, the pool with more headroom wins and
   speed only breaks a tie**; that is what keeps use even across pools.
5. **Protect Gemini's media and review lanes at the standard threshold.**
   Hydrogen covers media, wide reading and search, and Neon covers second-eye
   work, independent review and media fallback. Gemini uses the same standard
   thresholds as every other pool (**85 %** move / **90 %** stop on the
   five-hour or daily window, **95 %** weekly). When Gemini nears
   85 %, prioritize media first.
6. **Raise verification for weaker fallbacks.** For Hydrogen's
   accuracy-heavy reading, Astra `medium` is **below** on accuracy. For
   Neon `high` review, Astra `medium` is **below** on accuracy, knowledge
   and reasoning. Use Opus `high` for GPT-authored work in that ladder,
   marked **below** on all profiles. For Neon `medium` second-eye work,
   accuracy is unmeasured (n = 0). The operator marks Astra `medium`
   **below** on accuracy there. Opus `medium` is **below** on code,
   reasoning and knowledge in the second-eye ladder. Raise verification
   one step, label the output and prefer waiting when reset is within
   about 30 minutes.
7. **agy's Claude models are not a fallback lane.** Reserve them for configured short jobs. agy keeps
   them for short single jobs only.

## When a limit is hit

### 1. Classify the error

| Class | What it looks like | Meaning |
|---|---|---|
| **A. Throttle** | HTTP 429 with a short retry hint; "slow down and try again after N seconds"; HTTP 503 or 529 overloaded; Claude Code's "Server is temporarily limiting requests (not your usage limit)"; DeepSeek 429 | Too fast right now. Capacity returns in seconds to minutes. |
| **B. Window exhausted** | "5-hour limit reached · resets [time]"; a Codex usage-limit message with a reset time; Gemini `RESOURCE_EXHAUSTED` on the daily quota | This window's allowance is gone. A reset time is known, hours away at most. |
| **C. Plan exhausted** | "You've hit your weekly limit"; "Model-specific usage limit reached"; DeepSeek balance depleted (HTTP 402) | Nothing returns without waiting days or paying. |
| **D. Not a limit** | HTTP 400, 401, 403; context length exceeded; model not found; content refusal | The request is wrong. No other provider will fix it. |
| **E. Lane's own failure** | The model stops on its own mistake, not on the work or a limit: a tool-permission denial it caused (e.g. agy: a shell command typed into the file-read tool, a read outside the workspace), an early exit with no output, a file-lock collision | The lane is unreliable for this unit right now. |

Read the message, not only the status code: Claude Code and Codex state the
reset time, and Gemini's error description says which limit was hit. When the
class is unclear, treat it as A once; if the same error returns after the
backoff, treat it as B.

### 2. Act on the class

- **A, throttle.** Wait for the server's retry hint, or 5, 20, then 60
  seconds with jitter. Halve that lane's concurrency before retrying; for
  DeepSeek, narrowing concurrency is the whole fix. Three attempts, then mark
  the lane down for 15 minutes and continue as B.
- **B, window exhausted.** Record the reset time. If it is within about 20
  minutes and other lanes have work, reorder and come back. Otherwise fail
  over along the ladder. Tell the operator once.
- **C, plan exhausted.** Mark the affected model or shared pool down until its reset,
  fail over, and tell the operator, naming any paid options without taking them. For a
  depleted DeepSeek balance, ask the operator to top up.
- **D, not a limit.** Do not fail over. Fix the request.
- **E, lane's own failure.** Count these per lane in the session ledger. A failure the main loop caused (a wrong path or conversation id in the brief, overlapping `--files`) does not count. After each one, add the trap to the brief and relaunch on the same lane. When a lane has made **more than three** (on the fourth), new units for that lane go to its 1st fallback in the ladder below (for Hydrogen doing implementation, gpt-6.2-sol), and a unit that was running moves too. If the fallback fails as well, the next step in the ladder continues from where it stopped, from files, not from zero. The quota thresholds still apply to the fallback.

### 3. Failover ladders

Move left to right through the default ladder, skipping down pools and any
provider excluded by the hard rule on data. Use a different company's
model, or the same model through another client with independent capacity.
Hydrogen video/audio may use Neon under the media exception below.

Check the current workspace measurements described in Model notes. Resolve Mythos/Fable to the configured exact model and effort. Compare
that model on the needed task profiles, then use comparable
task times and live headroom as described above. The listed order and
**below** labels reflect the historical baseline. A refreshed, comparable
result may change the ranking among eligible lanes. Add a newly measured
model only if the project profile authorizes its runner, data scope, and
budget. Never treat an unmeasured comparison as equivalent.

| Lane that failed (profile it needs) | 1st fallback | 2nd fallback | 3rd fallback | If all fail |
|---|---|---|---|---|
| **Main loop** Opus `high` | Whole Claude pool down: gpt-6.2-astra `medium` in Codex. Use the knowledge-work profile to confirm equivalence. For a high-stakes document/PDF judgment, add a gemini-4-neon `high` review. | Codex also down: Antigravity **Orchestrator (Neon)** or **gemini-4-neon** `high`. See the handover below. | | Wait for reset |
| **Mythos/Fable advisor** `medium` | gemini-4-neon `high` (equal or better, slower) | gpt-6.2-astra `medium` with the same question, **below** on accuracy | | Decide without the second opinion and say so |
| **Opus delegate** `medium` | gpt-6.2-sol `high`, with a step-by-step brief | gemini-4-neon `medium` | gemini-4-hydrogen `high` | Wait for reset |
| **Opus** `high`, escalation | gpt-6.2-astra `medium` | gemini-4-neon `high` | | Wait for reset |
| **Sonnet** `high` | gpt-6.2-sol `high` | gemini-4-hydrogen `high` | | Wait for reset |
| **Haiku** `high` | gpt-6.1-terra `medium` (sample the first job on a new runner; if it fails, gpt-6.2-sol `high`) | gemini-4-hydrogen `medium` | | Queue |
| **gpt-6.2-sol** `xhigh` | gemini-4-neon `high` (equal or better, slower) | gemini-4-neon `medium` (**below** on code and reasoning) | Opus `high` (**below** on code and reasoning) | Wait for reset |
| **gpt-6.2-sol** `high`, default | gemini-4-neon `medium` | Opus `high` (**below** on reasoning) | gemini-4-hydrogen `high` (**below** on code and reasoning) | Wait for reset |
| **gpt-6.2-astra** `medium` | Mythos/Fable advisor if available | gemini-4-neon `high` (equal or better, slower) | Opus `high` (**below** on code/reasoning/accuracy; same-family if Opus main loop) | Skip the second opinion and say so |
| **gpt-6-luna** `high` (knowledge work) | gemini-4-hydrogen `low` | deepseek-flash (slower, first choice for very large publishable batches when budget permits) | Haiku `medium` (faster for small or restricted batches) | Queue |
| **gemini-4-hydrogen** `high`, PDFs, images, reading, search | gpt-6.2-astra `medium`, **below** on accuracy. Require sources and raise verification one step. | Sonnet `high` (Claude), **below** on accuracy (and borderline on knowledge), for bulk reading only | | Queue |
| **gemini-4-hydrogen**, video or audio | gemini-4-neon `high` (media only). Keep Hydrogen first for media when it has headroom. | | | Queue if a shared Gemini limit takes down both |
| **gemini-4-neon** `high`, reviewer | gpt-6.2-astra `medium` (**below** on accuracy, knowledge and reasoning). Raise verification one step. For GPT-authored work use Opus `high` (**below** on all profiles). Raise verification one step. | | | Queue independent review |
| **gemini-4-neon** `medium`, second eye | gpt-6.2-astra `medium` (accuracy comparison is unmeasured for Neon `medium`). Raise verification one step. | For GPT-authored work or Codex down: Opus `medium` (**below** on code/reasoning/knowledge) | | Skip the second eye and say so |
| **deepseek-flash** | gpt-6.2-sol `high` (light on Codex) | gemini-4-hydrogen `medium` | Sonnet `high` (Claude) | Queue |

**Limits attach to pools, not model names.** A Claude five-hour or weekly
limit takes down the main loop and every Claude delegate together; a Mythos/Fable model-specific limit can take down just the advisor. A Codex limit takes down Sol,
astra, terra and luna together. A shared Gemini limit takes down Hydrogen and Neon
together.

**When the whole Claude family is down:**

The operator talks to the main loop through the Claude app, and the app
stops answering when the Claude pool is down, so the main loop cannot hand
over at that moment. The handover is prepared **before** it is needed:

1. **At 85 % of the Claude five-hour window (stop mark 90 %) or 95 % of the weekly limit**,
   the main loop brings `orchestration-checkpoint.md` and the handover note
   up to date (goal, decisions, units with status, outputs, decisions still
   open), and commits, so a successor needs nothing from Claude.
2. If the pool goes down and the reset is within about 30 minutes, the
   operator waits. Rebuilding the stack on another family costs more.
3. Otherwise the operator opens Codex in the project folder with
   `codex -m gpt-6.2-astra -c model_reasoning_effort=medium` and invokes `astra-orchestration` with the current checkpoint.
   Follow the project handover rules for checkpointing, decisions that must wait, and
   delegation to Sol, Neon and Hydrogen. Send document/PDF-heavy judgments
   to gemini-4-neon `high` for review. If Codex is down too, the operator
   opens the project in Antigravity with **Orchestrator (Neon)** or
   **gemini-4-neon** `high` and invokes `neon-orchestration` with the current checkpoint.
4. When Claude returns, the operator opens a new Claude session; the main
   loop reads the checkpoint and reviews the handover period's work before it is
   treated as final. Hold the final synthesis for that return when the
   deliverable is not urgent, and mark it as pending.

### 4. Handoff rules

A fallback lane starts from files, never from another model's memory.

- **Checkpoint file.** `orchestration-checkpoint.md` in the working directory
  holds the goal, decisions made and why, the unit list with a status per
  unit (todo, running, done, verified), where each output lives, and open
  questions. Write it before any fan-out and update it when a unit changes
  state.
- **Units are idempotent.** Each unit writes its own output file. A unit that
  was running when the limit hit is rerun whole on the new lane.
- **Rewrite the brief for the new reader.** An Opus brief handed to Sol
  unchanged will underperform. Use the brief shape of the receiving lane.
- **Tag outputs with the model that produced them**, and sample each model's
  share separately before merging.
- **Raise verification one step** for work that fell to a lighter lane than
  the policy intended.
- **Do not fail over mid-edit.** Restore files to the last committed state
  before the new lane begins.

### 5. Provider state and recovery

Keep `provider-state.json` in the working directory so every agent routes
around a pool that is down instead of rediscovering it.

```json
{
  "claude":   {"status": "up",   "down_until": null, "limit": null},
  "claude-model-id": {"status": "up", "down_until": null, "limit": null},
  "codex":    {"status": "up",   "down_until": null, "limit": null},
  "gemini":   {"status": "up", "down_until": null, "limit": null},
  "deepseek": {"status": "up",   "down_until": null, "limit": null}
}
```

- Under this policy a model ID entry tracks only that advisor. The `claude` entry tracks the shared pool.
- Check it before every spawn.
- When `down_until` passes, send **one** small request as a probe. On
  success, mark the pool up and return new work to its normal lane. On
  failure, extend `down_until` and wait 15 minutes before probing again.
- Work already running on a fallback lane finishes there; only new units
  return to the primary lane.
- When the main loop returns, it reviews anything a lighter lane produced in
  its absence before that is treated as final.

## CLI lanes

**Codex (GPT).** GPT lanes run through `codex exec` with explicit model, effort, and sandbox settings. Execution lanes run on
`-m gpt-6.2-sol`, that skill's default; pass `-m gpt-6.2-astra` for second
opinions, `-m gpt-6.1-terra` for the cleanup pilot and `-m gpt-6-luna`
for large cleanup jobs. Sol defaults to `high`. Use `xhigh` for higher-requirement, reasoning-
or science-heavy sensitive work and escalation. Astra needs Codex CLI 0.153.0 or newer.

**Gemini.** Use `gemini-4-hydrogen` at high effort for media, wide reading and
search. The media exception permits gemini-4-neon
`high` to back up video/audio only. Gemini CLI headless runs use
`gemini -m <model> -p "<prompt>" --output-format json` with the subscription
account. Read the `response` field and pass the model explicitly. Use agy for
Neon review and second-eye jobs with the model and effort pinned.

**DeepSeek.** There is no first-party agent CLI. Use an OpenAI-compatible
client pointed at `https://api.deepseek.com`, or an Anthropic-compatible
harness pointed at `https://api.deepseek.com/anthropic`, with model
`deepseek-flash`. Ramp concurrency rather than opening at full width.

When assigning fleet lanes, stamp the model, effort and concurrency per lane
in the spec so the launch is mechanical and no routing decision happens at
spawn time. Confirm each recipe once against the installed CLI version before
a fleet depends on it.

## Model notes

The [bundled model measurements](../update-orchestration-skills/references/model-measurements.md) contain the benchmark scores, task profiles, averages, and observed or estimated task times. Read `.orchestration/model-measurements.md` in the current workspace first if it exists. The bundled archive is the historical basis for these defaults.

Run `/update-orchestration-skills` in Claude Code or Antigravity, or `$update-orchestration-skills` in Codex, to refresh the workspace data. Install the [refresh skill](../update-orchestration-skills/) alongside this preset. A refresh changes the measurement evidence available to routing; the project profile still governs authorization, pool access and model IDs. Use each model's exact measured variant and effort, and compare results only on matching task profiles and compatible source cohorts. Missing measurements remain unknown.

## Routing ledger

Append one line per delegation to `orchestration-ledger.md`: date, task type,
lane, effort, attempts, verification result, escalation if any. When the same
task type fails on a lane three times, or passes cleanly on a lighter lane
three times, propose a change to the routing table to the operator.
When qualifying Sol for standard code debugging, record three distinct standard
debugging jobs on gpt-6.2-sol, using `high` by default and `xhigh` only
under hard rule 4. Record verification and escalation for each job.
After the third job, use the ledger evidence to recommend a routing
decision to the operator.

## Exceptions

- If the operator explicitly names a model for a scoped task, honor it for that
  task only, then return to this policy.
- The operator can override any of this per session; absent that, this policy
  stands.
- When Mythos/Fable's allowance returns and the operator moves the main loop back to
  Mythos/Fable, switch to `fable-orchestration`.
