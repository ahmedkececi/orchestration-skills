# Fable Orchestration — CLI Lanes, Model Notes & Routing Ledger

## CLI lanes

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

To deterministically rank authorized models from live `.orchestration/model-measurements.md` and `.orchestration/provider-state.json` instead of relying only on static baseline tables, the coordinator can run `python3 -B <updater-skill-dir>/scripts/resolve_lanes.py --workspace . --role <coding|reasoning|accuracy|knowledge|review>` (adding `--author-family <family>` for cross-family review and `--restricted-data` when restricted-data rules apply).

## Routing ledger

Append one line per delegation to `.orchestration/orchestration-ledger.md`: date, task type,
lane, effort, attempts, verification result, escalation if any, `scope_drift` (`yes|no`), and `first_pass_ok` (`yes|no`). When the same
task type fails on a lane three times, or passes cleanly on a lighter lane
three times, propose a change to the routing table to the operator.
Optionally, to qualify `gpt-6.2-sol` for standard code debugging in your
project, record three distinct standard debugging jobs on `gpt-6.2-sol` (`high`
by default, `xhigh` only under hard rule 4), log verification and escalation
for each, and use the ledger evidence to propose a routing update.
