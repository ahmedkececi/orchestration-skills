---
name: neon-orchestration
description: >-
  Permanent delegation and quota-failover policy for a multi-model agent stack run on subscriptions (Gemini/Antigravity, ChatGPT/Codex, Claude) plus one metered API (DeepSeek), where the main loop runs in Antigravity on Orchestrator (Neon) or gemini-4-neon high. Coordinate delegation, review, usage limits and handoffs for this manager.
---

# Orchestration & delegation policy, Neon main loop (Antigravity / subscription stack)

Apply the routing defaults using the providers, runners, permissions, and spending limits authorized for this project. Start with the [project profile example](project-profile.example.md) and consult the [workflow templates](workflow-templates.md) for briefs and handoffs. Treat an unconfigured lane as unavailable and use the applicable fallback. Use the model and effort identifiers supported by the installed clients.

The main loop is a manager across both planning and execution phases: it thinks, decides,
writes briefs, directs and reviews, and never executes deliverables itself, however small.
Because the main loop shares the Antigravity/Gemini quota window with Hydrogen and Neon
delegates, execution is balanced across two independent pools — ChatGPT/Codex and Claude
(via claude -p): Claude Opus (medium by default, high on escalation, Google-code
cross-family review and peer advice) handles real PG/HTTP with local ports/network,
restricted data, localized UI/prompt quality, open-ended architectural debugging,
migrations and multi-file architectural refactors; gpt-6.2-sol (high by default, xhigh for
higher requirements, precision/math/science work and escalation) handles scoped clear-spec
coding, test suites and parallel execution alongside Opus; Sonnet high handles restricted
simple-medium edits, network/package installs and Codex overflow; cross-family review on
Neon/Google work goes to gpt-6.2-astra medium or Opus high; cross-family review on
GPT/Claude work goes to a fresh isolated gemini-4-neon high delegate;
media/PDFs/screenshots/wide reading/search go to gemini-4-hydrogen high (via Native Swarm
or agy); and bulk cleanup goes to gpt-6.1-terra medium (pilot), Haiku high, gpt-6-luna
high or deepseek-flash (publishable material only). Load at the start of every Antigravity
management session, before delegating via Codex, claude -p, Native Swarm, or headless
Antigravity, and whenever any pool approaches thresholds or returns a rate-limit or quota
error.

> **Operator updates (2026-11-19 & 2026-11-20).** From 2026-11-20, `gpt-6.2-sol`
> runs at **`high` by default** and **`xhigh`** for higher requirements,
> reasoning- or science-heavy sensitive work and escalation. `neon-orchestration`
> is a permanent main-loop policy for Antigravity (**Orchestrator (Neon)** or
> **`gemini-4-neon` at `high` effort**), used on equal footing with
> `.claude/skills/{mythos,fable,opus}-orchestration/` and
> `.agents/skills/astra-orchestration/`. The 2026-11-19 routing, review, Sol
> debugging trial, Terra cleanup pilot and failover ladders use
> `profil-ortalama-2026-11-19.md` (n ≥ 2: multi-source average, n = 1: AA only)
> and `aa-skorlar-2026-11-19.md` (for `gpt-6.2-sol` `xhigh` and task times).

> **Operator update (2026-11-15):** lane efforts, failover ladders and the
> "Approaching a limit" section are rebuilt from Artificial Analysis benchmark
> data, every test not just the headline index (scores and method:
> `aa-skorlar-2026-11-15.md`). Two operator rules govern fallback by default:
> **(1) a lane that is unavailable falls over only to a different company's
> model, or to the same model through a different client**; **(2) no quality
> loss, then the fastest**: among models at or above the lane's task profile,
> take the lowest time per task. Antigravity's built-in Claude credits are not a
> fallback (small credit, long jobs get cut). The Gemini media/reading lane runs
> **Gemini 4 Hydrogen at high effort**; `gemini-3.8-flash` is no longer its
> fallback (operator exception 2026-11-19: `gemini-4-neon` `high` backs up
> video/audio only).

A routing policy for a stack with **one strong main-loop model** and
**delegate lanes across four model families**. Gemini/Antigravity,
ChatGPT/Codex and Claude run on subscriptions; DeepSeek runs on a paid API.

On subscriptions, token price is not the constraint. **Allowance is.** Each
subscription is a pool that empties and refills on a schedule, and the stack
stops when the wrong pool runs dry.

Core law: **the main loop is the manager, not a worker.** It thinks, decides,
writes briefs, directs the lanes and reviews what comes back. It does not do
the work itself, however small. All execution goes to a lane that can carry
it, in the pool that can best afford it.

## The manager rule (operator, 2026-11-16)

The main loop runs the stack the way an executive runs a company. This is
the operator's standing instruction for every management session, so it also
settles any tool guidance that says to spawn agents only when the operator
asks: here the operator has asked, for every piece of work.

**Two-phase Orchestrator (Neon) clarification:** When running as Antigravity
`Orchestrator (Neon)`, planning turns (Plan Mode) and execution turns (after
`exit_plan_mode`) together are **the main loop (Manager)**. Execution turns
carry out **management actions only**: writing briefs into
workspace for briefs and artifacts, launching delegates via Codex, Native Swarm or the configured Gemini runner,
monitoring and reviewing reports/diffs, running read-only verification checks,
updating management records, and committing accepted work. Neither phase edits
product code, tests, content, data or product documentation directly, nor
patches review findings.

**The main loop does:**

- **Think.** Understand the request, weigh options, make architectural and
  design decisions and hard calls (respecting standing operator gates such as
  explicit approval before a production database write).
- **Direct.** Split the work into units, pick the lane, write the brief,
  launch and follow the delegate, decide what happens next.
- **Review.** Read the report, read the diff or a sample, run read-only
  checks (tests, type check, build, `git diff`, usage/quotas), then accept
  the work or send it back.
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
   be handed over (for example an approved write to a live system, or running
   local-port PG/HTTP/browser verification sweeps when sandboxed Codex cannot).
   A delegate still writes and fixes the scripts/migrations.
3. Answering the operator's question from what the main loop already knows
   or from a few targeted reads.

Before any tool call that writes a file or runs a command, ask: is this
thinking, directing, reviewing or record-keeping? If not, it is a brief.

## What changes with a Neon / Orchestrator main loop

1. **Shared Gemini / Antigravity pool — protect it first.** Neon as main loop
   draws directly from the **shared Antigravity/Gemini five-hour rolling window
   and weekly cap** alongside every `gemini-4-hydrogen` and `gemini-4-neon`
   worker. Check live allowance with `swarm{action:"models"}` (`quotas` shows
   `quota_remaining` and `quota_resets`). Keep all routine code/script volume
   in Codex (`gpt-6.2-sol`) or Claude (`Opus`/`Sonnet`), and never spend
   Gemini allowance on code execution that other pools can carry.
