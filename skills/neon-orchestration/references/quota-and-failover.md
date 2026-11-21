# Quota and failover — Neon orchestration

Reference companion to [SKILL.md](../SKILL.md).

## Quota levers

- **Check before a big fan-out.** Check `swarm{action:"models"}` for
  Gemini/Antigravity remaining `%` and reset time, `.orchestration/provider-state.json` and
  `/status` for Codex, and the configured DeepSeek quota or balance. If a fleet would use
  more than half of what is left in one pool's current window, split it
  across pools now.
- **Keep volume out of the Gemini pool.** The Neon main loop lives here.
  Every Hydrogen/Neon Swarm worker spends from this pool's 5-hour/weekly
  window too. Put code execution in Codex (`Sol`), large bulk in DeepSeek or
  `Luna`/`Terra`, and keep Gemini focused on media, visual inspection, wide
  source sweeps, and required cross-family reviews.
- **Protect the main loop.** At 90 % of the five-hour window (or 85 % of the
  weekly cap), move eligible delegated units off Gemini and keep
  `.orchestration/orchestration-checkpoint.md` current; at 95 % of the
  five-hour window (or 90 % of the weekly cap), stop starting new large Gemini
  delegates, finish running units, update
  `.orchestration/orchestration-checkpoint.md` and the handover note, and
  switch cleanly if needed.
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
   `.orchestration/provider-state.json` or operator `/usage`. Price-per-task figures do not
   measure subscription burn.
2. **Thresholds.** Past the "move" mark,
   new delegated units go to the equivalent lane (the 1st fallback in the
   ladder below) instead of queuing on the pool; past the "stop" mark, no
   new large job starts there and running units finish. The main loop keeps
   working past both only as needed to finish checks and update the checkpoint.

   | Pool | Move delegated units | Stop large jobs, write the checkpoint |
   |---|---|---|
   | Gemini/Neon five-hour, Hydrogen daily | **90 %** | **95 %** |
   | Gemini/agy weekly | **85 %** | **90 %** |
   | Codex weekly | **85 %** | **90 %** |
   | Codex five-hour | **90 %** | **95 %** |
   | DeepSeek gateway daily, when applicable | **90 %** | **95 %** |
   | Claude five-hour window | **90 %** | **95 %** (keep the checkpoint current from 90 %) |
   | Claude weekly limit | **85 %** | **90 %** (keep the checkpoint current from 85 %) |

   The five-hour window resets within hours, so it is used later; the weekly
   limit costs days when it runs out, so delegated work leaves it earlier.
3. **Spread by headroom.** When a fan-out has several equivalent lanes,
   split units in proportion to each pool's remaining allowance, not evenly.
   Available free capacity takes bulk first.
4. **Equivalent means equal or better on the lane's task profile**, within 3
   points on a comparable scale. See Model notes for the workspace and historical data.
   Among equivalents, take the lowest time per task. A model far above the
   lane is used only if it is also no slower and lighter on its pool than
   the next equivalent. **When two fallbacks are both equivalent, the pool
   with more headroom wins and speed only breaks a tie**; that is what keeps
   use even across pools.
5. **Gemini uses the standard pool thresholds.**
   Hydrogen covers media, wide reading and search, and Neon covers the main
   loop (here), second-eye work, independent review and media fallback.
   Gemini follows the same **90 %** move / **95 %** stop (five-hour or daily)
   and **85 %** move / **90 %** stop (weekly) thresholds as every other pool.
   When Gemini nears 90 % (five-hour/daily) or 85 % (weekly), prioritize
   main-loop turns, media and mandatory reviews.
6. **Raise verification for weaker fallbacks.** For Hydrogen's
   accuracy-heavy reading, Astra `medium` is **below** on accuracy. For
   Neon `high` review, Astra `medium` is **below** on accuracy, knowledge
   and reasoning; Opus `high` (for GPT-authored work) is marked **below** on
   all profiles. For Neon `medium` second-eye work, accuracy is unmeasured
   (n = 0): the operator marks Astra `medium` **below** on accuracy there, and
   Opus `medium` is **below** on code, reasoning and knowledge. Raise
   verification one step, label the output and prefer waiting when reset is
   within about 30 minutes.
7. **agy's Claude models are not a fallback lane.** Reserve them for configured
   short single jobs only.

