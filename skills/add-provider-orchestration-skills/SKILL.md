---
name: add-provider-orchestration-skills
description: Research a named model provider's official catalog and usage documentation and register it for local orchestration model discovery.
---

# Add an orchestration provider

Invoke `/add-provider-orchestration-skills PROVIDER` in Claude Code or Antigravity, or `$add-provider-orchestration-skills PROVIDER` in Codex. A provider named in the user's next message is also valid. Ask which provider if none was supplied or the name is ambiguous.

1. Find the provider's official documentation using live search. Open its current model catalog, dated release history, and usage guide. Verify an exact model ID and how a user would call it through a documented API endpoint, CLI or managed client. Check authentication, available effort or input modes, and any account or billing prerequisites. Keep provider docs separate from third-party evaluation results.
2. Follow the [provider registration format](../update-orchestration-skills/references/catalog-workflow.md#register-a-provider). Record documentation links and authentication method, using an environment variable **name** if applicable. Use the desired coverage start date, or the bundled snapshot date from the catalog plan when the user leaves it open. If a required official source cannot be verified, explain the missing piece before registering.
3. Use the helper in the adjacent [update skill](../update-orchestration-skills/) to register the provider locally. Then run `catalogs.py plan` and verify that the provider appears with the new source URLs and intended date.

```sh
python3 -B ../update-orchestration-skills/scripts/catalogs.py register --workspace /path/to/project --input provider.json
```

Report the official source links, one documented model ID, access method, call entry point and setup prerequisites. Registration adds a discovery source to `.orchestration/provider-catalogs.json`. The project profile governs whether its models can actually receive work. Store credential references only, and leave account changes, dependency installs, paid calls and runner authorization to the corresponding user instruction.

If the user also requests a named model for this provider, run the updater's single-model procedure for that model after registration. Future unnamed updates include the provider's public catalog and release history.