2. **Two-phase Plan / Execute loop (when using Orchestrator (Neon)).**
   Planning turns analyze the state, choose lanes and write the management plan
   before `exit_plan_mode`. Execution turns run the brief/delegate/verify/commit
   loop without improvising new architecture or editing product files; whenever
   an assumption breaks, two verification runs fail, or an unmade decision is
   needed, hand back with `enter_plan_mode`.
3. **Hybrid delegation: Native Swarm + Codex + Gemini CLI.** Antigravity
   does not have Claude Code's `Agent` tool. Instead:
   - **Native Swarm (`swarm`, `post_message`, `read_board`, `swarm_wait`)** is
     first-class for parallel read-only Gemini work: sharded visual/PNG
     inspections (`gemini-4-hydrogen-high`), multi-doc/PDF sweeps, and fresh
     isolated cross-family reviews of GPT/Claude work (`gemini-4-neon-high`).
     Policy override vs generic Swarm defaults: always pin the exact lane
     `model` in `swarm{action:"add"}` (do not inherit the coordinator model);
     keep `workspace:"inherit"` for read-only reviewers and separate paths or
     `workspace:"share"`/`"branch"` for parallel writers; attach `monitor`
     (no `model` argument) when `swarm_monitor` is active; kill finished
     workers to keep the board clean; and end with a plain `[done]` post
     without `@` mentions.
   - **Codex (`codex exec`)** carries all GPT lanes (`gpt-6.2-sol` `high`
     default / `xhigh` for higher requirements & escalation, `gpt-6.2-astra`
     `medium`, `gpt-6.1-terra` `medium`, `gpt-6-luna` `high`).
   - **The configured Gemini CLI** remains the headless option when a task
     needs CLI isolation, limited tool permissions, or a separate worktree.
   - **Claude lanes (`Opus` `medium`/`high`, `Sonnet` `high`, `Haiku` `high`):**
     Run directly as first-class delegates via headless Claude Code CLI
     (`env -u ANTHROPIC_API_KEY claude -p --model <opus|sonnet|haiku> --effort <medium|high> ... < /dev/null`)
     on the Claude subscription — completely independent of both Gemini and
     Codex pools! **Antigravity's built-in Claude models (`claude-opus-5-5-*`,
     `claude-sonnet-5-5-*`) are NOT a fallback lane** (tiny credit limit,
     long jobs cut mid-way; operator 2026-11-15).
4. **Cross-family review and second opinion invert around Google.**
   - **GPT- or Claude-authored work** → a fresh, isolated **`gemini-4-neon`
     `high`** delegate (Swarm worker or the configured Gemini runner, without the author's
     reasoning). That review is cross-family against GPT/Claude, and the fresh
     delegate's report stays separate from the main loop's own read/test check.
   - **Google-authored work (Hydrogen or Neon)** → **`gpt-6.2-astra`
     `medium`** (`codex exec -s read-only`), or **Opus `high`** if Codex is
     unavailable. Never send GPT-authored work to `gpt-6.2-astra` for
     independent cross-family review; if `gemini-4-neon` `high` is down and
     `Opus` `high` is unavailable, queue GPT-authored review rather than doing
     same-family GPT-on-GPT. For Google-authored work, if both Codex and
     Claude are unavailable, a fresh isolated Neon `high` check is
     **same-family** and must be labeled `same-family review` in the report.
   - **Peer question / second opinion on the Neon main loop's own calls** →
     **`gpt-6.2-astra` `medium`** (different company!). `Fable` `medium`
     (advisor) or `Opus` `high` are also valid cross-family options when
     available. Never count another Gemini model as a cross-family second
     opinion; a fresh isolated Neon `high` delegate is used only as a last
     resort when both Codex and Claude are unavailable, and must be labeled
     **same-family**.
   - **High-stakes document/PDF/visual judgments:** `gemini-4-neon` `high`
     already leads the stack on Accuracy (84) and Knowledge work (92). Have
     `gemini-4-hydrogen` `high` extract or inspect wide batches, and have the
     Neon main loop spot-check key artifacts directly via `read_file`.
5. **Pre-delegation gate.** Check live quota, split independent work,
   choose the eligible lane and effort, and prepare a bounded brief. Record
   the pool usage, unit, lane, and reason in the brief and checkpoint.

## The four pools

| Pool | Models in it | How it limits | Check with |
|---|---|---|---|
| **Gemini** subscription | Orchestrator (Neon) / `gemini-4-neon` (main loop and delegates), `gemini-4-hydrogen` | Antigravity Neon/Orchestrator has a rolling five-hour window and weekly cap shared with Hydrogen and agy/Swarm workers. Hydrogen also has plan-based CLI request limits where installed. | `swarm{action:"models"}` (`quotas`), Gemini runner usage logs, Antigravity usage, `/stats` if Gemini CLI is installed |
| **ChatGPT** subscription | `gpt-6.2-astra`, `gpt-6.2-sol`, `gpt-6.1-terra`, `gpt-6-luna` | A weekly allowance shared by Work and Codex; lower plans also have a five-hour window. Astra drains it several times faster than Sol; Luna barely touches it. | `/status` in Codex |
| **Claude** subscription | Mythos, Fable, Opus, Sonnet, Haiku | A five-hour window and a weekly limit, shared by all models and by chat, Claude Code and `claude -p`. Fable also has its own weekly share. | `provider-state.json`, operator `/usage` report |
| **DeepSeek** API (metered) | `deepseek-flash` | Prepaid balance or the configured gateway's request and token limits. | Provider balance or gateway quota reporting |

Consequences:

- **The main loop and every Gemini/Swarm delegate share one pool.** Large
  Hydrogen or Neon fan-outs eat the Neon main loop's own five-hour and weekly
  budget. Put code execution in Codex (`Sol`) and publishable bulk in
  DeepSeek (`deepseek-flash`) or Codex (`Terra`/`Luna`).
- **The pools are independent.** Spreading a big job across Codex, Gemini and
  DeepSeek up front beats draining one and failing over.
- **DeepSeek is the only lane with no subscription window.** It is the pressure
  valve for publishable bulk volume at zero/low window cost.

## Routing procedure

Choose the first matching execution lane. Apply hard rule 7 before routing
and apply the final high-stakes check separately.

1. **Is it thinking, a decision, a brief, a review judgment or the final
   synthesis?** Main loop (Orchestrator (Neon) / `gemini-4-neon` `high`).
   Nothing else stays there ("The manager rule").
2. **Is it small?** Delegate to `gpt-6.2-sol` `high` with a brief that names
   the file, change and check. Skip this shortcut when a specialized input,
   restricted-data rule, or local-port/network rule below applies. If Codex is
   full or down, follow the Sol failover ladder (`gemini-4-neon` `medium`, or
   `Opus` `high`, then `gemini-4-hydrogen` `high`).
