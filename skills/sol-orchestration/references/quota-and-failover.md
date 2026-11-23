# Sol Orchestration — Quota Levers, Load Balancing & Failover

## Quota levers

- **Check before a big fan-out.** Check `/status` in Codex,
  `.orchestration/provider-state.json`, Gemini runner usage logs, and
  the configured DeepSeek quota or balance. If a fleet would use more than half of what is
  left in one pool's current window, split it across pools now.
- **Keep Opus-shaped, reading and bulk work out of the ChatGPT/Codex pool.**
  The Sol `xhigh` main loop lives here alongside any Codex overflow delegates. Send PG/HTTP pipelines,
  restricted data, localized UI/prompts and open-ended debugging to **Claude
  Opus `medium`**, wide reading/media/PDFs/screenshots to **Gemini Hydrogen
  `high`**, and publishable bulk to DeepSeek (`deepseek-flash`).
- **Protect the main loop.** Keep main-loop turns concise and never run loose multi-turn exploration
  directly in Codex; delegate wide reading to `gemini-4-hydrogen` `high`. At **90 %** of either the Codex five-hour or weekly window, move eligible delegated
  units off Codex (`Opus` `medium`/`high`, `Sonnet` `high`, `Neon` `medium`)
  and keep `.orchestration/orchestration-checkpoint.md` current; at **95 %** of either window (or on pre-dispatch `projected-overflow`), stop starting new large Codex delegates, finish running units,
  update `.orchestration/orchestration-checkpoint.md` and the handover note, and
  switch cleanly if needed.
- **Effort before tier.** When a Sol result is close but not right, raise
  effort one step (`high` → `xhigh`) before escalating models; when an `Opus`
  `medium` result is close, raise to `Opus` `high`.
- **Start heavy fleets just after a window resets**, and ramp concurrency
  from a quarter of the planned width. Bursts trip per-minute limits.

## Approaching a limit: load balancing

The aim is to keep working as long as possible with no drop in quality, and
as fast as possible within that. Act **before** a pool runs dry, not after.

1. **Read live usage right before dispatch and right after each unit, not
   estimates.** Codex: `read_quota.py --write` (or `/status`); Gemini/agy: Gemini runner usage logs and quota
   errors; DeepSeek: provider quota or balance; Claude:
   `.orchestration/provider-state.json` or operator `/usage`. Price-per-task
   figures do not measure subscription burn. Treat the 5-minute TTL as the upper
   bound for idle readings only — always re-check live pool usage right before
   dispatching a delegated unit and right after it finishes.
