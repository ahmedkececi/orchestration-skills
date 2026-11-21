# Project orchestration profile example

Use this as a copyable starting point for the project profile that your repository instructions or session brief references. Fill only the lanes you can use. Keep the real profile in a project-approved location. Store credentials in the project's existing secret mechanism.

| Setting | Example or decision to fill in |
| --- | --- |
| Project instruction files | Applicable repository instructions and any project-specific contribution guide |
| Manager | Sol at xhigh effort |
| Authorized workers | Provider, account or pool label, exact model ID, effort, runner, available tools and allowed input classes |
| Default execution | Use Opus medium or Sonnet high for execution when that keeps capacity available in the manager's pool. Sol high is eligible for bounded work when Codex has headroom. Escalate difficult units separately. |
| Measurement data | `.orchestration/model-measurements.md` or the bundled historical snapshot. Record required task profiles, quality floors and any authorized per-lane overrides. |
| Independent review | An authorized fresh worker from a different model family, with a same-family fallback policy if appropriate |
| Data policy | Which providers can see public, internal or restricted data and which classes must remain local |
| Workspace | Writeable paths, worktree or branch conventions, allowed network access and rules for starting local services |
| Verification | Format or lint commands, focused tests, full suite and build where applicable |
| Usage and spending | How to read each pool's allowance, reset time, thresholds and any explicitly approved API budget |
| Decision gates | Changes that require a maintainer, plus any production, security and irreversible operations reserved for explicit approval |
| Handoff | Checkpoint path, owner and first verification step after a transfer |
| Source control | Who stages or commits, branch and pull-request conventions, and how to preserve another worker's changes |

For a new lane, verify the installed runner's current help and test an authorized read-only task before assigning writes or a batch. A credential reference may identify the secret by name. Keep its value out of this profile.