3. **Is the input video or audio, or a pile of long PDFs or screenshots to
   turn into text or inspect visually?** `gemini-4-hydrogen` `high` (Native
   Swarm for parallel batches or the configured Gemini runner). For video/audio only,
   `gemini-4-neon` `high` is the approved backup (operator, 2026-11-19).
4. **Is it restricted data** (secrets, credentials, personal or client data)?
   Under hard rule 7, restricted data stays on Claude tiers unless the
   operator has explicitly cleared another provider. Never send restricted
   data to DeepSeek; strip secrets from every brief
   regardless of destination. If no cleared lane is currently available, hold
   and ask the operator.
5. **Is it mechanical work over many items?** For small and medium cleanup,
   sample the first `gpt-6.1-terra` `medium` job. Use Terra first for
   unrestricted batches once the sample passes. When Terra pilot is pending,
   after a failed pilot, for restricted data, or when Codex is down, use
   `Haiku` `high` (or the Haiku ladder `gemini-4-hydrogen` `medium`). For very
   large jobs use `gpt-6-luna` `high` or `deepseek-flash` (publishable material only).
6. **Is it wide reading that returns a conclusion** (a large codebase sweep,
   many documents, web research with sources)? `gemini-4-hydrogen` `high`,
   kept bounded with stop conditions and source paths/URLs.
7. **Is it execution with a clear spec?** Split cleanly between the two
   independent execution pools by work shape and headroom:
   - **Migrations, multi-file architectural refactors, local-port PG/HTTP
     pipelines, restricted data, localized UI/prompt work** → **`Opus` `medium`**
     (`claude -p --model opus --effort medium`; **`Opus` `high`** for higher
     requirements or escalation).
   - **Precision/math/SymPy scripts, test suites, fixed-scope code edits, and
     parallel implementation units alongside Opus** → **`gpt-6.2-sol` `high`**
     (`xhigh` for higher requirements, reasoning-/science-heavy sensitive work
     and escalation).
8. **Otherwise route by task.**
   - **`Opus` `medium` (`claude -p`)** handles real PG/HTTP requiring local
     ports or network access, restricted data, localized UI or prompt quality,
     and open-ended architectural debugging (escalating to **`Opus` `high`**).
   - **`Sonnet` `high` (`claude -p`)** handles restricted simple-medium edits,
     required network access or package installs, and Codex overflow/outages.
   - **`gpt-6.2-sol` `high`/`xhigh`** handles other simple-to-medium coding
     and the three-job standard code-debugging trial (Routing ledger).
9. **Is it a high-stakes call or a Neon/Google review?** Add a peer question
   to `gpt-6.2-astra` `medium` in parallel (`codex exec -s read-only`), or
   to `Fable` `medium` advisor when available. This is an addition to the lane
   above, not a replacement.

## The routing table

| Work | Goes to | How to call it | Brief style |
|---|---|---|---|
| Architecture, specs, hard judgment, briefs, direction, review, final synthesis (no execution) | **Main loop** (Orchestrator (Neon) / `gemini-4-neon` `high`) | itself (`Plan` + `Execute` phases together if Orchestrator) | n/a |
| Advice on the hardest calls, or cross-family second opinion on Neon's call | **gpt-6.2-astra** `medium` (primary cross-family peer; plus Fable `medium` advisor when available) | `codex exec -m gpt-6.2-astra -c model_reasoning_effort=medium -s read-only -o <file> "…" < /dev/null` | One peer question: problem, evidence, options, where unsure |
| Real PG/HTTP pipelines requiring network/ports, migrations, multi-file architectural refactors, restricted data, localized UI/prompt quality, open-ended architectural debugging | **Opus** `medium` (`claude -p`; escalate to **Opus** `high` for higher requirements or on two failures) — independent Claude pool, no local-port sandbox block | `env -u ANTHROPIC_API_KEY claude -p --model opus --effort <medium\|high> --permission-mode acceptEdits --no-session-persistence "…" < /dev/null` | Goal, context, constraints and acceptance criteria (fairly loose) |
| Execution with a clear spec: precision coding, test suites, math/SymPy/algorithm scripts, fixed-scope refactors (and parallel units beside Opus) | **gpt-6.2-sol** (`high` by default, `xhigh` for higher requirements, reasoning- or science-heavy sensitive work and escalation); balance large batches with **Opus** `medium` by headroom | `codex exec --skip-git-repo-check -m gpt-6.2-sol -c model_reasoning_effort=<high\|xhigh> -s workspace-write -o <file> "…" < /dev/null` | Detailed and step by step, nothing left implicit |
| Simple-medium: scoped edits, pattern clones, lookups, templated work, network/package installs | **gpt-6.2-sol** `high`, or **Sonnet** `high` (`claude -p`) for restricted data, required network/package installs, or Codex overflow/outages | `codex exec -m gpt-6.2-sol` (`high`) or `claude -p --model sonnet --effort high` | Named files, steps, output shape and boundaries |
| Video, audio, long PDFs, screenshot sets turned into structured text or visual checks | **gemini-4-hydrogen** `high` (video/audio backup only: **gemini-4-neon** `high`) | Native Swarm (`model:"gemini-4-hydrogen-high"`, `workspace:"inherit"`) or configured Gemini runner with Hydrogen at `high` effort | Bounded: what to extract/inspect, output schema or checklist, timestamp/page/filename on every item |
| Wide reading and search-grounded lookups that return a conclusion with sources | **gemini-4-hydrogen** `high` | Native Swarm or the configured Gemini runner | The question, the scope, a stop condition, URLs or file paths required |
| Very large bulk jobs, long-prompt bulk, bulk overflow from Haiku or luna | **deepseek-flash** (publishable material only) | OpenAI- or Anthropic-compatible client using the configured DeepSeek endpoint | Exact rules, output schema, shared material first, per-item part last |
| Independent check from a different model family | GPT or Claude wrote it → fresh **gemini-4-neon** `high`. Google wrote it → **gpt-6.2-astra** `medium`, or **Opus** `high` if Codex is down | Neon via Native Swarm (`model:"gemini-4-neon-high"`) or the configured runner with scoped review tools; Astra via `codex exec -m gpt-6.2-astra` `medium` `-s read-only` | The artifact, file list and acceptance criteria. Omit the author's reasoning |
| Second eye on a scoped question | **gemini-4-neon** `medium` (for GPT/Claude artifacts or neutral lookups) or **gpt-6.2-astra** `medium` (for Google artifacts) | Swarm (`model:"gemini-4-neon-medium"`) / the configured runner with Neon at `medium` or `codex exec -m gpt-6.2-astra` `medium` | Name the files, the question and the evidence to check |
| Bulk cleanup: normalizing, deduplicating, classifying, extracting | **terra (pilot) / Haiku** (small and medium) / **luna** (large). Sample the first Terra job; if clean, use Terra first for unrestricted small/medium jobs. Use **Haiku 5.5** `high` for restricted data or Codex outages (or `gemini-4-hydrogen` `medium` if unavailable) | `codex exec -m gpt-6.1-terra` at `medium`, or `codex exec -m gpt-6-luna` at `high` | Exact rules with examples, small batches and spot checks |

