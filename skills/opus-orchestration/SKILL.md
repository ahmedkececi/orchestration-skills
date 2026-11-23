---
name: opus-orchestration
description: >-
  Delegation and quota-failover policy for a Claude Opus 5.5 (high/xhigh) manager across Claude, Codex, Gemini, and DeepSeek. Use at session start, before delegating or running commands, or on quota/rate limits.
---

# Orchestration & delegation policy, Opus main loop (subscription stack)

Apply the routing defaults using the providers, runners, permissions, and spending limits authorized for this project. Start with the [project profile example](project-profile.example.md) and consult the [workflow templates](workflow-templates.md) for briefs and handoffs. Treat an unconfigured lane as unavailable and use the applicable fallback. Use the model and effort identifiers supported by the installed clients.

**First-run bootstrap (when `.orchestration/` is missing, or during initial setup):** Do not stall, ask where `.orchestration/` files are, or silently fall back past an uninstalled or signed-out CLI that the operator wants to use. Creating `.orchestration/` management records and running CLI readiness checks are part of the manager's setup duties. Run these four steps in order before delegating the first unit:
1. **Detect local CLIs, auth & available model IDs:** Run read-only checks for `claude`, `codex`, and `agy` (plus `gemini` if used) — `command -v claude codex agy`, `CI=true claude auth status --text`, `codex login status`, and `agy --help` (or active Antigravity session) — note the live model IDs actually supported by each installed CLI/account, and show the operator a compact status table (`CLI | Installed | Signed in`).
2. **Ask which pools to enable:** Ask the operator in one short message to confirm: (a) which CLIs/pools they want to use for this project (never force installing unused tools), (b) writable paths and any restricted paths, and (c) verification/test commands — or offer to start from the [project profile example](project-profile.example.md) defaults.
3. **Install & sign in to wanted CLIs before starting:** For any **wanted** CLI that is missing, show its official install command (see [CLI installation and login](references/cli-lanes-and-ledger.md#cli-installation-and-login)) and run an install **only after explicit operator approval**. For any **wanted** CLI that is installed but not signed in, pause and ask the operator to sign in interactively in their terminal (`claude` -> `/login`, `codex login`, or `agy auth login` / `agy`; never paste API keys or tokens into chat), then re-verify auth status once they confirm.
4. **Create `.orchestration/` & proceed:** Write `.orchestration/project-profile.md` authorizing only the verified, signed-in, approved lanes in its `<!-- orchestration-lanes:v1 -->` JSON block — mapping reference model names from `project-profile.example.md` to the exact live model IDs actually supported by the operator's installed CLIs/accounts so no lane fails with "model not found" — initialize `.orchestration/provider-state.json` (`status: "up"`, `observed_at: null` until live usage is checked), suggest adding `.orchestration/provider-state.json` to `.gitignore`, and proceed with the operator's task (or report ready and wait if no task was given yet).

The main loop is a manager: it thinks, decides, writes briefs, directs and reviews, and
never does the work itself, however small; Mythos/Fable, when the operator has allowance for it,
is consulted only as an advisor on the hardest calls. Work is routed by input type, data
sensitivity, difficulty and remaining quota. gpt-6.2-sol at high is the primary execution
lane (xhigh for higher requirements and escalation) for simple to medium work. Sonnet high
covers restricted data, network or package installs and Codex outages. Opus delegates at
medium cover real PG/HTTP, restricted data, localized UI or prompts and open-ended
architectural debugging. gpt-6.2-astra gives second opinions; gemini-4-hydrogen takes
video, audio and large-document intake, search-grounded lookups and wide reading;
deepseek-flash takes large bulk jobs and low-stakes checks; gpt-6.1-terra medium (after sample qualification),
Haiku high or gpt-6-luna take bulk cleanup. Load at the start of every management session
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
| **ChatGPT** subscription | gpt-6.2-astra, gpt-6.2-sol, gpt-6.1-terra, gpt-6-luna | A weekly allowance shared by Work and Codex; lower plans also have a five-hour window. Astra drains it several times faster than Sol; Luna barely touches it. | `/status` in Codex |
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
   optionally qualify `gpt-6.1-terra` `medium` on your runner by sampling a
   first job, then use Terra first for unrestricted batches once it passes.
   Haiku `high` covers batches before qualification, after a failed sample, for
   restricted data, or when Codex is down. For very large jobs use `gpt-6-luna`
   `high` or `deepseek-flash` (publishable material only).
6. **Is it wide reading that returns a conclusion** (a large codebase sweep,
   many documents, web research with sources)? `gemini-4-hydrogen`, which
   keeps that volume out of the Claude pool.
7. **Is it execution with a clear spec?** Send a step-by-step brief to
   gpt-6.2-sol `high`. Use `xhigh` for higher-requirement, reasoning- or science-heavy sensitive
   work and escalation. Apply the network and data exceptions in steps 2
   and 4 and the Opus cases in step 8.
8. **Otherwise route by task.** Use Opus `medium` only for real PG/HTTP
   requiring local ports or network access, restricted data, localized
   UI or prompt quality, and open-ended architectural debugging. Optionally
   qualify `gpt-6.2-sol` on standard code-debugging jobs (see Routing ledger).
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
| Real PG/HTTP requiring local ports or network access, restricted data that needs Opus, localized UI or prompt quality, open-ended architectural debugging | **Opus** sub-agent, `medium`. Optionally qualify **gpt-6.2-sol** on standard code-debugging jobs | `model: 'opus'` (`claude-opus-5-5`), effort `medium`. Use the Sol command above when qualifying Sol | Goal, context, constraints and acceptance criteria. Use a step-by-step brief for Sol |
| Simple-medium: scoped edits, pattern clones, lookups, templated work, straightforward reading and summarizing | **gpt-6.2-sol** `high`. **Sonnet** `high` only for restricted data, required network access or package installs, or when Codex is full or down | `codex exec -m gpt-6.2-sol`, effort `high`, or `model: 'sonnet'` (`claude-sonnet-5-5`), effort `high` | Named files, steps, output shape and boundaries |
| Second opinion, out-of-the-box thinking, an angle the main loop may be missing                                              | **gpt-6.2-astra**                                                                                                 | `codex exec -m gpt-6.2-astra`, effort `medium`                                        | The open question plus the evidence, as to a peer                        |
| Video, audio, long PDFs, screenshot sets turned into structured text                                                        | **gemini-4-hydrogen**                                                                                           | configured Gemini runner (e.g. `gemini -m gemini-4-hydrogen -p` or headless Antigravity) at `high` effort | Bounded: what to extract, output schema, timestamp or page on every item |
| Wide reading and search-grounded lookups that return a conclusion with sources                                              | **gemini-4-hydrogen**                                                                                           | same (the configured Gemini runner)                                                 | The question, the scope, a stop condition, sources required              |
| Very large bulk jobs, long-prompt bulk, bulk overflow from Haiku or luna                                                    | **deepseek-flash**                                                                                              | OpenAI- or Anthropic-compatible client                                              | Exact rules, output schema, shared material first, per-item part last    |
| Independent check from a different model family | Claude or GPT wrote it → **gemini-4-neon** `high`. Google wrote it → **gpt-6.2-astra** `medium`, or **Opus** `high` if Codex is down | Neon via the configured Gemini runner (`high`), Astra via `codex exec -m gpt-6.2-astra` at `medium`, Opus via `model: 'opus'` at `high`. See the Verification ladder | The artifact, file list and acceptance criteria. Omit the author's reasoning |
| Second eye on a scoped question | **gemini-4-neon** `medium` | configured Gemini runner with Neon at `medium` (e.g. `--model gemini-4-neon-medium`) | Name the files, the question and the evidence to check. |
| Bulk cleanup: normalizing, deduplicating, classifying, extracting | **terra (qualified sample) / Haiku** (small and medium). Sample the first Terra job on a new runner; if clean, use Terra first for unrestricted small and medium jobs. Use **Haiku** `high` (`claude-haiku-5-5`) before qualification, for restricted data, or when Codex is down. Use **gpt-6-luna** `high` for large jobs | `codex exec -m gpt-6.1-terra` at `medium`, `model: 'haiku'` at `high`, or `codex exec -m gpt-6-luna` at `high` | Exact rules with examples, small batches and spot checks |

Integration (merging several delegates' outputs, resolving conflicts between
them, wiring pieces together) is execution, not synthesis: the main loop
decides how the pieces fit and a lane does the merging from a brief that
states those decisions.

**Default efforts per lane** (pin them on every call; effort can change relative performance):
main loop Opus `high` (`xhigh` for long-lived calls), Opus delegates
`medium`, Sonnet `high`, Haiku `high`, gpt-6.2-sol `high` (default), Sol `xhigh` for higher-requirement, reasoning- or
science-heavy sensitive work and escalation, gpt-6.1-terra `medium`
(cleanup sample), gpt-6.2-astra `medium`, gpt-6-luna `high`, gemini-4-hydrogen
`high`, gemini-4-neon `high` (independent review) or `medium` (second eye),
deepseek-flash at its highest reasoning
setting. Measured profile of each in "Model notes".

Reserve deepseek-flash checks for bulk or low-stakes work.

"DeepSeek v4.1" means one model today: V4.1 Flash, API alias `deepseek-flash`
(canonical catalog ID `deepseek-v4.1-flash-1017`). There is no V4.1 Pro yet,
and `deepseek-v4-pro` (`deepseek-v4-pro-0813`) is the older V4 Pro, which
DeepSeek itself ranks below V4.1 Flash. Do not route to it.

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
   architectural debugging. Optionally qualify Sol on standard code-debugging
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
12. **Review findings go back (max 2 rounds).** Every `BLOCKER` defect found
    in review returns to a lane with the evidence (the main loop never patches
    it); `NIT` items do not trigger rework. After 2 failed review rounds,
    escalate one tier or escalate to the operator.
13. **External Action Gate.** Workers must never run git-irreversible external
    side effects (`git push`, package publish, external API mutations, live DB
    migrations, or destructive deletes outside writable paths); only the
    coordinator executes them with explicit operator approval.

## Reference files (load on demand)

Read the relevant reference file in full before acting when any trigger below applies:

| Reference file | Mandatory trigger |
|---|---|
| [references/delegation-and-verification.md](references/delegation-and-verification.md) | Read before writing a worker brief, splitting parallel units, or running cross-family verification (`BLOCKER`/`NIT`, review circuit breaker, test integrity). |
| [references/quota-and-failover.md](references/quota-and-failover.md) | Read when checking pre-dispatch/post-unit quota, nearing unified thresholds (**90% move / 95% stop** for both five-hour and weekly windows) or `projected-overflow` (`--unit-size`), calibrating burn (`--record-burn`), handling rate/quota limits or timeouts/hangs, failing mid-edit, writing a handoff checkpoint, or recovering after context compaction / session resume. |
| [references/cli-lanes-and-ledger.md](references/cli-lanes-and-ledger.md) | Read before invoking external runner CLIs (`codex exec`, configured Gemini runner, DeepSeek), running `resolve_lanes.py` or reading benchmark snapshots, or recording `.orchestration/orchestration-ledger.md` entries. |

**Pre-dispatch & post-unit quota gate:** Read live pool usage right before dispatching each unit and right after it finishes (5-minute TTL is only the upper bound for idle readings); refresh the Codex reading first with `read_quota.py --write`. Classify unit size (`xs|s|m|l|xl`) and run `resolve_lanes.py --unit-size <size>` — if a lane hits `projected-overflow` (`projected >= 95%` stop on either five-hour or weekly window), **do not dispatch** to it; route to a healthy fallback or split into smaller units. A recommendation flagged `deprioritized` or `projected-deprioritized` (`dispatch_ok: false`) is not dispatchable either: take the next ladder step (below-tier, verification one step higher) or wait for the reset. After completion, record actual burn with `resolve_lanes.py --record-burn` into `.orchestration/provider-state.json` (`_calibration` EWMA; skips EWMA on window resets).

Every worker brief on every lane must end with the mandatory 4-line return contract (`STATUS` / `RESULT` / `EVIDENCE` / `NOT DONE`).
A report with no `EVIDENCE` is treated as `partial`; see [references/delegation-and-verification.md](references/delegation-and-verification.md) for the exact format and per-tier brief shapes.

## Exceptions

- If the operator explicitly names a model for a scoped task, honor it for that
  task only, then return to this policy.
- The operator can override any of this per session; absent that, this policy
  stands.
- When moving the main loop to another model or client family (for example when
  Mythos/Fable's allowance returns or on a Claude pool handover), switch to its
  corresponding skill (`fable-orchestration`, `astra-orchestration`,
  `sol-orchestration`, or `neon-orchestration`).
