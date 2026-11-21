---
name: update-orchestration-skills
description: Refresh local orchestration benchmark data from current releases and sourced measurements. Use when the user invokes the update command, asks to refresh model scores, or supplies a measurement export to import.
---

# Refresh orchestration measurements

Use this procedure for an explicit refresh request. The result is one workspace file, `.orchestration/model-measurements.md`. Its scores and profile averages are available for the next routing decision in this session. The bundled skill files and upstream repository stay separate from this workspace data.

1. Identify the current workspace root. With a model argument, scope the refresh to those models. Otherwise read the authorized project profile, look for recent releases from its providers and refresh any measured variants that can be compared with its current lanes. Without a project profile, use the providers in the bundled measurement snapshot as the search scope.
2. Use the host's live search or fetch tools to verify releases in provider documentation and benchmark results at their source. Open the actual table or model result. Start with the links in the [collection guide](references/collection.md). For a user-provided export, validate its provenance and convert it to the same input format.
3. Record the exact model variant, explicit effort, benchmark version, cohort, unit, source URL and observation date. Use the same series and normalization for a comparison. Keep benchmark scores, workload profile values, reported costs and measured task time in distinct metrics. A release without benchmark data is still useful. Add the release and leave its scores unknown. Do not infer effort, transfer Mythos/Fable scores between models, scrape gated data, or use a headline index as a task profile.
4. Build the input described in the [collection guide](references/collection.md). Run the bundled script from this skill folder with the actual project root as the workspace, passing the JSON via stdin or `--input`. For a preview request, add `--preview`; otherwise write the workspace file. If the helper cannot run, report the source-linked findings and the exact missing capability. If no source can be verified, leave the last workspace snapshot in use.

   ```sh
   python3 scripts/refresh.py --workspace /path/to/project --input /path/to/observations.json
   ```

5. Report the workspace path, new models, updated measurements, gaps and which authorized lanes are now comparable. Re-read the result when continuing an orchestration session. A catalog entry does not authorize a provider, a charge, a dependency install or a change of model for active work.

On clients that expose skill slash commands, invoke `/update-orchestration-skills`. In Codex use `$update-orchestration-skills` or choose it from the skills menu.