## When a limit is hit

### 1. Classify the error

| Class | What it looks like | Meaning |
|---|---|---|
| **A. Throttle** | HTTP 429 with a short retry hint; "slow down and try again after N seconds"; HTTP 503 or 529 overloaded; Claude Code's "Server is temporarily limiting requests (not your usage limit)"; DeepSeek 429 | Too fast right now. Capacity returns in seconds to minutes. |
| **B. Window exhausted** | "5-hour limit reached · resets [time]"; a Codex usage-limit message with a reset time; Gemini `RESOURCE_EXHAUSTED` or Antigravity `quota_remaining: 0%` with reset time | This window's allowance is gone. A reset time is known, hours away at most. |
| **C. Plan exhausted** | "You've hit your weekly limit"; "Model-specific usage limit reached"; weekly Antigravity cap depleted; DeepSeek balance depleted (HTTP 402) | Nothing returns without waiting days or paying. |
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
- **B, window exhausted.** Record the reset time in `.orchestration/provider-state.json`. If
  it is within about 20 minutes and other lanes have work, reorder and come
  back. Otherwise fail over along the ladder. Tell the operator once.
- **C, plan exhausted.** Mark the affected model or shared pool down in
  `.orchestration/provider-state.json` until its reset, fail over, and tell the operator, naming any paid options without
  taking them. For a depleted DeepSeek quota, report and wait or route
  along the ladder.
- **D, not a limit.** Do not fail over. Fix the request.
- **E, lane's own failure.** Count these per lane in
  `.orchestration/orchestration-ledger.md`. A failure the main loop caused (a wrong path or
  conversation id in the brief, missing tool access, an incorrect workspace,
  overlapping files) does not count. After each lane-owned failure, add the
  trap to the brief and relaunch on the same lane. When a lane has made
  **more than three** (on the fourth), new units for that lane go to its 1st
  fallback in the ladder below, and a unit that was running moves too, provided partial
  artifacts are isolated (or only that unit's broken uncommitted edits are
  reverted cleanly first — see Handoff rules). If the fallback continues from
  verified output artifacts written to files, read those files rather than
  restarting completed sub-items from zero. The quota thresholds still apply
  to the fallback.

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
| **Main loop** Orchestrator (Neon) / `gemini-4-neon` `high` | **Mythos/Fable** `medium` (**below** on all profiles: code, reasoning, accuracy, knowledge) or **Opus** `high` (**below** on all profiles) in the Claude app under `fable-orchestration` / `opus-orchestration` | **`gpt-6.2-astra`** `medium` (under `astra-orchestration`) or lower-burn **`gpt-6.2-sol`** `xhigh` (under `sol-orchestration`) in Codex (**below** on reasoning, accuracy and knowledge) | | Wait for reset |
| **Mythos/Fable advisor** `medium` | `gpt-6.2-astra` `medium` with the same question (cross-family from Neon, **below** on accuracy) | `Opus` `high` (**below** on code/reasoning/accuracy) | | Decide without the second opinion and say so |
| **Opus delegate** `medium` | `gpt-6.2-sol` `high`, with a step-by-step brief | `gemini-4-neon` `medium` | `gemini-4-hydrogen` `high` | Wait for reset |
| **Opus** `high`, escalation | `gpt-6.2-astra` `medium` | `gemini-4-neon` `high` | | Wait for reset |
| **Sonnet** `high` | `gpt-6.2-sol` `high` | `gemini-4-hydrogen` `high` | | Wait for reset |
| **Haiku** `high` | `gpt-6.1-terra` `medium` (sample the first job on a new runner; if it fails, `gpt-6.2-sol` `high`) | `gemini-4-hydrogen` `medium` | | Queue |
| **gpt-6.2-sol** `xhigh` | `gemini-4-neon` `high` (equal or better, slower) | `gemini-4-neon` `medium` (**below** on code and reasoning) | `Opus` `high` (**below** on code and reasoning) | Wait for reset |
| **gpt-6.2-sol** `high`, default | `gemini-4-neon` `medium` | `Opus` `high` (**below** on reasoning) | `gemini-4-hydrogen` `high` (**below** on code and reasoning) | Wait for reset |
| **gpt-6.2-astra** `medium` | Mythos/Fable advisor `medium` (cross-family) | `Opus` `high` (**below** on code/reasoning/accuracy; cross-family) | Only when both Codex and Claude are unavailable: fresh isolated `gemini-4-neon` `high` (equal or better, slower; **same-family** when Neon is main loop — label explicitly) | Skip the second opinion and say so |
| **gpt-6-luna** `high` (knowledge work) | `gemini-4-hydrogen` `low` | `deepseek-flash` (slower, first choice for very large publishable batches when budget permits) | `Haiku` `medium` (faster for small or restricted batches) | Queue |
| **gemini-4-hydrogen** `high`, PDFs, images, reading, search | `gpt-6.2-astra` `medium`, **below** on accuracy. Require sources and raise verification one step. | `Sonnet` `high` (Claude), **below** on accuracy (and borderline on knowledge), for bulk reading only | | Queue |
| **gemini-4-hydrogen**, video or audio | `gemini-4-neon` `high` (media only). Keep Hydrogen first for media when it has headroom. | | | Queue if a shared Gemini limit takes down both |
| **gemini-4-neon** `high`, reviewer | For Claude- or Google-authored work: `gpt-6.2-astra` `medium` (**below** on accuracy, knowledge and reasoning; raise verification one step; never for GPT-authored work). For GPT-authored work: `Opus` `high` (**below** on all profiles; raise verification one step). | | | Queue independent cross-family review |
| **gemini-4-neon** `medium`, second eye | For Claude- or Google-authored work: `gpt-6.2-astra` `medium` (accuracy comparison is unmeasured for Neon `medium`). Raise verification one step. | For GPT- or Google-authored work: `Opus` `medium` (**below** on code/reasoning/knowledge) | | Skip the second eye and say so |
| **deepseek-flash** | `gpt-6.2-sol` `high` (light on Codex) | `gemini-4-hydrogen` `medium` | `Sonnet` `high` (Claude) | Queue |

