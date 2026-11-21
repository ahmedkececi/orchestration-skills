---
name: astra-orchestration
description: >-
  Coordinate delegated work with Astra in Codex. Use for scoped worker briefs, independent review, quota-aware routing, failover and handoff across authorized model providers.
---

# Orchestration with Astra in Codex

Use this preset when Astra is the coordinator and you want to reserve its Codex allowance for architecture, difficult calls and final review.

**Manager:** Start with Astra at medium effort. Use the project profile to select the actual model, effort, runner and permissions.

**Default execution:** Send implementation to Opus medium or Sonnet high when authorized. Use Sol high for bounded overflow and raise to xhigh for an escalation. Keep broad reading in the configured Google lane.

## Establish the operating limits

1. Read project instructions and the authorized [project profile](project-profile.example.md). A runner entry identifies the exact model, effort, available tools, provider, quota pool, permitted data classes and write scope. Treat an unconfigured lane as unavailable. Resolve input capabilities against the configured endpoint and client.
2. Determine the scope of the request, definition of done and which actions need user approval. Using this skill does not grant permission to launch subprocesses, send data to a provider, buy capacity, commit, deploy or write to a live system. The client and project determine what is authorized.
3. Have the manager make the decisions, write work briefs, review artifacts and own the final synthesis. Delegate execution when permitted and worthwhile. Follow the controlling instructions if the host restricts delegation, and report what could not be staffed.
4. Before wide reads or edits, state file ownership, inputs, acceptance checks and the expected return. Use the [workflow templates](workflow-templates.md). Keep personal data, credentials and restricted material within approved lanes; sanitize delegated briefs.

## Route by the work

| Unit | Suggested lane when authorized | Evidence to request |
|---|---|---|
| Clear implementation, mechanical fixes, migrations and focused verification | Primary execution lane above | Scoped diff, exact checks, blockers |
| Open-ended debugging, product judgment or local integration | Scoped senior worker with the right tools and authorized network or service access | Minimal reproduction, evidence for the decision and a proposed fix |
| Video, audio, wide reading or long PDF intake | Hydrogen at a supported medium or high effort, or a verified multimodal worker | Structured findings with timestamps, page numbers or source links |
| Independent review | A fresh worker from a different model family. Consider Neon high for document and source checks, and a configured Astra or Claude lane for other work | Findings tied to acceptance criteria and an explicit accept or hold |
| Targeted second opinion | Neon medium, Astra medium or a qualified Mythos/Fable advisor, depending on the author and task | One bounded question, findings and uncertainty |
| Bulk extraction, classification and cleanup | A configured light lane such as Terra, Haiku or Luna. A metered worker such as DeepSeek is eligible only for the approved data and budget | Small first batch, structured output, spot checks |

Use exact IDs and effort settings supported by the installed runners. The names above are starting points for an authorized profile. On a new lane, run a small, representative unit before handing it a batch. Ask higher-effort reviewers only when the decision warrants it.

## Split, review and integrate

- Run units in parallel when their inputs and writable paths are independent. Use unambiguous ownership and an integration order. Keep dependent edits sequential and serialize runs that compete for the same local service, database or fixture.
- Ask each worker for the result, artifact or diff, checks executed, and unresolved risks. Inspect the evidence before accepting the unit. Run the applicable project checks when authorized. Include any skipped check in the final report.
- For consequential changes, give an independent reviewer the artifact and the acceptance criteria without the author's argument. Prefer a different model family and a fresh context. If independent review is unavailable, record the gap and leave a required decision pending.
- Keep a brief checkpoint before starting a large batch or when moving work. Record goal, baseline, completed work, writable paths, approved decisions, current pool state and first verification after resume. The next runner starts from artifacts and evidence.

## Manage quotas and failover

Use the runner's current status and reset times. For example, read Claude Code's usage display, Codex's status, Antigravity's quota display, or the approved metered provider's balance. Read the affected account and window. API price per task is not subscription consumption. Treat unknown quota as unknown.

| Window | Example move threshold | Example stop for new large units |
|---|---:|---:|
| Rolling or daily | 85% used | 90% used |
| Weekly | 95% used | 95% used |

Use thresholds in the project profile when specified. Let safe in-flight units finish, checkpoint before the window closes, and assign new work to pools with confirmed headroom.

| Event | Action |
|---|---|
| Brief throttle or overload | Honor the retry hint, reduce concurrency and keep retries bounded. Switch eligible new units if the lane is still constrained. |
| Per-model allowance exhausted | Check whether the rest of that pool is available, then apply the manager handoff and provider rules. |
| Shared pool exhausted | Stop starting work in that pool. Continue on an eligible independent pool, or queue until reset. |
| Wrong ID, authorization failure or expired credential | Fix the configuration or obtain authorization. A missing permission does not authorize another destination. |
| Worker fails the task | Record the failure. Narrow the brief or raise effort once where useful, then escalate or hand off from the partial artifact. |

### Choose an eligible replacement

Apply these checks in order:

1. Filter by data access, permitted write scope, required modalities and tools, spending limits and the exact model and effort the runner exposes. Confirm the quota for the replacement. For a pool outage, require a separate pool. Prefer a different provider for a shared failure. A same-provider exception needs an authorized project rule and evidence the relevant capacity is independent.
2. Read the workspace's `.orchestration/model-measurements.md` when present. Otherwise consult the [bundled measurements](../update-orchestration-skills/references/model-measurements.md) if installed alongside this skill. Use fresh, comparable evidence for the exact variants and effort levels. Compare the relevant profiles (coding, reasoning, accuracy or knowledge), not an overall index alone. Do not carry a Mythos/Fable score from one model to the other.
3. For otherwise eligible candidates, use the project profile's quality floor on each required dimension. Among equivalent options, favor spare quota and use comparable measured end-to-end task time as a tie-breaker. When a benchmark is missing, estimated or from an incompatible version, leave that comparison unknown.
4. Use the configured alternates and run a representative check if the evidence is incomplete. If only a weaker fallback is available, label the gap and add verification. Queue a high-stakes unit when the extra verification is unavailable.

**Manager handoff.** For a Codex-wide interruption, hand off to Neon in Antigravity or Mythos/Fable in Claude Code. An available Opus session can take over under the Opus preset. Continue only after the next runner reads the checkpoint, confirms its authorization, and can run the first verification.

## Refresh the measurements

Run `/update-orchestration-skills` in Claude Code or Antigravity, or `$update-orchestration-skills` in Codex. Install the [companion skill](../update-orchestration-skills/) beside this one. Its output is local to the current workspace. New models can be compared as soon as comparable data exists and become eligible for routing when the project authorizes the exact model and runner.

## Keep a short routing record

Capture the unit, model and effort, pool, reason for selection or failover, outcome and checks. Use repeated local evidence to propose changes to the user's routing profile. Keep selection, spending and data access decisions under project control.