2. **Unified thresholds (90 % move / 95 % stop for both five-hour and weekly
   windows).** Past the "move" mark (**90 %**, `deprioritized`), new delegated
   units go to the equivalent lane (the 1st fallback in the ladder below)
   instead of queuing on the pool; past the "stop" mark (**95 %**, `blocked`),
   no new large job starts there and running units finish. The main loop keeps
   working past both only as needed to finish checks and update the checkpoint.

   | Pool | Move delegated units (`deprioritized`) | Stop large jobs, write the checkpoint (`blocked`) |
   |---|---|---|
   | Codex five-hour & weekly | **90 %** | **95 %** |
   | Claude five-hour & weekly | **90 %** | **95 %** (keep the checkpoint current from 90 %) |
   | Gemini/Neon five-hour & weekly, Hydrogen daily | **90 %** | **95 %** |
   | DeepSeek gateway daily, when applicable | **90 %** | **95 %** |

   Both five-hour/daily and weekly windows share the same **90 % move / 95 %
   stop** thresholds, paired with the self-calibrating pre-dispatch guard below
   so a large unit cannot push an active window past 95 % mid-work.

   **Read the Codex quota before dispatch (no interactive `/status` needed):**
   run `python3 -B <skills>/update-orchestration-skills/scripts/read_quota.py --write`
   (`<skills>` is `.claude/skills` or `.agents/skills`) **before**
   `resolve_lanes.py --unit-size ...`. It takes the newest Codex `rate_limits`
   event from `~/.codex/sessions/` and writes `five_hour_pct`, `weekly_pct`,
   `resets_at` and `observed_at` of the `codex` entry in
   `.orchestration/provider-state.json` (the file must already exist; other
   entries and `_calibration` are untouched). `observed_at` is the reading
   time, not the log time: Codex percentages change only when Codex is used, so
   the latest event is current even if it is old. Without a fresh `observed_at`
   the resolver treats the pool as `stale` (5-minute TTL) and ignores its
   percentages. ChatGPT web usage draws on the same weekly pool but is not in
   the Codex log, so read the weekly figure as a lower bound. Claude and
   Gemini pools are still read live as in step 1.

   **Pre-dispatch projected overflow guard & self-calibration (`_calibration`):**
   Before dispatching each unit, classify its size and run
   `resolve_lanes.py --unit-size <xs|s|m|l|xl>` against fresh live readings in
   `.orchestration/provider-state.json`. The resolver computes
   `projected = current + estimated_burn × safety_margin` for each known fresh
   window:

   | Unit size | Multiplier | Typical scope |
   |---|---|---|
   | `xs` | `0.25×` | One-line fix, single lookup, tiny config edit |
   | `s` | `0.55×` | Small scoped edit, targeted test or quick check |
   | `m` | `1.00×` | Standard single-module implementation, test suite or review |
   | `l` | `1.90×` | Multi-file feature, refactor, migration or heavy cross-family review |
   | `xl` | `3.20×` | Large multi-module sweep or migration (split into smaller units when headroom is tight) |

   - **`projected-overflow` (`projected >= 95 %` stop):** The lane is marked
     `blocked` and **must not receive the unit** (for example, Codex at 89 %
     five-hour with an ~11 % `l` unit projects `89 % + 11 % × 1.2 = 102.2 % >= 95 %`).
     Route to a healthy equivalent fallback or split the unit into smaller
     pieces that fit safely below 95 %.
   - **`projected-deprioritized` (`90 % <= projected < 95 %`):** The lane is
     deprioritized so healthy equivalent lanes with headroom rank ahead of it.
   - **A recommended lane flagged `deprioritized` or `projected-deprioritized`**
     (the resolver ranks quality first, so it still recommends such a lane when
     no other lane is within ±3 points; the JSON field `dispatch_ok` is then
     `false`): **do not dispatch new units to that pool.** Take the next ladder
     step (label it below-tier and raise verification one step) or wait for the
     reset. `projected-overflow` (`>= 95 %`) is a hard stop: the lane is
     excluded and never receives the unit.
   - **Cold-start & automatic EWMA plan calibration:** On cold start (`0`
     samples), `resolve_lanes.py` uses conservative medium-unit baselines
     (`codex` 5.0%/2.0%, `claude` 6.0%/2.5%, `gemini` 4.5%/1.8%, `deepseek`
     2.0%/1.0% for 5h/weekly, scaled by model weight) with `safety_margin = 1.40`
     (dropping to `1.25` at 1–2 samples and adaptive
     `min(1.50, max(1.15, max_ratio))` at 3+ samples; optional override
     `--safety-margin <1.0..3.0>`). Right after each unit finishes, read live
     usage again and run `resolve_lanes.py --record-burn` to update the EWMA
     (`alpha = 0.35`) under `_calibration` in `.orchestration/provider-state.json`
     (lane-specific `lanes["<provider>/<model>/<effort>"]` with `by_size` plus
     pool-level `pools["<provider>"]`), so estimates automatically adapt to the
     operator's exact subscription plan (Pro / Plus / Max / Team).
   - **Window-reset guard:** If a window resets during a unit (`after < before`,
     or `--reset-occurred` is passed), `resolve_lanes.py --record-burn`
     automatically skips the EWMA update for that window while still recording
     the fresh `after` percentage.
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
   Hydrogen covers media, wide reading and search, and Neon covers second-eye
   work, independent review and media fallback. Gemini follows the same
   **90 %** move / **95 %** stop thresholds across both five-hour/daily and
   weekly windows as every other pool. When Gemini nears 90 % on either window,
   prioritize media and required reviews.
6. **Raise verification for weaker fallbacks.** For Hydrogen's
   accuracy-heavy reading, Astra `medium` is **below** on accuracy. For
   Neon `high` review, `Opus` `high` (for GPT-authored work) is marked
   **below** on all profiles, and Astra `medium` is **below** on accuracy,
   knowledge and reasoning (and never cross-family for GPT work). For Neon
   `medium` second-eye work, accuracy is unmeasured (n = 0): Astra `medium` is
   **below** on accuracy and `Opus` `medium` is **below** on code, reasoning
   and knowledge. Raise verification one step, label the output and prefer
   waiting when reset is within about 30 minutes.
7. **agy's Claude models are not a fallback lane.** Reserve them for configured short jobs. Use native
   `claude -p` on the Claude subscription instead.

## When a limit is hit

### 1. Classify the error