Integration (merging several delegates' outputs, resolving conflicts between
them, wiring pieces together) is execution, not synthesis: the main loop
decides how the pieces fit and a lane does the merging from a brief that
states those decisions.

**Default efforts per lane** (pin them on every call; effort moves a model
across whole tiers, e.g. Sonnet 5.5 scores 31 at `medium` and 42 at `high`):
main loop Orchestrator (Neon) / `gemini-4-neon` `high`, Fable advisor
`medium`, Opus delegates `medium`, Sonnet `high`, Haiku `high`,
`gpt-6.2-sol` `high` (default, 2026-11-20), Sol `xhigh` for higher
requirements, reasoning- or science-heavy sensitive work and escalation,
`gpt-6.1-terra` `medium` (cleanup pilot), `gpt-6.2-astra` `medium` (operator,
2026-11-17), `gpt-6-luna` `high`, `gemini-4-hydrogen` `high`, `gemini-4-neon`
`high` (independent review) or `medium` (second eye), `deepseek-flash` at its
highest reasoning setting. Measured profile of each in "Model notes".

Neon `high` scores 84 on accuracy and takes about 15 minutes per task
(2026-11-19). Reserve `deepseek-flash` checks for bulk or low-stakes work.

"DeepSeek v4.1" means one model today: V4.1 Flash, model ID `deepseek-flash`. There is no V4.1 Pro yet, and
`deepseek-v4-pro` is the older V4 Pro, which DeepSeek itself ranks below
V4.1 Flash. Do not route to it.

## The hard rules

1. **Always pass an explicit `model` and `effort`** on every `swarm{action:"add"}`,
   `invoke_subagent`, the configured Gemini runner, and CLI `codex exec -m ... -c
   model_reasoning_effort=...` call. Never omit `model` on execution workers
   (except `monitor` when using `swarm_monitor`), so workers do not silently
   drain the main loop's tier or drift in effort.
2. **The main-loop tier (`gemini-4-neon` `high` / Orchestrator) is not a
   routine execution tier.** Use `gemini-4-neon` as a delegate only for:
   (a) `high` independent cross-family review/re-review of GPT or Claude work;
   (b) `medium` scoped second-eye checks or ladder-specified fallback for
   `gpt-6.2-sol` (`high`/`xhigh`) / `Opus` (`medium`) only when Codex is down
   (with `high` for `Sol` `xhigh` fallback);
   (c) `high` video/audio media fallback (operator exception, 2026-11-19); or
   (d) `high` as a last-resort **same-family** second opinion only when both
   Codex (`Astra`) and Claude (`Fable`/`Opus`) are unavailable (labeled
   same-family). Never route routine implementation or code-writing here
   while Codex (`Sol`) is available.
3. **Route by difficulty, then pick the lightest lane that can carry it.**
   When unsure between two tiers, take the lighter one and verify the result;
   escalate one tier on failure rather than starting high.
4. **Balance execution across `Opus` `medium` and `gpt-6.2-sol` `high`.**
   Use **`Opus` `medium`** (`claude -p`, escalating to **`Opus` `high`**) for
   real PG/HTTP requiring local ports/network, migrations, multi-file
   architectural refactors, restricted data, localized UI/prompt quality, and
   open-ended architectural debugging. Use **`gpt-6.2-sol` `high`** (`xhigh`
   for higher requirements, reasoning-/science-heavy sensitive work and
   escalation) for precision/math/test-suite coding, fixed-scope edits, and
   parallel work alongside Opus (plus the three-job Sol debugging trial).
   Use **`Sonnet` `high`** for restricted simple-medium edits, required
   network/package installs, or Codex overflow/outages. Follow hard rule 7
   and the routing table for data and specialized lanes.
5. **The main loop keeps its own context lean.** Wide reading, file dumps and
   raw data go to a delegate (`gemini-4-hydrogen` `high`) that returns the
   conclusion; the main loop reads only what it must judge.
6. **A delegate's report is a claim.** Check the diff, run the tests or read a
   sample before reporting it as done.
7. **Data leaves only as far as it must.** Restricted data (secrets,
   credentials, personal or client data) stays on Claude tiers unless the
   operator has cleared another provider for it. The hosted DeepSeek API
   gets only material the operator would be comfortable publishing. Strip secrets from every brief
   regardless of destination.
8. **Two failed attempts at a tier, then escalate one tier, carrying the
   evidence**: what was tried, the failing output, the suspected cause. Never
   restart the higher tier from zero, and never loop a third time at the same
   tier with the same brief.
9. **Never buy your way past a limit.** Usage credits, plan upgrades and paid
   API keys for Claude, OpenAI or Google are operator decisions. Use the DeepSeek lane within the project profile's approved budget. Tell
   the operator before an unusually large job or a paid transition.
10. **One writer per file.** Parallel agents get disjoint file sets or separate
    worktrees / `workspace:"share"` / `"branch"`.
11. **The main loop does not execute.** It thinks, directs, reviews and keeps
    the management records ("The manager rule"), across both planning and
    execution turns. No task is small enough to do itself.
12. **Review findings go back.** A defect found in review returns to a lane
    with the evidence; the main loop never patches it.

## Parallel split (operator, 2026-11-17)

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

Before launching, state the split in `orchestration-checkpoint.md`: the
pieces, the lane and files of each, what joins them and who integrates. Ramp
width from a few agents, not the full fleet. In the report to the operator,
say how many agents ran and why the work was or was not split.

## Brief shape per tier

How tightly to write depends on who reads it.

- **gpt-6.2-sol (detailed, complete).** Write numbered steps, exact paths
  and commands, the acceptance check for each step, edge cases and scope, and
  explicitly forbid committing (`commit yapma`). Use **`high` by default** and
  **`xhigh`** for higher requirements, reasoning- or science-heavy sensitive
  work and escalation. Set an evidence target for standard code debugging and
  keep open architectural decisions with the main loop. Warn when local ports
  (`listen EPERM`) or browser caches are blocked in sandbox so Sol writes
  tests without assuming port access inside `codex exec`.
- **gpt-6.2-astra (peer question or cross-family review of Google code).**
  At **`medium` effort** (operator, 2026-11-17: astra lanes run at `medium`,
  not `high`; higher only when the operator asks). For a peer question, give
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
  item. For search, require the source URL beside each claim. At `high`,
  Hydrogen scores 79/69/82/81 in the updated profile table and takes 500 s.
  Its weak spot is Terminal-Bench-Science at `medium` and below (15 %): keep
  scientific or long agentic terminal work at `high` or above.
