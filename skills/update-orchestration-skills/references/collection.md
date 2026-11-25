# Collect and import model measurements

Use provider release notes and model documentation for exact model IDs and release dates. Use primary evaluation sources for measured results. Useful starting points include [Artificial Analysis model leaderboards](https://artificialanalysis.ai/leaderboards/models), [Terminal-Bench](https://www.tbench.ai/), [LiveBench](https://livebench.ai/), [ARC Prize](https://arcprize.org/leaderboard) and [Vals AI](https://www.vals.ai/). A user can also import results from a labeled in-house workload or an authorized data export. Keep sourcing and permissions with the evidence. Public lookup and local import do not require a bundled API key.

## Input shape

Pass a JSON object with the applicable arrays. Every supplied row should use the listed fields.

| Array | Fields |
| --- | --- |
| `models` | `model`, `provider`, `released` (ISO date or null), `url` (official release or model documentation) |
| `measurements` | `model`, `effort`, `metric`, `cohort`, `unit`, `source`, `date` (ISO date), `value` (number), `url` (direct result or documented export source) |
| `benchmark_checks` | `model`, `effort`, `date` (ISO lookup date), `checked` (all metric IDs in the checklist), `sources` (URLs actually inspected, or an empty array when none could be read) |

Identifiers use letters, numbers, hyphens, periods, underscores, slashes, colons or plus signs. Use a canonical model ID, a stable source identifier and a cohort identifier that encodes the benchmark version and harness or scoring method. Give a data mirror the primary source's identity or omit it. Use `unspecified` for an unreported effort and keep that receipt separate from explicitly measured efforts. Supported units are `points`, `percent`, `elo`, `seconds`, `usd` and `tokens`. These are representative field names and the syntax below reads a real export a user supplies.

```sh
python3 -I scripts/refresh.py --workspace /path/to/project --input /path/to/observations.json --preview
```

For speed use `seconds-per-task` (or `s-per-task` / `latency-seconds`) with `unit: "seconds"` and a cohort that identifies the task mix, measurement method and harness. Put modeled estimates in a distinct metric such as `estimated-seconds-per-task` (also `unit: "seconds"`); they do not qualify as measured speed. Use the exact scoring version for a headline index. For suite tests, use the exact versioned metric IDs from [benchmark-suite.json](benchmark-suite.json) (such as `terminal-bench-4.0`) with the harness and scoring cohort in `cohort`; other custom raw tests may use a descriptive metric ID with their version and harness in `cohort`.

## Task profiles and comparisons

- Use `coding`, `reasoning`, `accuracy`, `knowledge` (or `knowledge-work`), and `review` for normalized workload profiles, always with `unit: "points"`. Label the scale and reference set in the cohort. The [historical snapshot](model-measurements.md) documents its reference weights. Use raw scores directly for a matched test when a full profile is unavailable.
- To derive a profile, use all its required components under one fixed rubric, with the same version, units, harness, normalization, direction and weights for both models. Import the resulting value with the source and normalization cohort. Keep a profile unknown when a required component is missing. Scores above 100 are possible on a fixed reference scale.
- Only combine independent, comparable observations in a cohort. Do not count a test twice through a composite and its constituent test. Separate vendor reports from independent measurements unless the project explicitly accepts that evidence. Do not compare means across different cohorts or unmatched source coverage as if they were equivalent. Use matched source rows when coverage differs.
- The helper retains the latest observation per exact model, effort, metric, cohort, unit and primary source (matched case-insensitively so mixed-case duplicates such as `High` and `high` cannot collide). A refresh adds or replaces supplied rows without dropping missing ones. Compare the dates before using older retained observations. To revise local measurements, import corrected source rows with the same key and an equal or later date. To reset all live observations, move the workspace Markdown aside before re-running the command.

## Scope and check an update

- For a named update, include one exact `models` record and use `--model EXACT_ID`. Named lookups have no release-date cutoff. The helper rejects observations for other IDs, even if a source page lists related variants.
- For catalog mode, consult the [catalog workflow](catalog-workflow.md). Present the verified list and wait for the user's choices. Add one `--select` argument per chosen ID. Import benchmark checks and observations only for those choices.
- For a provider registration with selected models, use `--provider-entry provider.json` and repeat `--model EXACT_ID` for every chosen ID. Preview before registering. Writing the result requires the provider to be registered in the workspace. Report any unverified efforts or tests.
- For a deliberate offline or custom import, leave out both scope flags and submit the user-approved observations directly. This does not mark catalog coverage as checked.


## Full benchmark checklist

Use the exact metric IDs, versions and units from [benchmark-suite.json](benchmark-suite.json). It mirrors the raw test columns in the [historical archive](model-measurements.md). Check FrontierCode, Terminal-Bench, Terminal-Bench-Science, CritPt, HLE-Diamond, both Omniscience measures, Briefcase, AutomationBench and GDP.pdf. Start from the exact model and effort page and the [Artificial Analysis evaluation methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking). Use a benchmark owner's result only when it documents the same test edition and identifies the evaluated model and effort. Keep separate harnesses or cohorts in separate observations.

Record one complete checklist for every known model and effort variant in a live refresh. Use `unspecified` when no known effort is documented. Include only URLs actually read in `sources`, and keep the direct evidence links in the numeric measurement rows. An empty `measurements` array is valid when the checklist was attempted and no score was verified. The Markdown matrix renders every test column with a literal `-` wherever no matching verified observation exists. A real zero remains a numeric result.

Report the aggregate index, time, cost or workload profiles separately when sourced. Leaving a profile unknown does not remove the raw test results. A similar benchmark or an overall index cannot substitute for a missing test score. If a test was unavailable now, retain any earlier verified measurements for the same variant and mark the reason for the gap in the refresh summary.
