---
name: sol-orchestration
description: >-
  Delegation and quota-failover policy for a Codex gpt-6.2-sol (xhigh) manager (~2.5x lighter on Codex quota than Astra) across Codex, Claude, Gemini, and DeepSeek. Use at session start, before delegating, or on quota/rate limits.
---

# Orchestration & delegation policy, Sol xhigh main loop (ChatGPT / Codex subscription stack)

Apply the routing defaults using the providers, runners, permissions, and spending limits authorized for this project. Start with the [project profile example](project-profile.example.md) and consult the [workflow templates](workflow-templates.md) for briefs and handoffs. Treat an unconfigured lane as unavailable and use the applicable fallback. Use the model and effort identifiers supported by the installed clients.

**First-run bootstrap (when `.orchestration/` is missing):** If `.orchestration/project-profile.md` or `.orchestration/provider-state.json` does not exist yet in the workspace, do not stall or ask where the files are. Creating `.orchestration/` management records is part of the manager's record-keeping duties. Briefly inspect the workspace and available local runner CLIs, then ask the operator in one short message to confirm: (1) authorized model pools/runners, (2) writable paths and any restricted paths, and (3) verification/test commands — or offer to start from the bundled [project profile example](project-profile.example.md) defaults. Once confirmed, create `.orchestration/project-profile.md` (with its `<!-- orchestration-lanes:v1 -->` JSON block), initialize `.orchestration/provider-state.json` (`status: "up"`, `observed_at: null` until live usage is checked), suggest adding the ephemeral `.orchestration/` state files to `.gitignore`, and immediately proceed with the operator's task.

The main loop is a manager: it thinks, decides, writes briefs, directs and reviews, and
never executes deliverables itself, however small. Because the main loop shares the
ChatGPT/Codex quota pool with Sol, Terra, Luna and Astra, delegated execution is offloaded
primarily to non-OpenAI pools so Codex headroom stays available for the main loop: Claude
Opus (medium by default via claude -p, high for higher requirements, escalation,
Google-code cross-family review and peer advice) is the primary execution lane for
clear-spec implementation, migrations, test suites, refactors, real PG/HTTP, restricted
data, localized UI/prompts and open-ended debugging; Sonnet high handles simple-medium
scoped work, restricted data and network/package installs; gpt-6.2-sol (high default,
xhigh for higher requirements) serves as the parallel overflow lane and Claude-outage
fallback; gemini-4-neon high (via the configured Gemini runner) handles high-stakes
document/PDF checks and cross-family review of GPT/Claude work; gemini-4-hydrogen high
takes media, PDFs, screenshots, wide reading and search; and Haiku high, deepseek-flash
(publishable material only), gpt-6.1-terra medium (after sample qualification) or gpt-6-luna high handle bulk
cleanup. Load at the start of every Codex/ChatGPT management session (codex -m gpt-6.2-sol
-c model_reasoning_effort=xhigh), before delegating via codex exec, claude -p, the
configured Gemini runner or DeepSeek, and whenever any pool approaches thresholds or
returns a rate-limit or quota error.

A routing policy for a stack with **one strong main-loop model** and
**delegate lanes across four model families**. ChatGPT/Codex, Claude and
Gemini/Antigravity run on subscriptions; DeepSeek runs on a paid API.

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

- **Think.** Understand the request, weigh options, make architectural and
  design decisions and hard calls (or record locked decisions in
  `.orchestration/orchestration-checkpoint.md` under project handover rules).
- **Direct.** Split the work into units, pick the lane, write the brief,
  launch and follow the delegate, decide what happens next.
- **Review.** Read the report, read the diff or a sample, run read-only
  checks (tests, type check, build, `git diff`, `/status`), then accept the
  work or send it back.
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
   read-only local-port PG/HTTP verification tests when sandboxed `codex exec`
   cannot). A delegate still writes and fixes the scripts/migrations.
3. Answering the operator's question from what the main loop already knows
   or from a few targeted reads.

Before any tool call that writes a file or runs a command, ask: is this
thinking, directing, reviewing or record-keeping? If not, it is a brief.

