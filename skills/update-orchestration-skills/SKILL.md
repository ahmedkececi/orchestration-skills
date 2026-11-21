---
name: update-orchestration-skills
description: Discover models released after the orchestration presets' reference versions, or refresh a single named model. Use for verified model releases, benchmark updates and local measurement imports.
---

# Refresh orchestration model data

Run `/update-orchestration-skills` in Claude Code or Antigravity, or `$update-orchestration-skills` in Codex. Work in the user's current project. Read the [catalog workflow](references/catalog-workflow.md) and the [measurement guide](references/collection.md). Write verified results to `.orchestration/model-measurements.md`.

## With a model name

A name supplied in the invocation or in the user's next message selects **only that model**. Resolve the name to the provider's exact documented ID and release, then search primary benchmark sources for that exact variant and effort. Ask for clarification if multiple distinct IDs fit. Skip the broad catalog scan. Use the complete benchmark checklist below even if the release has no published scores.

```sh
python3 -B scripts/refresh.py --workspace /path/to/project --model EXACT_ID --input observations.json
```

## Without a model name

1. Run `python3 -B scripts/catalogs.py plan --workspace /path/to/project`. It lists the official sources, reference versions from the orchestration presets, and any workspace providers added by the companion skill.
2. Read both the provider catalog and release history for each provider. Follow applicable pagination, tabs and dated links. Verify reference-model dates and newer release IDs from the official sources. Record the IDs observed in each source. Mark missing pages or unclear dates rather than claiming full coverage.
3. Run `catalogs.py verify` with the report format in the [catalog workflow](references/catalog-workflow.md). Run the complete benchmark checklist below only for the newer model IDs returned by the verifier.
4. Save the releases, benchmark rows and catalog audit. Omit `--input` only when the verifier returned no newer models.

```sh
python3 -B scripts/refresh.py --workspace /path/to/project --catalog-report scan.json --input observations.json
```

## Check the complete benchmark suite

For each verified model, identify its documented effort levels and any explicitly labeled benchmark variants. Use `unspecified` when no effort can be verified. Read the [benchmark checklist](references/benchmark-suite.json) and search for **every test column** for each variant. Start with the evaluator's model breakdown and follow the individual evaluation links for fields absent from the summary. Check exact test editions and harnesses. An index or a related test does not fill a missing raw result.

Submit one `benchmark_checks` row per model and effort, even if every result is unavailable. List only sources actually inspected. Add numeric observations for verified results. The helper rejects incomplete checklists and displays a literal `-` for missing values. See the [measurement guide](references/collection.md#full-benchmark-checklist).

## Verification and result

Use the host's live source tools. Open primary sources, distinguish release dates from account rollout dates, and match benchmark version and exact effort. Keep estimates, raw scores and profile values separate. If the sources conflict, record the gap. Use a reported ID only for the actual release it identifies and never transfer a score between Mythos and Fable.

Add `--preview` when requested. Read the resulting workspace file or preview and report the new model IDs, source links, observed scores, missing scores and any incomplete catalog coverage. When the host cannot access a source, retain prior measurements and label the gap. A documented model becomes eligible for routing through the project's separately authorized runner, data scope and budget.

For an explicit user-supplied measurement export, use the [import procedure](references/collection.md). To register a new provider for future scans, use [add-provider-orchestration-skills](../add-provider-orchestration-skills/).
