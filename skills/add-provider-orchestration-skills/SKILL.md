---
name: add-provider-orchestration-skills
description: List a provider's documented models, ask which to add, and register the provider and selected model benchmarks in the user's project. Use when onboarding or adding a new model provider for orchestration.
argument-hint: "<PROVIDER>"
---

# Add an orchestration provider

Invoke `/add-provider-orchestration-skills PROVIDER` in Claude Code or Antigravity, or `$add-provider-orchestration-skills PROVIDER` in Codex. A provider named in the user's next message is also valid. Ask which provider if none was supplied or the name is ambiguous.

This skill depends on the sibling [update-orchestration-skills](../update-orchestration-skills/) skill. Before running any script below, locate `update-orchestration-skills` relative to **this installed skill's directory** (not the user's workspace root) and set `<updater-skill-dir>` to that resolved path. If `update-orchestration-skills` is not installed alongside this skill, stop and instruct the user to install it first before continuing.

## Show the choices

1. Use live search to open the provider's official model catalog, dated release history, and usage guide. Identify the API, CLI or managed client that serves the models. Check model availability, supported effort and inputs, authentication, billing, and any account restrictions. Give source links and flag incomplete coverage.
2. Show a numbered list of models the provider documents as available on the relevant surface, with exact model IDs and any access conditions. If the catalog is large, group by family and include a link to the full official list. Ask **which models the user wants to add**, accepting one, several or explicit all. Any model chosen from the linked list must still be verified. A model scoped explicitly by the user already counts as a choice.
3. End the step and wait for an explicit response. Keep the provider draft and model list in the session. Do not register the provider, write measurements, or start benchmark lookups until the selection is made. A request to register only the provider skips benchmark collection. Cancellation leaves the project as it was.

## Add the selection

1. Fill the [provider registration format](../update-orchestration-skills/references/catalog-workflow.md#register-a-provider) with the checked documentation, a supported call entry point and a credential variable name where applicable. Use the requested coverage start date or the bundled snapshot date. Stop if a required official source could not be verified.
2. For each selected model, apply the updater's [full benchmark checklist](../update-orchestration-skills/references/collection.md#full-benchmark-checklist). Collect official model records and the checks for every documented effort into one observation file. The updater shows missing verified scores as `-`. Pass one `--model` flag for each selected canonical ID. Validate with `--preview` before registering the provider.

   ```sh
   python3 -I <updater-skill-dir>/scripts/refresh.py --workspace /path/to/project \
     --provider-entry provider.json --model EXACT_ID --input observations.json --preview
   ```

3. For a requested preview, show the proposed provider record and benchmark matrix. Otherwise register the provider if it is new, verify it appears in `catalogs.py plan`, then rerun the checked refresh command without `--preview` to write the selected models. For a provider-only request, run registration without the refresh step.

   ```sh
   python3 -I <updater-skill-dir>/scripts/catalogs.py register --workspace /path/to/project --input provider.json
   ```

Report the models added, score gaps, provider documentation and setup prerequisites. Registration stores the discovery source in `.orchestration/provider-catalogs.json`. The updater stores model measurements in `.orchestration/model-measurements.md`. The project profile still governs runner authorization, credentials, private data and budget.
