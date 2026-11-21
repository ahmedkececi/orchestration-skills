# Collect and import model measurements

Use provider release notes and model documentation for exact model IDs and release dates. Use primary evaluation sources for measured results. Useful starting points include [Artificial Analysis model leaderboards](https://artificialanalysis.ai/leaderboards/models), [Terminal-Bench](https://www.tbench.ai/), [LiveBench](https://livebench.ai/), [ARC Prize](https://arcprize.org/leaderboard) and [Vals AI](https://www.vals.ai/). A user can also import results from a labeled in-house workload or an authorized data export. Keep sourcing and permissions with the evidence. Public lookup and local import do not require a bundled API key.

## Input shape

Pass a JSON object with one or both arrays. Every supplied row should use the listed fields.

| Array | Fields |
| --- | --- |
| `models` | `model`, `provider`, `released` (ISO date or null), `url` (official release or model documentation) |
| `measurements` | `model`, `effort`, `metric`, `cohort`, `unit`, `source`, `date` (ISO date), `value` (number), `url` (direct result or documented export source) |

Identifiers use letters, numbers, hyphens, periods, underscores, slashes, colons or plus signs. Use a canonical model ID, a stable source identifier and a cohort identifier that encodes the benchmark version and harness or scoring method. Give a data mirror the primary source's identity or omit it. Use `unspecified` for an unreported effort and keep that receipt separate from explicitly measured efforts. Supported units are `points`, `percent`, `elo`, `seconds`, `usd` and `tokens`. These are representative field names and the syntax below reads a real export a user supplies.

```sh
python3 -B scripts/refresh.py --workspace /path/to/project --input /path/to/observations.json --preview
```

For speed use `seconds-per-task` and a cohort that identifies the task mix, measurement method and harness. Put modeled estimates in a distinct metric such as `estimated-seconds-per-task`; they do not qualify as measured speed. Use the exact scoring version for a headline index. A metric may also identify a raw test such as `terminal-bench` with the test version and harness in its cohort.

## Task profiles and comparisons

- Use `coding`, `reasoning`, `accuracy` and `knowledge` for normalized workload profiles. Label the scale and reference set in the cohort. The [historical snapshot](model-measurements.md) documents its reference weights. Use raw scores directly for a matched test when a full profile is unavailable.
- To derive a profile, use all its required components under one fixed rubric, with the same version, units, harness, normalization, direction and weights for both models. Import the resulting value with the source and normalization cohort. Keep a profile unknown when a required component is missing. Scores above 100 are possible on a fixed reference scale.
- Only combine independent, comparable observations in a cohort. Do not count a test twice through a composite and its constituent test. Separate vendor reports from independent measurements unless the project explicitly accepts that evidence. Do not compare means across different cohorts or unmatched source coverage as if they were equivalent. Use matched source rows when coverage differs.
- The helper retains the latest observation per exact model, effort, metric, cohort, unit and primary source. A refresh adds or replaces supplied rows without dropping missing ones. Compare the dates before using older retained observations. To revise local measurements, import corrected source rows with the same key and an equal or later date. To reset all live observations, move the workspace Markdown aside before re-running the command.

## Scope and check an update

- For a named update, include one exact `models` record and use `--model EXACT_ID`. The helper rejects observations for other IDs, even if a source page lists related variants.
- For catalog mode, consult the [catalog workflow](catalog-workflow.md). The verified report supplies the model list. Import only benchmark rows for the returned IDs. Retain source links and explicitly report unmeasured efforts or tests.
- For a deliberate offline or custom import, leave out both scope flags and submit the user-approved observations directly. This does not mark catalog coverage as checked.
