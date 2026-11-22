---
name: neon-orchestration
description: >-
  Delegation and quota-failover policy for an Antigravity Orchestrator (Neon) / gemini-4-neon (high) manager across Gemini, Codex, Claude, and DeepSeek. Use at session start, before delegating or reviewing, or on quota/rate limits.
---

# Orchestration & delegation policy, Neon main loop (Antigravity / subscription stack)

Apply the routing defaults using the providers, runners, permissions, and spending limits authorized for this project. Start with the [project profile example](project-profile.example.md) and consult the [workflow templates](workflow-templates.md) for briefs and handoffs. Treat an unconfigured lane as unavailable and use the applicable fallback. Use the model and effort identifiers supported by the installed clients.

**First-run bootstrap (when `.orchestration/` is missing, or during initial setup):** Do not stall, ask where `.orchestration/` files are, or silently fall back past an uninstalled or signed-out CLI that the operator wants to use. Creating `.orchestration/` management records and running CLI readiness checks are part of the manager's setup duties. Run these four steps in order before delegating the first unit:
1. **Detect local CLIs & auth status:** Run read-only checks for `claude`, `codex`, and `agy` (plus `gemini` if used) — `command -v claude codex agy`, `CI=true claude auth status --text`, `codex login status`, and `agy --help` (or active Antigravity session) — and show the operator a compact status table (`CLI | Installed | Signed in`).
2. **Ask which pools to enable:** Ask the operator in one short message to confirm: (a) which CLIs/pools they want to use for this project (never force installing unused tools), (b) writable paths and any restricted paths, and (c) verification/test commands — or offer to start from the [project profile example](project-profile.example.md) defaults.
3. **Install & sign in to wanted CLIs before starting:** For any **wanted** CLI that is missing, show its official install command (see [CLI installation and login](references/cli-lanes-and-ledger.md#cli-installation-and-login)) and run an install **only after explicit operator approval**. For any **wanted** CLI that is installed but not signed in, pause and ask the operator to sign in interactively in their terminal (`claude` -> `/login`, `codex login`, or `agy auth login` / `agy`; never paste API keys or tokens into chat), then re-verify auth status once they confirm.
4. **Create `.orchestration/` & proceed:** Write `.orchestration/project-profile.md` authorizing only the verified, signed-in, approved lanes in its `<!-- orchestration-lanes:v1 -->` JSON block, initialize `.orchestration/provider-state.json` (`status: "up"`, `observed_at: null` until live usage is checked), suggest adding the ephemeral `.orchestration/` state files to `.gitignore`, and proceed with the operator's task (or report ready and wait if no task was given yet).

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
or agy); and bulk cleanup goes to gpt-6.1-terra medium (after sample qualification), Haiku high, gpt-6-luna
high or deepseek-flash (publishable material only). Load at the start of every Antigravity
management session, before delegating via Codex, claude -p, Native Swarm, or headless
Antigravity, and whenever any pool approaches thresholds or returns a rate-limit or quota
error.

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

## The manager rule

The main loop runs the stack the way an executive runs a company. This is
the operator's standing instruction to delegate each in-scope work item in
the management session, including small tasks. Treat it as the operator's
request to delegate wherever the host accepts standing authorization. Follow
any separate approval requirements set by the host or project.

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
     Run headless Claude Code CLI (`claude -p`) after the [subscription preflight](references/cli-lanes-and-ledger.md#claude-code-subscription-preflight).
     Use an authorized fallback when the subscription cannot be confirmed. **Antigravity's built-in Claude models (`claude-opus-5-5-*`,
     `claude-sonnet-5-5-*`) are NOT a fallback lane** (reserved for configured short jobs).
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
     **`gpt-6.2-astra` `medium`** (different company!). `Mythos/Fable` `medium`
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
| **Claude** subscription | Mythos/Fable, Opus, Sonnet, Haiku | A five-hour window and a weekly limit, shared by all models and by chat, Claude Code and `claude -p`. A Mythos/Fable model may have a separate allowance; check the selected model and plan. | `.orchestration/provider-state.json`, operator `/usage` report |
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
   `gemini-4-neon` `high` is the approved backup.
4. **Is it restricted data** (secrets, credentials, personal or client data)?
   Under hard rule 7, restricted data stays on Claude tiers unless the
   operator has explicitly cleared another provider. Never send restricted
   data to DeepSeek; strip secrets from every brief
   regardless of destination. If no cleared lane is currently available, hold
   and ask the operator.
5. **Is it mechanical work over many items?** For small and medium cleanup,
   optionally qualify `gpt-6.1-terra` `medium` on your runner by sampling a
   first job, then use Terra first for unrestricted batches once it passes.
   Before qualification, after a failed sample, for restricted data, or when
   Codex is down, use `Haiku` `high` (or the Haiku ladder `gemini-4-hydrogen`
   `medium`). For very large jobs use `gpt-6-luna` `high` or `deepseek-flash`
   (publishable material only).
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
     (and optional standard code-debugging qualification runs in the Routing
     ledger).
9. **Is it a high-stakes call or a Neon/Google review?** Add a peer question
   to `gpt-6.2-astra` `medium` in parallel (`codex exec -s read-only`), or
   to `Mythos/Fable` `medium` advisor when available. This is an addition to the lane
   above, not a replacement.

## The routing table

| Work | Goes to | How to call it | Brief style |
|---|---|---|---|
| Architecture, specs, hard judgment, briefs, direction, review, final synthesis (no execution) | **Main loop** (Orchestrator (Neon) / `gemini-4-neon` `high`) | itself (`Plan` + `Execute` phases together if Orchestrator) | n/a |
| Advice on the hardest calls, or cross-family second opinion on Neon's call | **gpt-6.2-astra** `medium` (primary cross-family peer; plus Mythos/Fable `medium` advisor when available) | `codex exec -m gpt-6.2-astra -c model_reasoning_effort=medium -s read-only -o <file> "…" < /dev/null` | One peer question: problem, evidence, options, where unsure |
| Real PG/HTTP pipelines requiring network/ports, migrations, multi-file architectural refactors, restricted data, localized UI/prompt quality, open-ended architectural debugging | **Opus** `medium` (`claude -p`; escalate to **Opus** `high` for higher requirements or on two failures) — independent Claude pool, no local-port sandbox block | `CI=true claude -p --model opus --effort <medium\|high> --permission-mode acceptEdits --no-session-persistence "…" < /dev/null` | Goal, context, constraints and acceptance criteria (fairly loose) |
| Execution with a clear spec: precision coding, test suites, math/SymPy/algorithm scripts, fixed-scope refactors (and parallel units beside Opus) | **gpt-6.2-sol** (`high` by default, `xhigh` for higher requirements, reasoning- or science-heavy sensitive work and escalation); balance large batches with **Opus** `medium` by headroom | `codex exec --skip-git-repo-check -m gpt-6.2-sol -c model_reasoning_effort=<high\|xhigh> -s workspace-write -o <file> "…" < /dev/null` | Detailed and step by step, nothing left implicit |
| Simple-medium: scoped edits, pattern clones, lookups, templated work, network/package installs | **gpt-6.2-sol** `high`, or **Sonnet** `high` (`claude -p`) for restricted data, required network/package installs, or Codex overflow/outages | `codex exec -m gpt-6.2-sol` (`high`) or `claude -p --model sonnet --effort high` | Named files, steps, output shape and boundaries |
| Video, audio, long PDFs, screenshot sets turned into structured text or visual checks | **gemini-4-hydrogen** `high` (video/audio backup only: **gemini-4-neon** `high`) | Native Swarm (`model:"gemini-4-hydrogen-high"`, `workspace:"inherit"`) or configured Gemini runner with Hydrogen at `high` effort | Bounded: what to extract/inspect, output schema or checklist, timestamp/page/filename on every item |
| Wide reading and search-grounded lookups that return a conclusion with sources | **gemini-4-hydrogen** `high` | Native Swarm or the configured Gemini runner | The question, the scope, a stop condition, URLs or file paths required |
| Very large bulk jobs, long-prompt bulk, bulk overflow from Haiku or luna | **deepseek-flash** (publishable material only) | OpenAI- or Anthropic-compatible client using the configured DeepSeek endpoint | Exact rules, output schema, shared material first, per-item part last |
| Independent check from a different model family | GPT or Claude wrote it → fresh **gemini-4-neon** `high`. Google wrote it → **gpt-6.2-astra** `medium`, or **Opus** `high` if Codex is down | Neon via Native Swarm (`model:"gemini-4-neon-high"`) or the configured runner with scoped review tools; Astra via `codex exec -m gpt-6.2-astra` `medium` `-s read-only` | The artifact, file list and acceptance criteria. Omit the author's reasoning |
| Second eye on a scoped question | **gemini-4-neon** `medium` (for GPT/Claude artifacts or neutral lookups) or **gpt-6.2-astra** `medium` (for Google artifacts) | Swarm (`model:"gemini-4-neon-medium"`) / the configured runner with Neon at `medium` or `codex exec -m gpt-6.2-astra` `medium` | Name the files, the question and the evidence to check |
| Bulk cleanup: normalizing, deduplicating, classifying, extracting | **terra (qualified sample) / Haiku** (small and medium) / **luna** (large). Sample the first Terra job on a new runner; if clean, use Terra first for unrestricted small/medium jobs. Use **Haiku** `high` (`claude-haiku-5-5`) before qualification, for restricted data, or during Codex outages (or `gemini-4-hydrogen` `medium` if unavailable) | `codex exec -m gpt-6.1-terra` at `medium`, `claude -p --model haiku --effort high`, or `codex exec -m gpt-6-luna` at `high` | Exact rules with examples, small batches and spot checks |

Integration (merging several delegates' outputs, resolving conflicts between
them, wiring pieces together) is execution, not synthesis: the main loop
decides how the pieces fit and a lane does the merging from a brief that
states those decisions.

**Default efforts per lane** (pin them on every call; effort can change relative performance):
main loop Orchestrator (Neon) / `gemini-4-neon` `high`, Mythos/Fable advisor
`medium`, Opus delegates `medium`, Sonnet `high`, Haiku `high`,
`gpt-6.2-sol` `high`, Sol `xhigh` for higher
requirements, reasoning- or science-heavy sensitive work and escalation,
`gpt-6.1-terra` `medium` (cleanup batches), `gpt-6.2-astra` `medium`, `gpt-6-luna` `high`, `gemini-4-hydrogen` `high`, `gemini-4-neon`
`high` (independent review) or `medium` (second eye), `deepseek-flash` at its
highest reasoning setting. Measured profile of each in "Model notes".

Reserve `deepseek-flash` checks for bulk or low-stakes work.

"DeepSeek v4.1" means one model today: V4.1 Flash, API alias `deepseek-flash`
(canonical catalog ID `deepseek-v4.1-flash-1017`). There is no V4.1 Pro yet, and
`deepseek-v4-pro` (`deepseek-v4-pro-0813`) is the older V4 Pro, which DeepSeek
itself ranks below V4.1 Flash. Do not route to it.

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
   (c) `high` video/audio media fallback; or
   (d) `high` as a last-resort **same-family** second opinion only when both
   Codex (`Astra`) and Claude (`Mythos/Fable` or `Opus`) are unavailable (labeled
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
   parallel work alongside Opus (plus optional standard-debugging qualification
   runs).
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
   API keys for Claude, OpenAI or Google are operator decisions. Follow the
   [subscription preflight](references/cli-lanes-and-ledger.md#claude-code-subscription-preflight) before launching a Claude subscription lane.
   Use the DeepSeek lane within the project profile's approved budget. Tell
   the operator before an unusually large job or a paid transition.
10. **One writer per file.** Parallel agents get disjoint file sets or separate
    worktrees / `workspace:"share"` / `"branch"`.
11. **The main loop does not execute.** It thinks, directs, reviews and keeps
    the management records ("The manager rule"), across both planning and
    execution turns. No task is small enough to do itself.
12. **Review findings go back (with a circuit breaker).** Every `BLOCKER`
    finding returns to a lane with the evidence (`NIT` notes never trigger
    rework alone); the main loop never patches it. After 2 failed review rounds
    on a unit, escalate one tier or stop and escalate to the operator.
13. **External Action Gate.** Workers must never perform git-irreversible or
    external side effects (`git push`, package publish, external API mutations,
    live DB migrations, or destructive deletes outside writable paths); only
    the coordinator executes them with explicit operator approval.

## Reference files (load on demand)

Load the matching reference file before acting in any of these situations — do not improvise from memory:

| Reference file | Load when | Mandatory reminder |
|---|---|---|
| [references/delegation-and-verification.md](references/delegation-and-verification.md) | Splitting work in parallel, shaping a delegate brief, or checking results on the verification ladder | Every brief on every lane must end with the 4-line return contract (`STATUS`, `RESULT`, `EVIDENCE`, `NOT DONE`); enforce `BLOCKER`/`NIT` review classification (max 2 rounds), high-stakes tie-breaker, and the Test Integrity Invariant. |
| [references/quota-and-failover.md](references/quota-and-failover.md) | Checking pool headroom, approaching thresholds, handling rate/quota/timeout errors, failing over, recovering from compaction, or writing a checkpoint/handoff | Move delegated units at **85 %** weekly / **90 %** five-hour; stop new large jobs at **90 %** weekly / **95 %** five-hour; only the coordinator writes `.orchestration/*`; after compaction or resume, re-read `orchestration-checkpoint.md`, `provider-state.json`, and `git status --short` before spawning delegates. |
| [references/cli-lanes-and-ledger.md](references/cli-lanes-and-ledger.md) | Launching Native Swarm, `claude -p`, `codex exec`, headless Gemini, or DeepSeek; resolving lanes deterministically; reading measurements; or logging to the routing ledger | Pin explicit `model` and `effort` on every call (non-interactive `< /dev/null`, `CI=true`), use `resolve_lanes.py` or `.orchestration/model-measurements.md` before the bundled archive, and log `scope_drift` / `first_pass_ok` to `.orchestration/orchestration-ledger.md`. |

## Exceptions

- If the operator explicitly names a model for a scoped task, honor it for that
  task only, then return to this policy.
- The operator can override any of this per session; absent that, this policy
  stands.
- When moving the main loop to another client/model family, switch to its
  corresponding skill (`fable-orchestration`, `opus-orchestration`,
  `astra-orchestration`, or `sol-orchestration`).
