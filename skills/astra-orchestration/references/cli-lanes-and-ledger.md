# Astra Orchestration — CLI Lanes, Model Notes & Routing Ledger

## CLI lanes

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

**Codex (GPT).** GPT delegates run through `codex exec`:
`codex exec --skip-git-repo-check -m <model> -c model_reasoning_effort=<medium|high|xhigh> -s <read-only|workspace-write> -o <report_file> "<prompt>" < /dev/null`
Execution lanes run on `-m gpt-6.2-sol` (`high` default, `xhigh` for higher
requirements, reasoning-/science-heavy sensitive work and escalation); pass
`-m gpt-6.1-terra` (`medium`) for cleanup qualification/batches and `-m gpt-6-luna`
(`high`) for large cleanup jobs. Check the selected model and client's requirements in the [Codex model guide](https://learn.chatgpt.com/docs/models).

**Gemini.** Use the Gemini runner configured in the project profile, such
as headless Antigravity (`agy -p "<brief>" --model "<id>"`). Pin the
model and effort using the runner's supported options. Give Hydrogen
bounded briefs and limit review permissions to the checks required.

**DeepSeek.** Use an OpenAI- or Anthropic-compatible client with the model
`deepseek-flash` and the endpoint authorized in your project profile. Set
`max_tokens >= 2048` and ramp concurrency gradually. Use publishable material
only.

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

## Routing ledger

Append one line per delegation to `.orchestration/orchestration-ledger.md`: date, task type,
lane, effort, attempts, verification result, escalation if any, `scope_drift` (`yes|no`), and `first_pass_ok` (`yes|no`). When the same
task type fails on a lane three times, or passes cleanly on a lighter lane
three times, propose a change to the routing table to the operator.
Optionally, to qualify `gpt-6.2-sol` for standard code debugging in your
project, record three distinct standard debugging jobs on `gpt-6.2-sol` (`high`
by default, `xhigh` only under hard rule 4), log verification and escalation
for each, and use the ledger evidence to propose a routing update.