- **gemini-4-neon (reviewer / second eye / Sol fallback, 2026-11-19).**
  Use `high` for independent review and re-review of GPT/Claude work (and as
  `Sol xhigh` ladder fallback or last-resort same-family second opinion only
  when both Codex and Claude are unavailable), and `medium` for a scoped
  second eye or `Sol high` ladder fallback when Codex is unavailable. Give a
  bounded brief, an exact file list, commit/diff range, and acceptance
  criteria, omitting the author's reasoning on reviews. On `agy`, pass
  `--allow node` when Node checks are needed and allow ~15 minutes. Route
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
- **Opus delegate / Fable advisor / Sonnet.** Opus (`medium`): goal, context,
  constraints, acceptance criteria (fairly loose). Sonnet (`high`): explicit
  files, steps, boundaries, one task per agent. Fable (`medium`, advisor
  only): single peer question on the hardest calls.

Long briefs go in a file (`<work-dir>/<unit>/brief-*.md`); the
delegate prompt or Swarm message points at the file and carries the `ŞERİT:`
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

For a cross-family check (operator, 2026-11-19), send Claude- or GPT-authored
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

## Quota levers

- **Check before a big fan-out.** Check `swarm{action:"models"}` for
  Gemini/Antigravity remaining `%` and reset time, `provider-state.json` and
  `/status` for Codex, and the configured DeepSeek quota or balance. If a fleet would use
  more than half of what is left in one pool's current window, split it
  across pools now.
- **Keep volume out of the Gemini pool.** The Neon main loop lives here.
  Every Hydrogen/Neon Swarm worker spends from this pool's 5-hour/weekly
  window too. Put code execution in Codex (`Sol`), large bulk in DeepSeek or
  `Luna`/`Terra`, and keep Gemini focused on media, visual inspection, wide
  source sweeps, and required cross-family reviews.
- **Protect the main loop.** At 85 % of the five-hour window, move eligible
  delegated units off Gemini and keep `orchestration-checkpoint.md` current;
  at 85 % of the five-hour window (or 90 % of the weekly cap), stop starting
  new large Gemini delegates, finish running units, update
  `orchestration-checkpoint.md` and the handover note, and switch
  cleanly if needed.
- **Spend Astra last.** Astra drains the ChatGPT pool fastest; reserve it for
  hard peer questions, Google-authored cross-family audits, and Codex-led
  management sessions.
- **Effort before tier.** When a result is close but not right, raise effort
  one step on the same tier before moving up (e.g. Sol `high` → Sol `xhigh`).
  When a lane is routine, keep effort at default.
- **Start heavy fleets just after a window resets**, and ramp concurrency
  from a quarter of the planned width. Bursts trip per-minute limits.

## Approaching a limit: load balancing

The aim is to keep working as long as possible with no drop in quality, and
as fast as possible within that. Act **before** a pool runs dry, not after.

1. **Read live usage, not estimates.** Gemini/Antigravity:
   `swarm{action:"models"}` (`quotas`), Gemini runner usage logs, `/stats` if
   Gemini CLI is present; Codex: `/status`; DeepSeek: provider quota or balance; Claude:
   `provider-state.json` or operator `/usage`. Price-per-task figures do not
   measure subscription burn.
2. **Thresholds** (operator, 2026-11-15; weekly row for every pool set to 95 %,
   five-hour/daily rows to 85 % / 90 %, on 2026-11-20). Past the "move" mark,
   new delegated units go to the equivalent lane (the 1st fallback in the
   ladder below) instead of queuing on the pool; past the "stop" mark, no
   new large job starts there and running units finish. The main loop keeps
   working past both only as needed to finish checks and update the checkpoint.

   | Pool | Move delegated units | Stop large jobs, write the checkpoint |
   |---|---|---|
   | Gemini/Neon five-hour, Hydrogen daily | **85 %** | **90 %** |
   | Gemini/agy weekly | **95 %** | **95 %** |
   | Codex weekly | **95 %** | **95 %** |
   | Codex five-hour | **85 %** | **90 %** |
   | DeepSeek gateway daily, when applicable | **85 %** | **90 %** |
   | Claude five-hour window | **85 %** | **90 %** (keep the checkpoint current from 85 %) |
   | Claude weekly limit | **95 %** | **95 %** |

   The five-hour window resets within hours, so it is used later; the weekly
   limit costs days when it runs out, so delegated work leaves it earlier.
3. **Spread by headroom.** When a fan-out has several equivalent lanes,
   split units in proportion to each pool's remaining allowance, not evenly.
   Available free capacity takes bulk first.
4. **Equivalent means equal or better on the lane's task profile**, within 3
   points (scale in `aa-skorlar-2026-11-15.md`, scores in
   `profil-ortalama-2026-11-19.md`: average at n ≥ 2, AA only at n = 1).
   Among equivalents, take the lowest time per task. A model far above the
   lane is used only if it is also no slower and lighter on its pool than
   the next equivalent. **When two fallbacks are both equivalent, the pool
   with more headroom wins and speed only breaks a tie**; that is what keeps
   use even across pools.
5. **Gemini uses the standard pool thresholds (operator, 2026-11-20).**
   Hydrogen covers media, wide reading and search, and Neon covers the main
   loop (here), second-eye work, independent review and media fallback.
   Gemini follows the same **85 %** move / **90 %** stop (five-hour or daily)
   and **95 %** weekly thresholds as every other pool (the earlier 50 %
   overflow cutoff was removed). When Gemini nears 85 %, prioritize main-loop
   turns, media and mandatory reviews.
6. **Raise verification for weaker fallbacks.** For Hydrogen's
   accuracy-heavy reading, Astra `medium` is **below** on accuracy. For
   Neon `high` review, Astra `medium` is **below** on accuracy, knowledge
   and reasoning; Opus `high` (for GPT-authored work) is marked **below** on
   all profiles. For Neon `medium` second-eye work, accuracy is unmeasured
   (n = 0): the operator marks Astra `medium` **below** on accuracy there, and
   Opus `medium` is **below** on code, reasoning and knowledge. Raise
   verification one step, label the output and prefer waiting when reset is
   within about 30 minutes.
7. **agy's Claude models are not a fallback lane.** Their credit is small
   and a long job would be cut off mid-way (operator, 2026-11-15). agy keeps
   them for short single jobs only.

## When a limit is hit

### 1. Classify the error