**Limits attach to pools, not model names.** A shared Antigravity/Gemini
five-hour or weekly limit takes down the Neon main loop, Neon reviewers and
Hydrogen workers together. A Codex usage limit takes down Sol, Astra, Terra
and Luna together. A Claude limit takes down Mythos/Fable, Opus, Sonnet and
Haiku together (a model-specific limit can leave the other Claude lanes available).

**When the Gemini / Antigravity pool runs low or goes down:**

1. At **90 %** of the five-hour window or **85 %** of the weekly cap, move
   eligible delegated units off Gemini and keep
   `.orchestration/orchestration-checkpoint.md` current; at **95 %** of the
   five-hour window or **90 %** of the weekly cap, stop starting new large
   Swarm/agy delegates, finish running units, update
   `.orchestration/orchestration-checkpoint.md` and the handover note, and
   switch cleanly before Antigravity refuses turns.
2. If the Gemini pool is exhausted and resets within ~30 minutes, wait rather
   than rebuilding the stack. Otherwise switch to **Claude
   (`fable-orchestration` / `opus-orchestration`)** or **Codex
   (`astra-orchestration`, `codex -m gpt-6.2-astra -c model_reasoning_effort=medium`;
   or lower-burn `sol-orchestration`, `codex -m gpt-6.2-sol -c model_reasoning_effort=xhigh`)**.

### 4. Handoff rules

A fallback lane starts from files, never from another model's memory.

- **Checkpoint file.** `.orchestration/orchestration-checkpoint.md` holds the
  goal, decisions made and why, the unit list with a status per
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

Keep `.orchestration/provider-state.json` so every session routes around a
pool that is down instead of rediscovering it.

```json
{
  "claude":          {"status": "up", "down_until": null, "limit": null},
  "claude-model-id": {"status": "up", "down_until": null, "limit": null},
  "codex":           {"status": "up", "down_until": null, "limit": null},
  "gemini":          {"status": "up", "down_until": null, "limit": null},
  "deepseek":        {"status": "up", "down_until": null, "limit": null}
}
```

- Check it before every spawn.
- When `down_until` passes, send **one** small request as a probe. On
  success, mark the pool up and return new work to its normal lane. On
  failure, extend `down_until` and wait 15 minutes before probing again.
- Work already running on a fallback lane finishes there; only new units
  return to the primary lane.
