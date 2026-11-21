## Summary

<!-- Describe what changed and why. Link any related issue. -->

## Verification

<!-- List the commands you ran locally and their outcomes. -->

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 -B skills/update-orchestration-skills/scripts/refresh.py --workspace . --input examples/measurements.json --preview > /dev/null`

## Checklist

- [ ] Changes are free of credentials, account identifiers, and private logs/source material.
- [ ] User-facing documentation changes are updated in both the English and Turkish sections of `README.md`.
- [ ] Any updated benchmark numbers include exact model ID, effort, test edition, date, and primary source link (missing scores remain `-`).
- [ ] Any changes to shared templates or policy conventions are consistent across all affected presets.