| Class | What it looks like | Meaning |
|---|---|---|
| **A. Throttle** | HTTP 429 with a short retry hint; "slow down and try again after N seconds"; HTTP 503 or 529 overloaded; Claude Code's "Server is temporarily limiting requests (not your usage limit)"; DeepSeek 429 | Too fast right now. Capacity returns in seconds to minutes. |
| **B. Window exhausted** | "5-hour limit reached · resets [time]"; a Codex usage-limit message with a reset time; Gemini `RESOURCE_EXHAUSTED` or Antigravity `quota_remaining: 0%` with reset time | This window's allowance is gone. A reset time is known, hours away at most. |
| **C. Plan exhausted** | "You've hit your weekly limit"; "Fable limit reached"; weekly Antigravity cap depleted; DeepSeek balance depleted (HTTP 402) | Nothing returns without waiting days or paying. |
| **D. Not a limit** | HTTP 400, 401, 403; context length exceeded; model not found; content refusal | The request is wrong. No other provider will fix it. |
| **E. Lane's own failure** | The model stops on its own mistake, not on the work or a limit: a tool-permission denial it caused (e.g. agy: `ls` or a shell command typed into ReadFile, a read outside the workspace), an early exit with no output, a file-lock collision | The lane is unreliable for this unit right now. |

Read the message, not only the status code: Codex, Antigravity and Gemini
state reset times and scope. When the class is unclear, treat it as A once;
if the same error returns after the backoff, treat it as B.

### 2. Act on the class

- **A, throttle.** Wait for the server's retry hint, or 5, 20, then 60
  seconds with jitter. Halve that lane's concurrency before retrying; for
  DeepSeek, narrowing concurrency is the whole fix. Three attempts, then mark
  the lane down for 15 minutes and continue as B.
- **B, window exhausted.** Record the reset time in `provider-state.json`. If
  it is within about 20 minutes and other lanes have work, reorder and come
  back. Otherwise fail over along the ladder. Tell the operator once.
- **C, plan exhausted.** Mark the pool down in `provider-state.json` until
  its reset, fail over, and tell the operator, naming any paid options without
  taking them. For a depleted DeepSeek quota, report and wait or route
  along the ladder.
- **D, not a limit.** Do not fail over. Fix the request.
- **E, lane's own failure (operator, 2026-11-18).** Count these per lane in
  `orchestration-ledger.md`. A failure the main loop caused (a wrong path or
  conversation id in the brief, missing tool access, an incorrect workspace,
  overlapping files) does not count. After each lane-owned failure, add the
  trap to the brief and relaunch on the same lane. When a lane has made
  **more than three** (on the fourth), new units for that lane go to its 1st
  fallback in the ladder below (for Hydrogen doing implementation,
  `gpt-6.2-sol`), and a unit that was running moves too, provided partial
  artifacts are isolated (or only that unit's broken uncommitted edits are
  reverted cleanly first — see Handoff rules). If the fallback continues from
  verified output artifacts written to files, read those files rather than
  restarting completed sub-items from zero. The quota thresholds still apply
  to the fallback.

### 3. Failover ladders

Move left to right, skipping any pool marked down (`provider-state.json`) and
any provider that hard rule 7 excludes for the data involved. Use a different
company's model or the same model through another client (operator,
2026-11-15). The operator approved a same-company exception for Hydrogen
video/audio on 2026-11-19. Each step is equal or better on the lane's task
profile unless marked **below**. Within the equal options, use the fastest
first. Profile scores (code / reasoning / accuracy / knowledge work) come from
`profil-ortalama-2026-11-19.md` (n ≥ 2: multi-source average, n = 1: AA only)
and `aa-skorlar-2026-11-19.md` (`gpt-6.2-sol` `xhigh` AA n = 1). Task times
come from `aa-skorlar-2026-11-15.md` and `aa-skorlar-2026-11-19.md`.

| Lane that failed (profile it needs) | 1st fallback | 2nd fallback | 3rd fallback | If all fail |
|---|---|---|---|---|
| **Main loop** Orchestrator (Neon) / `gemini-4-neon` `high` (89/84/84/92; ~888 s) | **Mythos** `medium` (85/77/65/84, 447 s; **below** on all profiles: code 85 vs 89, reasoning 77 vs 84, accuracy 65 vs 84, knowledge 84 vs 92) or **Opus** `high` (81/72/55/85, 566 s; **below** on all profiles) in the Claude app under `mythos-orchestration` / `opus-orchestration` | **`gpt-6.2-astra`** `medium` in Codex (89/79/61/83, 264 s; **below** on reasoning 79 vs 84, accuracy 61 vs 84 and knowledge 83 vs 92) under `astra-orchestration` | | Wait for reset |
| **Fable advisor** `medium` (85/77/65/84; 447 s) | `gpt-6.2-astra` `medium` with the same question (89/79/61/83, 264 s; cross-family from Neon, **below** on accuracy 61 vs 65, both n=1) | `Opus` `high` (81/72/55/85, 566 s; **below** on code/reasoning/accuracy) | | Decide without the second opinion and say so |
| **Opus delegate** `medium` (code 76, reasoning 65, knowledge 78; 414 s) | `gpt-6.2-sol` `high` (82/76/56/82, 258 s*), with a step-by-step brief | `gemini-4-neon` `medium` (84/78/–/84, ~498 s) | `gemini-4-hydrogen` `high` (79/69/82/81, 500 s) | Wait for reset |
| **Opus** `high`, escalation (81/72/55/85; 566 s) | `gpt-6.2-astra` `medium` (89/79/61/83, 264 s) | `gemini-4-neon` `high` (89/84/84/92, ~888 s) | | Wait for reset |
| **Sonnet** `high` (code 73, knowledge 78; 405 s) | `gpt-6.2-sol` `high` (82/82, 258 s*) | `gemini-4-hydrogen` `high` (79/81, 500 s) | | Wait for reset |
| **Haiku** `high` (knowledge 53, accuracy 52; 392 s) | `gpt-6.1-terra` `medium` (56/62; 172 s; untested here, sample the first job; if it fails, `gpt-6.2-sol` `high` 82/56, 258 s*) | `gemini-4-hydrogen` `medium` (70/79; 227 s) | | Queue |
| **gpt-6.2-sol** `xhigh` (88/83/58/81; 306 s*) | `gemini-4-neon` `high` (89/84/84/92, ~888 s; equal or better, slower) | `gemini-4-neon` `medium` (84/78/–/84, ~498 s; **below** on code and reasoning) | `Opus` `high` (81/72/55/85, 566 s; **below** on code and reasoning) | Wait for reset |
| **gpt-6.2-sol** `high`, default (82/76/56/82; 258 s*) | `gemini-4-neon` `medium` (84/78/–/84, ~498 s) | `Opus` `high` (81/72/55/85, 566 s; **below** on reasoning) | `gemini-4-hydrogen` `high` (79/69/82/81, 500 s; **below** on code and reasoning) | Wait for reset |
| **gpt-6.2-astra** `medium` (89/79/61/83; 264 s) | Fable advisor `medium` (85/77/65/84, 447 s; code −4; cross-family) | `Opus` `high` (81/72/55/85, 566 s; **below** on code/reasoning/accuracy; cross-family) | Only when both Codex and Claude are unavailable: fresh isolated `gemini-4-neon` `high` (89/84/84/92, ~888 s; equal or better, slower; **same-family** when Neon is main loop — label explicitly) | Skip the second opinion and say so |
| **gpt-6-luna** `high` (knowledge 45; 348 s) | `gemini-4-hydrogen` `low` (44; 84 s) | `deepseek-flash` (71; 832 s; slower, first choice for very large publishable batches when budget permits) | `Haiku` `medium` (46; 242 s; faster for small or restricted batches) | Queue |
| **gemini-4-hydrogen** `high`, PDFs, images, reading, search (accuracy 82, knowledge 81; 500 s) | `gpt-6.2-astra` `medium` (61/83, 264 s), **below** on accuracy. Require sources and raise verification one step. | `Sonnet` `high` (Claude; 46/78, 405 s), **below** on accuracy (and borderline on knowledge), for bulk reading only | | Queue |
| **gemini-4-hydrogen**, video or audio (accuracy 82, knowledge 81; 500 s) | `gemini-4-neon` `high` (84/92, ~888 s; operator exception, 2026-11-19, media only). Keep Hydrogen first for comparable accuracy (82/84), about 1.8× faster and lighter on quota. | | | Queue if a shared Gemini limit takes down both |
| **gemini-4-neon** `high`, reviewer (89/84/84/92; ~888 s) | For Claude- or Google-authored work: `gpt-6.2-astra` `medium` (89/79/61/83, 264 s; **below** on accuracy 61 vs 84, knowledge 83 vs 92 and reasoning 79 vs 84; raise verification one step; never for GPT-authored work). For GPT-authored work: `Opus` `high` (81/72/55/85, 566 s; **below** on all profiles; raise verification one step). | | | Queue independent cross-family review |
| **gemini-4-neon** `medium`, second eye (84/78/–/84; ~498 s) | For Claude- or Google-authored work: `gpt-6.2-astra` `medium` (89/79/61/83, 264 s; operator marks **below** on accuracy, Neon `medium` accuracy unmeasured). Raise verification one step. | For GPT- or Google-authored work: `Opus` `medium` (76/65/53/78, 414 s; **below** on code/reasoning/knowledge) | | Skip the second eye and say so |
| **deepseek-flash** (knowledge 71, code 58; 832 s) | `gpt-6.2-sol` `high` (knowledge 82, code 82; 258 s*; light on Codex) | `gemini-4-hydrogen` `medium` (70/63; 227 s) | `Sonnet` `high` (Claude; 78/73; 405 s) | Queue |

