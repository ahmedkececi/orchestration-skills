---
name: sol-orchestration
description: "Sol-led multi-agent orchestration for Codex. Use when coordinating delegated work, assigning reviewers, balancing provider quotas, or handing off a session."
---

# Sol orchestration

Use Sol at xhigh effort as the main-loop preference, where your account and client support it. Reserve the manager for managing well-specified delivery while conserving the coordinator's allowance. Resolve model aliases, effort names and permissions against the current client and project profile before dispatch.

## Start the session

1. Read the repository's applicable instructions and any active handoff. Identify the requested result, allowed actions, data constraints and verification commands.
2. Read the project's orchestration profile if one exists. Use [project-profile.example.md](project-profile.example.md) to create one or to identify the minimum configuration for this session. Treat unverified providers as unavailable for dispatch.
3. Identify the available workers, model families and quota pools. Check their actual capabilities for file writes, tools, network, local services and media.
4. Agree on acceptance criteria before assigning work. Convert each result into a unit with a single owner and a way to verify it.

## Coordinate and route

The manager plans, writes briefs, handles decisions, reviews evidence and accepts results. Give routine implementation, extraction and cleanup to available authorized workers. The manager can inspect a diff and run verification. When a required lane is unavailable, use an eligible fallback or record the blocked unit. Keep progressing on independent units.

| Work | First route to try | Dispatch rule |
| --- | --- | --- |
| Scoped implementation, tests, migrations or refactors from a written design | Claude Opus at medium, then Codex Sol at high | Specify interfaces, paths, boundaries and exact checks. Escalate effort after diagnosing the first lane's failure. |
| Hard debugging or a tool-dependent task | An approved worker with the required environment, often Claude Opus | Pass the failure, a minimal reproducer and the allowed tools. Keep production actions behind the project's authorization. |
| Large PDFs, screenshots, audio, video or wide search | An approved Gemini ingestion worker, such as Hydrogen if available | Split by source or page range. Request quotations or observations with page numbers, timestamps or links as appropriate. |
| Repeatable low-risk bulk work | A lower-cost approved lane, such as Luna, Haiku or an explicitly authorized metered provider | Pilot on a representative slice. Validate output shape and quality before increasing volume. |
| Contested judgment or high-impact review | An authorized reviewer outside the author's model family | Give a fresh reviewer the artifact, acceptance criteria and essential context. Keep its report separate from manager verification. |

- Use Claude Opus or Sonnet for steady execution volume when available. Keep same-pool Sol runs small enough to preserve room for acceptance and handoff.
- Favor explicit, step-by-step briefs with named paths and checks. Use a stronger reviewer for ambiguous architecture or source-sensitive claims.
- Use Astra as a same-family peer for multi-source synthesis when needed. Use a fresh Claude or Gemini worker for independent review of GPT-authored changes.

Use a higher-effort lane for a difficult finding that survives a scoped retry. Prefer a familiar, capable lane for time-sensitive work. Check data, tool access, permissions and quota again whenever a unit moves between lanes.

## Write and run briefs

Use the [brief and handoff templates](workflow-templates.md). Include the goal, relevant inputs and their allowed recipients, owned files or output paths, required constraints, checks, stop conditions and return format.

- Keep one writer per file or isolate writers in worktrees. Use separate output paths for search, research and review shards. Integrate after prerequisite results are accepted.
- Pin the provider, model and effort when supported. Confirm the intended authentication mode and any metered use. Give read-only workers read-only access. Limit writes to the assigned workspace.
- Share only the material the lane is authorized to receive. Keep credentials out of briefs, checkpoints and logs. Preserve unrelated work and never route around safety, access, data or billing restrictions.
- Require the worker to report the result, files or evidence, verification and any blocker. Ask for commands and artifacts sufficient to reproduce important findings. A claim of completion starts the manager's review.

## Verify and accept

1. Inspect the full change or artifact against the brief. Check boundaries and compatibility with related work.
2. Run the project's actual verification commands on the integrated result. Sample representative inputs in bulk jobs. For sourced work, check material claims at the original sources.
3. Match review depth to the impact of the decision. If a cross-family review is required and unavailable, record the gap and wait on that acceptance gate. If it is optional, clearly label any same-family review that you use.
4. Return each defect with its evidence and a concrete acceptance condition. Recheck after the fix. Commit accepted changes only when the project or user authorizes it.

## Handle limits and handoffs

Use live usage and reset indicators rather than treating model names as independent pools. Track shared allowance and model-specific limits separately. If the project has no thresholds, consider shifting new volume at 85% used, reserving the last 10% of a short window for closure, and pausing routine work at 95% of a weekly allowance. Apply percentages only when the client reports the corresponding usage.

| Signal | Response |
| --- | --- |
| Transient rate limit or overloaded service | Respect the retry hint, lower concurrency and retry once if the work can safely resume. |
| Rolling or daily window exhausted | Record the reset and reroute eligible work to a healthy independent pool. |
| Weekly cap or depleted balance | Mark the pool unavailable, queue affected units and identify the next reset or authorized alternative. |
| Invalid model, authentication, permission or context error | Fix or report the actual cause. Preserve the original authorization and data boundaries. |
| Worker failure or partial write | Inspect existing output, preserve useful changes and restart the remaining work from a clear checkpoint. |

If this manager cannot continue, try Codex Astra for a judgment-heavy handoff if Codex is available, then Claude Opus or Antigravity Neon in that order, subject to current availability and enabled project lanes. Hand off the goal, decisions, active units, artifacts, unresolved decisions, known limits and exact next verification steps. Ask the incoming manager to verify the state independently before accepting pending work.
