---
name: update-orchestration-skills
description: List models released after the orchestration presets' reference versions and refresh the models the user chooses. Use for verified releases, benchmark updates and local measurement imports.
---

# Refresh orchestration model data

Run `/update-orchestration-skills` in Claude Code or Antigravity, or `$update-orchestration-skills` in Codex. Work in the user's current project. Read the [catalog workflow](references/catalog-workflow.md) and the [measurement guide](references/collection.md). Write verified results to `.orchestration/model-measurements.md`.

## With a model name

A name supplied in the invocation or in the user's next message selects **only that model**. Resolve the name to the provider's exact documented ID and release, then search primary benchmark sources for that exact variant and effort. Ask for clarification if multiple distinct IDs fit. Skip the broad catalog scan. Named lookups have no release-date cutoff. Use the complete benchmark checklist below even if the release has no published scores.

```sh
python3 -B scripts/refresh.py --workspace /path/to/project --model EXACT_ID --input observations.json
```

## Without a model name

1. Run `python3 -B scripts/catalogs.py plan --workspace /path/to/project`. It lists official sources, reference versions and any providers added to the workspace.
2. Read each provider's model catalog and release history. Verify the reference dates and newer model IDs using the [catalog workflow](references/catalog-workflow.md), then run `catalogs.py verify`. Cover relevant pages and dates and identify any gaps.
3. Show the verified newer models as a numbered list with provider, exact model ID, release date and source. Report any incomplete coverage. If the list is empty, report that and stop. Ask **which models the user wants to add**. Accept one, several or explicit all. Stop and wait for their answer before any benchmark lookup or workspace write. Keep the verified report for the next step.
4. Use the checklist below only for the chosen IDs. If the selection is unclear, clarify it. On cancellation, finish without importing. Pass one `--select` flag per chosen model. An explicit choice of all means passing each verified ID from the displayed list.

```sh
python3 -B scripts/refresh.py --workspace /path/to/project --catalog-report scan.json \
  --select EXACT_ID --input observations.json
```

## Check the complete benchmark suite

For each verified model, identify its documented effort levels and any explicitly labeled benchmark variants. Use `unspecified` when no effort can be verified. Read the [benchmark checklist](references/benchmark-suite.json) and search for **every test column** for each variant. Start with the evaluator's model breakdown and follow the individual evaluation links for fields absent from the summary. Check exact test editions and harnesses. An index or a related test does not fill a missing raw result.

Submit one `benchmark_checks` row per model and effort, even if every result is unavailable. List only sources actually inspected. Add numeric observations for verified results. The helper rejects incomplete checklists and displays a literal `-` for missing values. See the [measurement guide](references/collection.md#full-benchmark-checklist).

## Verification and result

Use the host's live source tools. Open primary sources, distinguish release dates from account rollout dates, and match benchmark version and exact effort. Keep estimates, raw scores and profile values separate. If the sources conflict, record the gap. Use a reported ID only for the actual release it identifies and never transfer a score between Mythos and Fable.

Add `--preview` when requested. Read the resulting workspace file or preview and report the new model IDs, source links, observed scores, missing scores and any incomplete catalog coverage. When the host cannot access a source, retain prior measurements and label the gap. A documented model becomes eligible for routing through the project's separately authorized runner, data scope and budget.

For an explicit user-supplied measurement export, use the [import procedure](references/collection.md). To register a new provider for future scans, use [add-provider-orchestration-skills](../add-provider-orchestration-skills/).

For deterministic lane ranking, run `python3 -B scripts/resolve_lanes.py --workspace /path/to/project --role coding` from the updater skill directory. The resolver uses workspace measurements, provider state and the authorization block in `.orchestration/project-profile.md` (or `--profile PATH`). A missing block gives an advisory ranking with no recommended lane. Use `--providers` to narrow the pool list, `--author-family` for independent review, `--restricted-data` for restricted inputs, and `--format json` for machine-readable output.

Use `--cohort ID` to select a compatible live benchmark cohort. When multiple
live cohorts are applicable and no cohort is selected, the resolver warns
and compares the historical evidence. Estimated task times do not break ties.