| Class | What it looks like | Meaning |
|---|---|---|
| **A. Throttle** | HTTP 429 with a short retry hint; "slow down and try again after N seconds"; HTTP 503 or 529 overloaded; Claude Code's "Server is temporarily limiting requests"; DeepSeek 429 | Too fast right now. Capacity returns in seconds to minutes. |
| **B. Window exhausted** | "You've hit your usage limit... try again at [time]" in Codex; "5-hour limit reached · resets [time]" in Claude; Gemini `RESOURCE_EXHAUSTED` on daily/5h quota | This window's allowance is gone. A reset time is known, hours away at most. |
| **C. Plan exhausted** | "You've hit your weekly limit"; "Model-specific usage limit reached"; DeepSeek balance depleted (HTTP 402) | Nothing returns without waiting days or paying. |
| **D. Not a limit** | HTTP 400, 401, 403; context length exceeded; model not found; content refusal | The request is wrong. No other provider will fix it. |
| **E. Lane's own failure** | The model stops on its own mistake, not on the work or a limit: a tool-permission denial it caused (e.g. agy: `ls` typed into ReadFile, a read outside the workspace), an early exit with no output, a file-lock collision | The lane is unreliable for this unit right now. |
| **F. Timeout / Hung lane** | Worker stalls on an interactive prompt, enters a runaway loop, or exceeds its bounded time/step budget (guide: 5–10 min small/medium, 15 min heavy review/complex) | The lane is wedged, not making progress. Always launch CLI runners non-interactively with `< /dev/null` and `CI=true`. |

Read the message, not only the status code: Codex, Claude and Gemini state
reset times and scope. When the class is unclear, treat it as A once; if the
same error returns after the backoff, treat it as B.

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
  to the fallback. Reset per-lane Class E counters per session (or after a clean
  cooldown probe) so a lane is not permanently blacklisted across days.
- **F, timeout / hung lane.** Terminate the hung process, revert only that
  interrupted unit's broken unaccepted edits if needed (see Handoff rules), and
  tighten scope or constraints once before retrying. On a second hang for the
  same lane/unit, treat it as Class E and fail over along the ladder.

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
| **Main loop** `gpt-6.2-sol` `xhigh` | Antigravity **Orchestrator (Neon)** or **`gemini-4-neon`** `high` (equal or better on all profiles, slower) under `neon-orchestration` | **Mythos/Fable** `medium` (**below** on reasoning) or **Opus** `high` (**below** on code and reasoning) in Claude app under `fable-orchestration` / `opus-orchestration` | | Wait for reset |
| **Mythos/Fable advisor** `medium` | `gemini-4-neon` `high` (equal or better, slower) | `Opus` `high` (**below** on code/reasoning/accuracy) | | Decide without the second opinion and say so |
| **Opus delegate** `medium` | `gpt-6.2-sol` `high`, with a step-by-step brief | `gemini-4-neon` `medium` | `gemini-4-hydrogen` `high` | Wait for reset |
| **Opus** `high`, escalation | `gemini-4-neon` `high` (equal or better, slower; cross-family from GPT) | `gpt-6.2-sol` `xhigh` (Codex escalation; avoids spawning Astra sub-agents per hard rule 2) | | Wait for reset |
| **Sonnet** `high` | `gpt-6.2-sol` `high` | `gemini-4-hydrogen` `high` | | Wait for reset |
| **Haiku** `high` | `gpt-6.1-terra` `medium` (sample the first job on a new runner; if it fails, `gpt-6.2-sol` `high`) | `gemini-4-hydrogen` `medium` | | Queue |
| **gpt-6.2-sol** `xhigh` | `gemini-4-neon` `high` (equal or better, slower) | `gemini-4-neon` `medium` (**below** on code and reasoning) | `Opus` `high` (**below** on code and reasoning) | Wait for reset |
| **gpt-6.2-sol** `high`, default | `gemini-4-neon` `medium` | `Opus` `high` (**below** on reasoning) | `gemini-4-hydrogen` `high` (**below** on code and reasoning) | Wait for reset |
| **gpt-6-luna** `high` (knowledge work) | `gemini-4-hydrogen` `low` | `deepseek-flash` (slower, first choice for very large publishable batches when budget permits) | `Haiku` `medium` (faster for small or restricted batches) | Queue |
| **gemini-4-hydrogen** `high`, PDFs, images, reading, search | `gpt-6.2-astra` `medium`, **below** on accuracy. Require sources and raise verification one step. | `Sonnet` `high` (Claude), **below** on accuracy (and borderline on knowledge), for bulk reading only | | Queue |
| **gemini-4-hydrogen**, video or audio | `gemini-4-neon` `high` (media only). Keep Hydrogen first for media when it has headroom. | | | Queue if a shared Gemini limit takes down both |
| **gemini-4-neon** `high`, reviewer | For GPT-authored work: `Opus` `high` (**below** on all profiles; raise verification one step; never route GPT-authored review to Astra). For Claude- or Google-authored work: `Opus` `high` (for Google) or `gpt-6.2-astra` `medium` (**below** on accuracy/knowledge/reasoning; Management review only if GPT is main loop). | | | Queue independent cross-family review |
| **gemini-4-neon** `medium`, second eye | For GPT-authored work: `Opus` `medium` (**below** on code/reasoning/knowledge). For Claude- or Google-authored work: `gpt-6.2-astra` `medium` (accuracy comparison is unmeasured for Neon `medium`). Raise verification one step. | | | Skip the second eye and say so |
| **deepseek-flash** | `gpt-6.2-sol` `high` (light on Codex) | `gemini-4-hydrogen` `medium` | `Sonnet` `high` (Claude) | Queue |

