# Opus Orchestration — CLI Lanes, Model Notes & Routing Ledger

## CLI lanes

### CLI installation and login

Before authorizing worker pools on a fresh setup, check which CLIs are installed and signed in, ask the operator which pools they want to enable, install missing wanted CLIs **only with explicit operator approval**, and pause for interactive sign-in in the operator's terminal before re-verifying auth:

- **Claude Code (`claude`)**
  - Detect & check auth: `command -v claude` and `CI=true claude auth status --text`
  - Install (with approval): `npm install -g @anthropic-ai/claude-code`
  - Sign in (user terminal): run `claude` then `/login` (or `claude auth login`)
- **Codex (`codex`)**
  - Detect & check auth: `command -v codex` and `codex login status`
  - Install (with approval): `npm install -g @openai/codex`
  - Sign in (user terminal): `codex login` (or `codex login --device-auth` over SSH)
- **Antigravity (`agy`)**
  - Detect & check CLI: `command -v agy` and `agy --help` (plus active Antigravity session)
  - Install (with approval): macOS/Linux `curl -fsSL https://antigravity.google/cli/install.sh | bash` · Windows PowerShell `irm https://antigravity.google/cli/install.ps1 | iex`
  - Sign in (user terminal): `agy auth login` or launch `agy` (`agy auth login --no-browser` over SSH)

Never ask the operator to paste API keys, OAuth tokens, or passwords into chat. Only authorize verified, signed-in, operator-approved lanes in `.orchestration/project-profile.md`.

### Claude Code subscription preflight