## What changes with a Sol xhigh (ChatGPT / Codex) main loop

1. **Shared ChatGPT / Codex pool — offload execution to Claude, Gemini &
   DeepSeek first.** The `gpt-6.2-sol` `xhigh` main loop and every GPT delegate (`gpt-6.2-sol`,
   `gpt-6.1-terra`, `gpt-6-luna`, `gpt-6.2-astra`) draw from the **same
   ChatGPT/Codex five-hour and weekly pool**. Running the main loop on Sol
   `xhigh` instead of Astra `medium` cuts Codex pool burn ~2.5×, and
   offloading execution to Claude + Gemini stretches that allowance further.
   **Claude is an independent subscription pool here:** delegate clear-spec
   implementation (from written designs, migrations, test suites, fixed-scope
   refactors), real PG/HTTP with local ports/network, restricted data, localized
   UI/prompt quality, and open-ended architectural debugging to **Claude Opus
   `medium`** (`high` for higher requirements/escalation), and simple-medium
   edits, lookups and package installs to **Sonnet `high`** via `claude -p`.
   Send wide reading, media, PDFs, screenshots and search to **`gemini-4-hydrogen`
   `high`**, and publishable bulk to DeepSeek (`deepseek-flash`).
   Use `gpt-6.2-sol` (`high`/`xhigh`) for parallel cross-pool fan-outs or when
   the Claude pool approaches its threshold. Check Codex live allowance with
   `/status`.
2. **Pin model and effort at launch.** Always open the management session explicitly with
   `codex -m gpt-6.2-sol -c model_reasoning_effort=xhigh`. Switch to
   `astra-orchestration` only when a session specifically needs Astra's
   stronger multi-source synthesis.
3. **High-stakes document, PDF, accuracy and architecture checks.** Send high-stakes document/PDF judgments to
   **`gemini-4-neon` `high`** (the configured Gemini runner), wide PDF/image extraction to
   `gemini-4-hydrogen` `high`, and hard architectural/security/localized product
   calls to **`Opus` `high`** (`claude -p`) or **`Mythos/Fable` `medium`**.
4. **Cross-family review and second opinion invert around OpenAI / GPT (with
   Claude Opus `high` and Neon `high` as the two external pillars).**
   - **GPT-authored work (`Sol`, `Terra`, `Luna`, or Astra-authored policies /
     docs)** → **`gemini-4-neon` `high`** (configured runner with scoped review tools), or
     **`Opus` `high`** (`claude -p --model opus --effort high`) if Neon is
     unavailable. Never use Astra or another GPT model for independent
     cross-family review of GPT-authored work.
   - **Claude-authored work (`Opus`, `Sonnet`, `Haiku`)** → **`gemini-4-neon`
     `high`** (configured runner with scoped review tools), cross-family!
   - **Google-authored work (`Hydrogen` or `Neon`)** → **`Opus` `high`**
     (`claude -p --model opus --effort high`) is the primary independent
     cross-family reviewer while Sol `xhigh` is the main loop (record Sol's own
     read/test check as Management review, separate from independent review!).
     Only if Claude (`Opus` `high`) is unavailable does a fresh isolated
     `gemini-4-neon` `high` second eye run, explicitly labeled `same-family review`.
   - **Peer question / second opinion on Sol `xhigh`'s own calls** → **`gemini-4-neon`
     `high`** (for document/PDF accuracy and knowledge-heavy calls), **`Opus`
     `high`** (for architecture, security, localized UX/product nuance, or when
     Gemini is constrained), or **`Mythos/Fable` `medium`** advisor when available.
     All three are cross-family from OpenAI/GPT.