**Limits attach to pools, not model names.** A ChatGPT/Codex usage limit takes
down the Sol `xhigh` main loop, Astra, Terra and Luna together. A Claude limit takes
down Mythos/Fable, Opus, Sonnet and Haiku together (a model-specific limit can leave the other Claude lanes available). A shared Gemini limit takes down
Hydrogen and Neon together.

**When the ChatGPT / Codex pool runs low or goes down:**

1. At **90 %** of either the five-hour or weekly window, move
   eligible delegated units off Codex (to **Claude `Opus` `medium`/`high`**,
   **`Sonnet` `high`**, or **`gemini-4-neon` `medium`** along the ladders) and
   keep `.orchestration/orchestration-checkpoint.md` current.
2. At **95 %** of either the five-hour or weekly window (or when pre-dispatch
   `resolve_lanes.py --unit-size` flags `projected-overflow`), stop
   starting new large Codex delegates, finish running units, update `.orchestration/orchestration-checkpoint.md` and the handover note, and commit them (`.orchestration/provider-state.json` stays local) before Codex refuses turns.
3. If Codex hits its limit and resets within ~30 minutes, wait rather than
   rebuilding the stack. Otherwise switch to **Antigravity (`neon-orchestration`,
   Orchestrator (Neon) / `gemini-4-neon` `high`)** or **Claude
   (`fable-orchestration` / `opus-orchestration`)**.

### 4. Handoff rules

A fallback lane starts from files, never from another model's memory.

- **Checkpoint file.** `.orchestration/orchestration-checkpoint.md` holds the
  goal, decisions made and why, the unit list with a status per
  unit (todo, running, done, verified), where each output lives, and open
  questions. Write it before any fan-out, update it lightly after each accepted
  unit (not only at 90%/95% quota or before fan-outs), and update it whenever a
  unit changes state. Commit it with the project, together with `orchestration-ledger.md`, so the handover history survives across clients (ignore them only if you keep handovers local); `provider-state.json` stays local and git-ignored.
- **Compaction recovery.** Whenever context compaction or session resume occurs,
  re-read `.orchestration/orchestration-checkpoint.md`,
  `.orchestration/provider-state.json`, and `git status --short` before spawning
  any new delegate.
- **Units are idempotent.** Each unit writes its own output file. A unit that
  was running when the limit hit is rerun whole on the new lane.
- **Rewrite the brief for the new reader.** An Opus brief handed to Sol
  unchanged will underperform. Use the brief shape of the receiving lane.
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
  "claude":          {"status": "up", "down_until": null, "limit": null, "five_hour_pct": null, "weekly_pct": null, "resets_at": null, "observed_at": null},
  "claude-model-id": {"status": "up", "down_until": null, "limit": null, "five_hour_pct": null, "weekly_pct": null, "resets_at": null, "observed_at": null},
  "codex":           {"status": "up", "down_until": null, "limit": null, "five_hour_pct": null, "weekly_pct": null, "resets_at": null, "observed_at": null},
  "gemini":          {"status": "up", "down_until": null, "limit": null, "five_hour_pct": null, "weekly_pct": null, "resets_at": null, "observed_at": null},
  "deepseek":        {"status": "up", "down_until": null, "limit": null, "five_hour_pct": null, "weekly_pct": null, "resets_at": null, "observed_at": null}
}
```

- **Pre-dispatch & post-unit checks + 5-minute TTL:** Check live usage right
  before dispatching each unit (`resolve_lanes.py --unit-size <xs|s|m|l|xl>`)
  and right after it finishes (`resolve_lanes.py --record-burn`, which updates
  live `after` percentages and the reserved `_calibration` EWMA key inside
  `.orchestration/provider-state.json`; `_calibration` is never treated as a
  provider entry). Readings with `observed_at` older than **5 minutes** (or
  `null`) are `stale` — the 5-minute TTL is the upper bound for idle readings,
  not permission to skip pre-dispatch or post-unit checks.
- **Single-writer invariant:** Only the coordinator writes `.orchestration/*`
  state files (`provider-state.json`, `orchestration-checkpoint.md`,
  `orchestration-ledger.md`); workers write only to their scoped deliverable or
  output files.
- When `down_until` passes, send **one** small request as a probe. On
  success, mark the pool up and return new work to its normal lane. On
  failure, extend `down_until` and wait 15 minutes before probing again.
- Work already running on a fallback lane finishes there; only new units
  return to the primary lane.
