# Contributing

The most useful reports show where an installation, quota handoff or model selection went differently than expected.

- For an installation, routing or handoff issue, include the client and version, preset, the smallest prompt that reproduces it, and the expected and observed result. Use the [workflow feedback template](https://github.com/ahmedkececi/ultimate-orchestration-skills/issues/new?template=workflow-feedback.md).
- For a script bug, broken link or schema validation failure, use the [bug report template](https://github.com/ahmedkececi/ultimate-orchestration-skills/issues/new?template=bug-report.md).
- For a benchmark correction, name the exact model, effort, test edition and date. Link the original result and mention the harness if known. Leave missing measurements unfilled.
- For a new preset or provider integration, include the supported client or runner, setup steps, and a small example that other contributors can reproduce. Explain where it uses existing policy and where it needs a change.

## Local validation

Before opening a pull request, run the zero-dependency test suite and the offline preview smoke check from the repository root (Python 3.9+):

```sh
python3 -m unittest discover -s tests -v
python3 -B skills/update-orchestration-skills/scripts/refresh.py \
  --workspace . --input examples/measurements.json --preview > /dev/null
```

Keep examples free of credentials, account identifiers and private source material. Check that any change to user-facing instructions includes matching updates in both English and Turkish sections of [README.md](README.md).