A headless Claude lane is available only after you verify that the worker will
use the intended active Claude subscription. Run
`CI=true claude auth status --text` in the worker’s directory with the same
executable, environment, and settings profile. Check the effective provider,
account, and sign-in method. Use the client's `/status` in that environment if
you need more detail. See [Claude Code authentication precedence](https://code.claude.com/docs/en/authentication#authentication-precedence).

Removing `ANTHROPIC_API_KEY` alone cannot establish subscription billing.
Bearer tokens (`ANTHROPIC_AUTH_TOKEN`), `apiKeyHelper`, custom endpoints
(`ANTHROPIC_BASE_URL`), and managed gateway or cloud settings can change the
effective provider or credentials. Keep credential values out of briefs and
reports. If you cannot confirm the subscription, leave this lane unavailable
and use an authorized fallback. Follow the operator’s managed settings and
billing policy. Keep workers non-interactive and retain normal permissions.
Claude CLI aliases such as `opus`, `sonnet` and `haiku` must resolve to the
model approved in the profile. Never use `--dangerously-skip-permissions`.

Headless invocation examples after the preflight. Use the exact model and
effort accepted by the worker’s configured Claude client.

- Read-only review (`Opus` `high`):
  `CI=true claude -p --model opus --effort high --tools Read,Glob,Grep --permission-mode dontAsk --no-session-persistence "<prompt>" < /dev/null`
- Scoped execution (`Opus` `medium`):
  `CI=true claude -p --model opus --effort medium --permission-mode acceptEdits --no-session-persistence "<prompt>" < /dev/null`

### Codex and other runners

**Codex (GPT).** GPT lanes run through `codex exec` with explicit model, effort, and sandbox settings. Execution lanes run on
`-m gpt-6.2-sol` (this policy's default); pass `-m gpt-6.2-astra` for second
opinions, `-m gpt-6.1-terra` for cleanup qualification/batches and `-m gpt-6-luna`
for large cleanup jobs. Sol defaults to `high`. Use `xhigh` for higher-requirement, reasoning-
or science-heavy sensitive work and escalation. Check the selected model and client's requirements in the [Codex model guide](https://learn.chatgpt.com/docs/models).

**Gemini.** Use the Gemini runner configured in the project profile (such as
Gemini CLI headless `gemini -m <model> -p "<prompt>" --output-format json` on
the subscription account, reading the `response` field, or headless
Antigravity `agy -p "<brief>" --model "<id>"`). Use `gemini-4-hydrogen` at
`high` effort for media, wide reading and search (with `gemini-4-neon` `high`
permitted as a video/audio backup only), and `gemini-4-neon` (`high` review /
`medium` second eye) with model and effort pinned.

**DeepSeek.** There is no first-party agent CLI. Use an OpenAI-compatible
client pointed at `https://api.deepseek.com`, or an Anthropic-compatible
harness pointed at `https://api.deepseek.com/anthropic`, with model
`deepseek-flash` (catalog ID `deepseek-v4.1-flash-1017`). Ramp concurrency
rather than opening at full width.

When assigning fleet lanes, stamp the model, effort and concurrency per lane
in the spec so the launch is mechanical and no routing decision happens at
spawn time. Confirm each recipe once against the installed CLI version before
a fleet depends on it.

## Model notes

The [bundled model measurements](../../update-orchestration-skills/references/model-measurements.md) contain the benchmark scores, task profiles, averages, and observed or estimated task times. Read `.orchestration/model-measurements.md` in the current workspace first if it exists. The bundled archive is the historical basis for these defaults.

Run `/update-orchestration-skills` in Claude Code or Antigravity, or `$update-orchestration-skills` in Codex, to refresh the workspace data. Install the [refresh skill](../../update-orchestration-skills/) alongside this preset. A refresh changes the measurement evidence available to routing; the project profile still governs authorization, pool access and model IDs. Use each model's exact measured variant and effort, and compare results only on matching task profiles and compatible source cohorts. Missing measurements remain unknown.

To rank lanes, run `resolve_lanes.py` from the installed updater skill with
`--workspace . --role` and the relevant task role. Its default authorization
source is the JSON block in [the project's profile](../project-profile.example.md#machine-readable-worker-authorization).
Pass `--profile PATH` to inspect another profile. Without an authorization
block the output is advisory and has no recommended lane. `--providers`
narrows the pool list, and `--cohort ID` selects a compatible live benchmark
cohort when multiple live cohorts exist. Add `--author-family` for review and
`--restricted-data` when the unit touches restricted data. The project still
controls what each worker can access and which tools it can use.

For pre-dispatch overflow protection and automatic plan calibration, pass
`--unit-size <xs|s|m|l|xl>` (and optional `--safety-margin <1.0..3.0>`) before
dispatching each unit, and run `--record-burn` right after the unit completes:

```sh
# 1. Pre-dispatch ranking with projected overflow guard (90% move / 95% stop)
python3 -B skills/update-orchestration-skills/scripts/resolve_lanes.py \
  --workspace . --role coding --unit-size l \
  --state .orchestration/provider-state.json

# 2. Post-unit burn calibration (updates live after-% and _calibration EWMA)
python3 -B skills/update-orchestration-skills/scripts/resolve_lanes.py \
  --workspace . --state .orchestration/provider-state.json \
  --record-burn --burn-provider codex --burn-model gpt-6.2-sol --burn-effort high \
  --unit-size l --before-5h 72 --after-5h 83 --before-weekly 40 --after-weekly 44
```

If a window resets mid-unit (`after < before`, or when `--reset-occurred` is
passed), `--record-burn` skips the EWMA update for that reset window while
still recording the live `after` percentage. Do not dispatch to any lane flagged
`projected-overflow` (`projected >= 95%`); route to a healthy equivalent
fallback or split the unit into smaller pieces.

## Routing ledger

Append one line per delegation to `.orchestration/orchestration-ledger.md`: date, task type,
lane, effort, attempts, verification result, escalation if any, `scope_drift` (`yes|no`), and `first_pass_ok` (`yes|no`). When the same
task type fails on a lane three times, or passes cleanly on a lighter lane
three times, propose a change to the routing table to the operator.
Optionally, to qualify `gpt-6.2-sol` for standard code debugging in your
project, record three distinct standard debugging jobs on `gpt-6.2-sol` (`high`
by default, `xhigh` only under hard rule 4), log verification and escalation
for each, and use the ledger evidence to propose a routing update.