5. **Delegation mechanics from Codex CLI (`codex exec` + `claude -p` +
   the configured Gemini runner).**
   - **Claude lanes (`Opus` `medium`/`high`, `Sonnet` `high`, `Haiku` `high`)**
     run via headless Claude Code CLI (`claude -p`) after the [subscription preflight](references/cli-lanes-and-ledger.md#claude-code-subscription-preflight).
     Use an authorized fallback when the subscription cannot be confirmed. Never use
     `--dangerously-skip-permissions`. Note: **agy's built-in Claude credits
     are NOT a fallback lane** (reserved for configured short jobs) — use native `claude -p` instead.
   - **GPT lanes (`Sol` `high`/`xhigh`, `Terra` `medium`, `Luna` `high`)** run
     via `codex exec --skip-git-repo-check -m <model> -c
     model_reasoning_effort=<effort> -s <workspace-write|read-only> -o
     <report> "…" < /dev/null`. Give each delegate the applicable project rules and handover constraints in its brief. Because sandboxed
     `codex exec` cannot bind local ports (`listen EPERM`) or access network,
     route local-port/network execution pipelines directly to **`Opus`
     `medium`** (or `Sonnet` `high` for package installs); when Sol writes
     test files, the Sol `xhigh` main loop runs read-only verification tests.
   - **Gemini lanes (`Hydrogen` `high`, `Neon` `high`/`medium`)** run via
     the Gemini runner configured in the project profile.
6. **Pre-delegation gate.** Check live quota, split independent work,
   choose the eligible lane and effort, and prepare a bounded brief. Record
   the pool usage, unit, lane, and reason in the brief and checkpoint.

## The four pools

| Pool | Models in it | How it limits | Check with |
|---|---|---|---|
| **ChatGPT** subscription | `gpt-6.2-sol` (`xhigh` main loop, `high`/`xhigh` overflow), `gpt-6.2-astra`, `gpt-6.1-terra`, `gpt-6-luna` | A weekly allowance shared by Work and Codex; lower plans also have a five-hour window. Astra drains it several times faster than Sol; Luna barely touches it. | `/status` in Codex |
| **Claude** subscription | Opus (`medium`/`high` delegates), Sonnet (`high`), Haiku (`high`), Mythos/Fable (advisor) | A five-hour window and a weekly limit, shared by all models and by chat, Claude Code and `claude -p`. A Mythos/Fable model may have a separate allowance; check the selected model and plan. | `.orchestration/provider-state.json`, operator `/usage` report, `claude auth status` |
| **Gemini** subscription | `gemini-4-hydrogen`, `gemini-4-neon` | Antigravity Neon has a rolling five-hour window and weekly cap shared with Hydrogen and agy workers. Hydrogen also has plan-based CLI request limits where installed. | Gemini runner usage logs, Antigravity usage, `/stats` if Gemini CLI is installed |
| **DeepSeek** API (metered) | `deepseek-flash` | Prepaid balance or the configured gateway's request and token limits. | Provider balance or gateway quota reporting |

Consequences:

- **The main loop and every Codex delegate share one pool; Claude and Gemini
  are independent pools.** Offloading Opus-shaped tasks (PG/HTTP pipelines,
  restricted data, localized UI/prompts, open-ended architectural debugging) to
  **Claude Opus `medium`** and wide reading/media to **Gemini Hydrogen `high`**
  directly extends the Sol `xhigh` main loop's session!
- **The pools are independent.** Spreading a big job across Codex, Claude,
  Gemini and DeepSeek up front beats draining one and failing over.
- **DeepSeek is the only lane with no subscription window.** It is the
  pressure valve for publishable bulk volume.

## Routing procedure

Choose the first matching execution lane. Apply hard rule 7 before routing
and apply the final high-stakes check separately.

1. **Is it thinking, a decision, a brief, a review judgment or the final
   synthesis?** Main loop (`gpt-6.2-sol` `xhigh`). Nothing else stays there
   ("The manager rule"). For high-stakes document/PDF judgments, add a
   `gemini-4-neon` `high` check; for hard architecture/security/localized
   product calls, add `Opus` `high` or `Mythos/Fable` `medium`.
2. **Is it small?** Delegate to **`Sonnet` `high`** (`claude -p`) with a brief
   that names the file, change and check (keeping small edits out of the Codex
   pool). For Opus cases in hard rule 4, go to **`Opus` `medium`**. Skip this
   shortcut when a specialized input or work type below applies. Use
   `gpt-6.2-sol` `high` when Claude is full or down, or for parallel overflow.
3. **Is the input video or audio, or a pile of long PDFs or screenshots to
   turn into text or inspect visually?** `gemini-4-hydrogen` `high` (the configured Gemini runner).
   For video/audio only, `gemini-4-neon` `high` is the approved backup.
4. **Is it restricted data** (secrets, credentials, personal or client data)?
   Continue through the applicable lanes using **Claude only** (**`Opus`
   `medium`/`high`**, **`Sonnet` `high`**, **`Haiku` `high`** via `claude -p`),
   unless the operator has explicitly cleared another provider. Never send
   restricted data to DeepSeek; strip secrets from
   every brief regardless of destination.
5. **Is it mechanical work over many items?** For small and medium cleanup,
   optionally qualify `gpt-6.1-terra` `medium` on your runner by sampling a
   first job, then use Terra first for unrestricted batches once it passes.
   **`Haiku` `high`** covers batches before qualification, after a failed
   sample, for restricted data, or when Codex is down. For very large jobs use
   `gpt-6-luna` `high` or `deepseek-flash` (publishable material only).
6. **Is it wide reading that returns a conclusion** (a large codebase sweep,
   many documents, web research with sources)? `gemini-4-hydrogen` `high`,
   which keeps that volume out of both the Codex and Claude pools.
7. **Is it execution with a clear spec** (implementation from a written
   design, migrations, test suites, refactors with fixed scope)? Send to
   **`Opus` `medium`** (`claude -p --model opus --effort medium`), or **`Opus`
   `high`** for higher requirements, reasoning-/science-heavy sensitive work
   and escalation — keeping heavy coding volume out of the ChatGPT/Codex pool
   and avoiding `codex exec`'s local-port sandbox block. Use `gpt-6.2-sol`
   (`high` default, `xhigh` for higher requirements) as parallel cross-pool
   overflow or when Claude is full/down.
8. **Otherwise route by task.** Use **`Opus` `medium`** (`claude -p --model
   opus --effort medium`) for real PG/HTTP requiring local ports or network
   access, restricted data, localized UI or prompt quality, and open-ended
   architectural debugging (escalating to **`Opus` `high`** on two failures).
   Use **`Sonnet` `high`** for simple-medium scoped edits, lookups, network or
   package installs. Use `gpt-6.2-sol` (`high`/`xhigh`) when fanning out
   across pools or when Claude is unavailable (optionally logging standard
   debugging runs in `.orchestration/orchestration-ledger.md` to qualify Sol
   for standard debugging in your project).
9. **Is it a high-stakes call or a document/PDF-heavy judgment?** Add a peer
   question to **`gemini-4-neon` `high`** (document/PDF accuracy & knowledge)
   or **`Opus` `high`** / **`Mythos/Fable` `medium`** (architecture, security, localized
   product judgment) in parallel. This is an addition to the lane above, not a
   replacement.

## The routing table

| Work | Goes to | How to call it | Brief style |
|---|---|---|---|
| Architecture, specs, hard judgment, briefs, direction, review, final synthesis (no execution) | **Main loop** (`gpt-6.2-sol` `xhigh`) | itself (`codex -m gpt-6.2-sol -c model_reasoning_effort=xhigh`) | n/a |
| Second opinion, high-stakes document/PDF judgment, cross-family peer review on Sol `xhigh`'s call | **gemini-4-neon** `high` (accuracy/PDF/knowledge peer) or **Opus** `high` / **Mythos/Fable** `medium` (architecture, security, localized product peer) | Neon via the configured runner with Neon at `high`; Opus via `claude -p --model opus --effort high` | One peer question: problem, evidence, options, where unsure |
| Execution with a clear spec: implementation from a written design, migrations, test suites, refactors with fixed scope | **Opus** `medium` by default (`high` for higher requirements/escalation) to preserve Codex quota; **gpt-6.2-sol** (`high`/`xhigh`) as parallel overflow or Claude-outage fallback | `CI=true claude -p --model opus --effort <medium\|high>` (or `codex exec -m gpt-6.2-sol` when offloading from Claude) | Goal, spec, constraints and acceptance criteria (step-by-step when routed to Sol) |
| Real PG/HTTP requiring local ports or network access, restricted data that needs Opus, localized UI or prompt quality, open-ended architectural debugging | **Opus** `medium` (`claude -p`); escalate to **Opus** `high` on two failures | `CI=true claude -p --model opus --effort medium` (`high` on escalation) | Goal, context, constraints and acceptance criteria (fairly loose) |
| Simple-medium: scoped edits, pattern clones, lookups, templated work, straightforward reading and summarizing, network/package installs | **Sonnet** `high` (`claude -p`) to preserve Codex quota; **gpt-6.2-sol** `high` as parallel overflow or when Claude is full/down | `CI=true claude -p --model sonnet --effort high`, or `codex exec -m gpt-6.2-sol` (`high`) | Named files, steps, output shape and boundaries |
| Video, audio, long PDFs, screenshot sets turned into structured text or visual checks | **gemini-4-hydrogen** `high` (video/audio backup only: **gemini-4-neon** `high`) | configured Gemini runner with Hydrogen at `high` effort | Bounded: what to extract/inspect, output schema or checklist, timestamp/page/filename on every item |
| Wide reading and search-grounded lookups that return a conclusion with sources | **gemini-4-hydrogen** `high` | same (the configured Gemini runner) | The question, the scope, a stop condition, URLs or file paths required |
| Very large bulk jobs, long-prompt bulk, bulk overflow from Haiku or luna | **deepseek-flash** (publishable material only) | OpenAI- or Anthropic-compatible client using the configured DeepSeek endpoint | Exact rules, output schema, shared material first, per-item part last |
| Independent check from a different model family | GPT or Claude wrote it → **gemini-4-neon** `high` (if Neon unavailable for GPT work → **Opus** `high`). Google wrote it → **Opus** `high` (Sol `xhigh`'s own check is Management review; only if Opus is unavailable, fresh Neon `high` labeled **same-family**) | Neon via the configured runner with Neon at `high` and scoped review tools; Opus via `CI=true claude -p --model opus --effort high` (read-only tools) | The artifact, file list and acceptance criteria. Omit the author's reasoning |
| Second eye on a scoped question | **gemini-4-neon** `medium` (or **Opus** `medium` for GPT-authored work when Neon is unavailable) | the configured runner with Neon at `medium` or `claude -p --model opus --effort medium` (read-only) | Name the files, the question and the evidence to check |
| Bulk cleanup: normalizing, deduplicating, classifying, extracting | **terra (qualified sample) / Haiku** (small and medium) / **luna** (large). Sample the first Terra job on a new runner; if clean, use Terra first for unrestricted small/medium jobs. Use **Haiku** `high` (`claude-haiku-5-5`) before qualification, for restricted data, or when Codex is down | `codex exec -m gpt-6.1-terra` (`medium`), `claude -p --model haiku --effort high`, or `codex exec -m gpt-6-luna` (`high`) | Exact rules with examples, small batches and spot checks |

Integration (merging several delegates' outputs, resolving conflicts between
them, wiring pieces together) is execution, not synthesis: the main loop
decides how the pieces fit and a lane does the merging from a brief that
states those decisions.

**Default efforts per lane** (pin them on every call; effort can change relative performance):
main loop `gpt-6.2-sol` `xhigh`, Mythos/Fable
advisor `medium`, **Opus delegates `medium`** (**`high`** for escalation,
cross-family review of Google/GPT work, and peer questions), Sonnet `high`,
Haiku `high`, `gpt-6.2-sol` `high`, Sol `xhigh` for
higher requirements, reasoning- or science-heavy sensitive work and escalation,
`gpt-6.1-terra` `medium` (cleanup batches), `gpt-6-luna` `high`,
`gemini-4-hydrogen` `high`, `gemini-4-neon` `high` (independent review &
document/PDF check) or `medium` (second eye), `deepseek-flash` at its highest
reasoning setting. Measured profile of each in "Model notes".

Reserve `deepseek-flash` checks for bulk or low-stakes work.

"DeepSeek v4.1" means one model today: V4.1 Flash, API alias `deepseek-flash`
(canonical catalog ID `deepseek-v4.1-flash-1017`). There is no V4.1 Pro yet, and
`deepseek-v4-pro` (`deepseek-v4-pro-0813`) is the older V4 Pro, which DeepSeek
itself ranks below V4.1 Flash. Do not route to it.

## The hard rules

1. **Always pass an explicit model and effort** on every `codex exec`
   (`-m` + `-c model_reasoning_effort=`), `claude -p` (`--model` + `--effort`),
   and every Gemini runner call. Never rely on client defaults.
2. **Do not burn Codex quota on `gpt-6.2-astra` sub-agents or redundant Sol
   fan-outs when Claude is open.** Offload routine execution to Claude
   (`Opus` `medium`/`high`, `Sonnet` `high`) first; use `gpt-6.2-sol`
   (`high`/`xhigh`) delegates for parallel overflow or Claude outages, and
   never use any GPT model for cross-family review of GPT-authored work.
3. **Route by difficulty, then pick the lightest lane that can carry it.**
   When unsure between two tiers, take the lighter one and verify the result;
   escalate one tier on failure rather than starting high.
4. **Offload routine execution out of Codex first.** Use **`Opus` `medium`**
   (`claude -p`, escalating to **`Opus` `high`**) as the primary execution lane
   for clear-spec implementation, migrations, test suites, fixed-scope
   refactors, real PG/HTTP with local ports/network, restricted data, localized
   UI/prompts and open-ended architectural debugging; use **`Sonnet` `high`**
   for simple-medium edits, network/package installs and restricted data. Use
   **`gpt-6.2-sol` `high`** (and `xhigh` for higher requirements/escalation)
   for parallel cross-pool overflow or when the Claude pool is full/down.
   Follow hard rule 7 and the routing table for data and specialized lanes.
5. **The main loop keeps its own context lean.** Wide reading, file dumps and
   raw data go to a delegate (`gemini-4-hydrogen` `high`) that returns the
   conclusion; the main loop reads only what it must judge.
6. **A delegate's report is a claim.** Check the diff, run the tests or read a
   sample before reporting it as done.
7. **Data leaves only as far as it must.** Restricted data (secrets,
   credentials, personal or client data) stays on **Claude tiers (`Opus`,
   `Sonnet`, `Haiku` via `claude -p`)** unless the operator has cleared
   another provider for it. The hosted DeepSeek API gets only material the operator would be comfortable publishing. Strip secrets from every brief regardless of destination.
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
    `git worktree` checkouts.
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

Read the applicable reference file before executing any of the procedures below:

| Reference | Mandatory trigger |
|---|---|
| [references/delegation-and-verification.md](references/delegation-and-verification.md) | Read before writing a worker brief, splitting parallel units, or running cross-family verification (`BLOCKER`/`NIT`, review circuit breaker, test integrity). |
| [references/quota-and-failover.md](references/quota-and-failover.md) | Read when any pool nears thresholds (**85% weekly / 90% five-hour move; 90% weekly / 95% five-hour stop**), hits a rate/quota limit, times out/hangs, fails mid-edit, requires a handoff checkpoint, or recovers after context compaction / session resume. |
| [references/cli-lanes-and-ledger.md](references/cli-lanes-and-ledger.md) | Read before invoking external runner CLIs (`codex exec`, `claude -p`, configured Gemini runner, DeepSeek), running `resolve_lanes.py` or reading benchmark snapshots, or recording `.orchestration/orchestration-ledger.md` entries. |

**Mandatory worker return contract:** Every brief on every lane must end by requiring the 4-line return block: `STATUS: done | partial | blocked`, `RESULT`, `EVIDENCE`, and `NOT DONE`.
Any report missing `EVIDENCE` is treated as `partial`.

## Exceptions

- If the operator explicitly names a model for a scoped task, honor it for that
  task only, then return to this policy.
- The operator can override any of this per session; absent that, this policy
  stands.
- During a Claude-pool handover, skip Claude lanes and follow the decision and commit rules in the project profile.
- When moving the main loop to another client/model family, switch to its
  corresponding skill (`fable-orchestration`,
  `opus-orchestration`, `neon-orchestration`, or `astra-orchestration`).