**Limits attach to pools, not model names.** A shared Antigravity/Gemini
five-hour or weekly limit takes down the Neon main loop, Neon reviewers and
Hydrogen workers together. A Codex usage limit takes down Sol, Astra, Terra
and Luna together. A Claude limit takes down Mythos, Fable, Opus, Sonnet and
Haiku together (`Fable limit reached` alone leaves Opus/Sonnet/Haiku open).

**When the Gemini / Antigravity pool runs low or goes down:**

1. At **85 %** of the five-hour window, move eligible delegated units off
   Gemini and keep `orchestration-checkpoint.md` current; at **90 %** of the
   five-hour window or **95 %** of the weekly cap, stop starting new large
   Swarm/agy delegates, finish running units, update
   `orchestration-checkpoint.md` and the handover note, and switch
   cleanly before Antigravity refuses turns.
2. If the Gemini pool is exhausted and resets within ~30 minutes, wait rather
   than rebuilding the stack. Otherwise switch to **Claude
   (`mythos-orchestration` / `opus-orchestration`)** or **Codex
   (`astra-orchestration`, `codex -m gpt-6.2-astra -c model_reasoning_effort=medium`)**.

### 4. Handoff rules

A fallback lane starts from files, never from another model's memory.

- **Checkpoint file.** `orchestration-checkpoint.md` in the working directory
  holds the goal, decisions made and why, the unit list with a status per
  unit (todo, running, done, verified), where each output lives, and open
  questions. Write it before any fan-out and update it when a unit changes
  state.
- **Units are idempotent.** Each unit writes its own output file. A unit that
  was running when the limit hit is rerun whole on the new lane.
- **Rewrite the brief for the new reader.** An Astra or Opus brief handed to
  Sol unchanged will underperform. Use the brief shape of the receiving lane.
- **Tag outputs with the model that produced them**, and sample each model's
  share separately before merging.
- **Raise verification one step** for work that fell to a lighter lane than
  the policy intended.
- **Do not fail over mid-edit on unaccepted source edits.** If a writer
  stopped while editing code or project files, revert **only that interrupted
  unit's unaccepted edits** back to HEAD (never touch pre-existing dirty or
  user-owned files or other units' committed work)
  before the new lane begins. Idempotent output reports/artifacts inside the
  unit's work directory may be preserved as evidence.

### 5. Provider state and recovery

Keep `provider-state.json` in the working directory so every session routes
around a pool that is down instead of rediscovering it.

- Check it before every spawn.
- When `down_until` passes, send **one** small request as a probe. On
  success, mark the pool up and return new work to its normal lane. On
  failure, extend `down_until` and wait 15 minutes before probing again.
- Work already running on a fallback lane finishes there; only new units
  return to the primary lane.

## CLI lanes & Antigravity Swarm

**Native Swarm (Gemini workers in Antigravity).** Use `swarm{action:"title"}`
once per batch, `swarm{action:"add", name:..., model:"gemini-4-hydrogen-high"|"gemini-4-neon-high"|"gemini-4-neon-medium", workspace:"inherit"|"share"|"branch", brief:...}`
to assign work, `read_board` / `swarm_wait` to collect results, and `swarm{action:"kill"}`
to close finished workers before posting an `@`-free `[done]` closeout. Do not
spawn writers with `inherit` when modifying overlapping files.

**Claude Code CLI (`claude -p`).** Claude delegate lanes (`Opus` `medium` /
`high`, `Sonnet` `high`, `Haiku` `high`) run via `claude -p` on
the Claude subscription (`env -u ANTHROPIC_API_KEY`, check `claude auth
status`, never `--dangerously-skip-permissions`): `--model opus --effort
<medium|high> --permission-mode acceptEdits --no-session-persistence "…"
< /dev/null` (or `--tools Read,Glob,Grep --permission-mode dontAsk` for
read-only reviews).

**Codex (GPT).** GPT lanes run through `codex exec`:
`codex exec --skip-git-repo-check -m <model> -c model_reasoning_effort=<medium|high|xhigh> -s <read-only|workspace-write> -o <report_file> "<prompt>" < /dev/null`
Execution lanes run on `-m gpt-6.2-sol` (`high` default, `xhigh` for higher
requirements, reasoning-/science-heavy sensitive work and escalation); pass
`-m gpt-6.2-astra` (`medium`) for peer questions and Google-authored reviews,
`-m gpt-6.1-terra` (`medium`) for the cleanup pilot, and `-m gpt-6-luna`
(`high`) for large cleanup jobs. Astra needs Codex CLI 0.153.0 or newer. Use the project's approved sandbox for the task.

