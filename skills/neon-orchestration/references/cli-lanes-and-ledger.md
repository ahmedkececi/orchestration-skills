# CLI lanes, model notes, and routing ledger — Neon orchestration

Reference companion to [SKILL.md](../SKILL.md).

## CLI lanes & Antigravity Swarm

**Native Swarm (Gemini workers in Antigravity).** Use `swarm{action:"title"}`
once per batch, `swarm{action:"add", name:..., model:"gemini-4-hydrogen-high"|"gemini-4-neon-high"|"gemini-4-neon-medium", workspace:"inherit"|"share"|"branch", brief:...}`
to assign work, `read_board` / `swarm_wait` to collect results, and `swarm{action:"kill"}`
to close finished workers before posting an `@`-free `[done]` closeout. Do not
spawn writers with `inherit` when modifying overlapping files.

**Claude Code CLI (`claude -p`).** Claude delegate lanes (`Opus` `medium` /
`high`, `Sonnet` `high`, `Haiku` `high` — CLI aliases `opus`, `sonnet`, `haiku`
mapping to catalog IDs `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`)
run via `claude -p` on the Claude subscription (`env -u ANTHROPIC_API_KEY`,
check `claude auth status`, never `--dangerously-skip-permissions`): `--model opus --effort
<medium|high> --permission-mode acceptEdits --no-session-persistence "…"
< /dev/null` (or `--tools Read,Glob,Grep --permission-mode dontAsk` for
read-only reviews).

**Codex (GPT).** GPT lanes run through `codex exec`:
`codex exec --skip-git-repo-check -m <model> -c model_reasoning_effort=<medium|high|xhigh> -s <read-only|workspace-write> -o <report_file> "<prompt>" < /dev/null`
Execution lanes run on `-m gpt-6.2-sol` (`high` default, `xhigh` for higher
requirements, reasoning-/science-heavy sensitive work and escalation); pass
`-m gpt-6.2-astra` (`medium`) for peer questions and Google-authored reviews,
`-m gpt-6.1-terra` (`medium`) for cleanup qualification/batches, and `-m gpt-6-luna`
(`high`) for large cleanup jobs. Check the selected model and client's requirements in the [Codex model guide](https://learn.chatgpt.com/docs/models). Use the project's approved sandbox for the task.

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

The [bundled model measurements](../../update-orchestration-skills/references/model-measurements.md) contain the benchmark scores, task profiles, averages, and observed or estimated task times. Read `.orchestration/model-measurements.md` in the current workspace first if it exists. The bundled archive is the historical basis for these defaults.

Run `/update-orchestration-skills` in Claude Code or Antigravity, or `$update-orchestration-skills` in Codex, to refresh the workspace data. Install the [refresh skill](../../update-orchestration-skills/) alongside this preset. A refresh changes the measurement evidence available to routing; the project profile still governs authorization, pool access and model IDs. Use each model's exact measured variant and effort, and compare results only on matching task profiles and compatible source cohorts. Missing measurements remain unknown.

## Routing ledger

Append one line per delegation to `.orchestration/orchestration-ledger.md`: date, task type,
lane, effort, attempts, verification result, escalation if any. When the same
task type fails on a lane three times, or passes cleanly on a lighter lane
three times, propose a change to the routing table to the operator.
Optionally, to qualify `gpt-6.2-sol` for standard code debugging in your
project, record three distinct standard debugging jobs on `gpt-6.2-sol` (`high`
by default, `xhigh` only under hard rule 4), log verification and escalation
for each, and use the ledger evidence to propose a routing update.