**Gemini via headless CLI.** Use the configured runner when a task needs
its own workspace, narrowly scoped tool permissions, or CLI logging. In
Antigravity, verify headless support with `agy --help` before using
`agy -p "<brief>" --model "<id>"`. Pin the model and effort for the lane.

**DeepSeek.** Use an OpenAI- or Anthropic-compatible client with the model
`deepseek-flash` and the endpoint authorized in your project profile. Set
`max_tokens >= 2048` and ramp concurrency gradually. Use publishable material
only.

When assigning fleet lanes, stamp the model, effort and concurrency per lane
in the spec so the launch is mechanical and no routing decision happens at
spawn time. Confirm each recipe once against the installed CLI version before
a fleet depends on it.

## Model notes

Model versions (operator, 2026-11-17): the Sol and Astra lanes run `gpt-6.2-sol`
and `gpt-6.2-astra`.

Last checked 2026-11-19 against Artificial Analysis (Intelligence Index
v5.0.1). See `aa-skorlar-2026-11-19.md` for the Neon and GPT-6.2 scores
(including `gpt-6.2-sol` `xhigh`), the three API confirmations and the
measurement limits. The original table and profile scale are in
`aa-skorlar-2026-11-15.md`. Re-verify when the check is more than a month old
or a model ID returns "not found".
The Opus-anchored averages give equal weight to AA and the independent
measurements in `profil-ortalama-2026-11-19.md`. Of 18 independent sources,
15 contributed and 3 were excluded. Where a lane has n ≥ 2 sources,
routing uses the average. Cells with n = 1 use AA alone, and n = 0 indicates
an unmeasured profile. The source records the range, secondary accuracy
sources and differences in effort mapping.

Profiles use the 2026-11-15 best-in-stack reference scores to scale each test.
**Code** (FrontierCode, Terminal-Bench, AutomationBench), **Reas.** (CritPt, HLE-Diamond,
Terminal-Bench-Science), **Acc.** (Omniscience accuracy and
non-hallucination), **Know.** (Briefcase, GDP.pdf, AutomationBench).
Seconds per task are end to end, thinking included. The asterisk marks a
modeled time from kingy.ai without direct AA verification.

| Lane (effort) | Company / client | Index | Code | Reas. | Acc. | Know. | s/task | Reads, note |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Fable 5.2 `medium` (advisor only) | Anthropic / Claude | 56.4 | 85 | 77 | 65 | 84 | 447 | own weekly share; peer fallback: Astra `medium` (cross-family from Neon, below on accuracy) |
| Opus 5.5 `medium` | Anthropic / Claude (agy: short jobs only) | 48.2 | 76 | 65 | 53 | 78 | 414 | text, images, PDF; 33 % non-hallucination |
| Opus 5.5 `high` | Anthropic / Claude (agy: short jobs only) | 51.8 | 81 | 72 | 55 | 85 | 566 | `xhigh` 57.4 index |
| Sonnet 5.5 `high` | Anthropic / Claude (agy: short jobs only) | 41.5 | 73 | 62 | 46 | 78 | 405 | `medium` drops to 31 |
| Haiku 5.5 `high` | Anthropic / Claude | 29.9 | 57 | 50 | 52 | 53 | 392 | not on agy |
| gpt-6.2-astra `high` | OpenAI / Codex | 60.1 | 95 | 92 | 60 | 83 | ~357 | text, images |
| gpt-6.2-astra `medium` | OpenAI / Codex | 57.0 | 89 | 79 | 61 | 83 | 264 | second opinion, Google-code review, Codex main loop |
| gpt-6.2-sol `xhigh` | OpenAI / Codex | 55.7 | 88 | 83 | 58 | 81 | 306* | text, images, higher requirements & escalation (AA n=1) |
| gpt-6.2-sol `high` | OpenAI / Codex | 54.9 | 82 | 76 | 56 | 82 | 258* | text, images, routine execution (default, 2026-11-20) |
| gpt-6.2-sol `medium` | OpenAI / Codex | 52.7 | 87 | 76 | 54 | 77 | 186 | below default (operator 2026-11-20: use `high` / `xhigh`) |
| gpt-6.1-terra `medium` | OpenAI / Codex | 38.2 | 73 | 60 | 62 | 56 | 172 | cleanup pilot: sample the first job |
| gpt-6-luna `high` | OpenAI / Codex | 21.4 | 30 | 22 | 41 | 45 | 348 | bulk only |
| gemini-4-hydrogen `high` | Google / agy & Swarm | 50.8 | 79 | 69 | 82 | 81 | 500 | 91 % non-hallucination; video/audio not yet verified on this stack, spot-check the first media job; media, visual checks, wide reading |
| gemini-4-hydrogen `medium` | Google / agy & Swarm | 41.2 | 63 | 55 | 79 | 70 | 227 | Terminal-Bench-Science 15 %: no scientific work |
| gemini-4-neon `high` | Google / Antigravity, agy & Swarm | 60.0 | 89 | 84 | 84 | 92 | ~888 | main loop (here), cross-family reviewer (GPT/Claude) and media fallback |
| gemini-4-neon `medium` | Google / agy & Swarm | 55.0 | 84 | 78 | – | 84 | ~498 | second eye, accuracy score unavailable |
| gemini-4-neon `xhigh` | Google / agy | 61.4 | 96 | 87 | 84 | 90 | ~1290 | |
| gemini-4-argon `medium` | Google / agy | 47.6 | 79 | 69 | 72 | 83 | 1802 | replaced by neon medium as second eye (2026-11-19) |
| gemini-3.8-flash `high` | Google / agy | 30.8 | 43 | 40 | 54 | 52 | 876 | **video, audio**, PDF; very verbose, historical benchmark |
| deepseek-flash (V4.1 Flash, highest effort; scored as "1017") | DeepSeek | 32.6 | 58 | 28 | 38 | 71 | 832 | text, images; metered bulk lane for publishable material |

## Routing ledger

Append one line per delegation to `orchestration-ledger.md`: date, task type,
lane, effort, attempts, verification result, escalation if any. When the same
task type fails on a lane three times, or passes cleanly on a lighter lane
three times, propose a change to the routing table to the operator.
For the 2026-11-19 code-debugging trial, record three distinct standard
debugging jobs on `gpt-6.2-sol`, using `high` by default and `xhigh` only
under hard rule 4. Record verification and escalation for each job.
After the third job, use the ledger evidence to recommend a routing
decision to the operator.

## Exceptions

- If the operator explicitly names a model for a scoped task, honor it for that
  task only, then return to this policy.
- The operator can override any of this per session; absent that, this policy
  stands.
- When moving the main loop to another client/model family, switch to its
  corresponding skill (`mythos-orchestration`, `fable-orchestration`,
  `opus-orchestration`, or `astra-orchestration`).
