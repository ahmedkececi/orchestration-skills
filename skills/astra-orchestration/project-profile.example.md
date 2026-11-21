# Project orchestration profile example (Astra in Codex)

Copy this file to `.orchestration/project-profile.md` in your repository and replace the sample values with the lanes, paths and commands approved for your project. Keep the pools you use and list their approved worker configurations below. Store secret values in your project's secret manager or environment variables, never in this file.

Reference the saved profile from your repository instructions (`AGENTS.md` or `CLAUDE.md`):

```markdown
## Orchestration
Read `.orchestration/project-profile.md` before delegating or switching pools.
```

| Setting | Example configuration (edit for your project) |
| --- | --- |
| Project instruction files | `AGENTS.md`, `CONTRIBUTING.md` |
| Manager | `gpt-6.2-astra` at `medium` effort via Codex (`codex -m gpt-6.2-astra -c model_reasoning_effort=medium`) |
| Authorized workers | 1) **Claude pool (`claude-sub`)**: `Claude Opus 5.5` (`medium`/`high`) and `Claude Sonnet 5.5` (`high`, confirm exact IDs in client) via `claude -p`, read/write code, restricted data allowed.<br>2) **Codex pool (`codex-sub`)**: `gpt-6.2-sol` (`high`/`xhigh`) via `codex exec`, read/write code, internal data allowed. *(Add Gemini/Antigravity or DeepSeek lanes here if authorized.)* |
| Default execution | Claude Opus (`medium` via `claude -p`) first to preserve Codex headroom, then Codex `gpt-6.2-sol` (`high` via `codex exec`) as overflow/fallback |
| Measurement data | `.orchestration/model-measurements.md` (refresh via `$update-orchestration-skills`). Override: require verified coding scores on the same cohort before swapping primary implementation lane. |
| Independent review | Fresh worker from a different model family than the author (e.g., Codex `gpt-6.2-sol` reviews Claude edits; Claude Opus `high` reviews Codex edits). Same-family fallback allowed only with explicit `same-family review` label. |
| Data policy | **Public/Internal**: Codex and Claude pools. **Restricted/PII**: Claude pool only (or local only). **Publishable only**: metered third-party APIs (e.g., DeepSeek). |
| Workspace | Writable paths: `src/`, `tests/`, `docs/`. Read-only: `infra/prod/`, `.github/workflows/`. Branch convention: `feat/<topic>` or `fix/<topic>`. Local dev server allowed on `127.0.0.1` only. |
| Restricted paths | Paths excluded from external/non-Claude runners (e.g., `.env*`, `secrets/`, `data/pii/`). Strip secrets from every brief regardless of destination. |
| Verification | Lint: `ruff check .` · Focused tests: `pytest tests/unit` · Full suite: `pytest` · Build: `npm run build` |
| Usage and spending | Check `.orchestration/provider-state.json` before delegating. **Weekly limits**: move at `85%`, stop at `90%`. **5-hour windows**: move at `90%`, stop at `95%`. Metered API cap: `$0` (subscriptions only; if enabling an API, name the env var e.g. `DEEPSEEK_API_KEY` and set a hard monthly cap). |
| Decision gates | Maintainer approval required for DB schema migrations, auth/security changes, dependency major bumps, production deploys and force-pushes. |
| External actions | Forbidden for workers (`git push`, package publish, external API mutations, live DB migrations, destructive deletes outside writable paths); coordinator + explicit operator approval only. |
| Handoff | Checkpoint: `.orchestration/orchestration-checkpoint.md` · Ledger: `.orchestration/orchestration-ledger.md` · First check after transfer: `git status --short` + focused test command from checkpoint. |
| Source control | Manager reviews diffs and decides when to commit; workers never run `git commit` or `git push`. Preserve unrelated working-tree changes. |

For any new lane, check the installed runner's `--help` and run one read-only verification task before assigning file edits or batches. A credential reference may name an environment variable (such as `DEEPSEEK_API_KEY`); keep its value out of this file.

## Machine-readable worker authorization

`resolve_lanes.py` reads this block from the project's saved profile. Replace
the sample entries with workers you have explicitly approved. Use an exact
catalog model ID and an effort verified in the selected runner. Set `pool` to
the matching quota pool. `runner` describes the approved launcher and the
resolver only reports it. List the permitted `roles` from `coding`,
`reasoning`, `accuracy`, `knowledge`, and `review`. Set
`"restricted_data": true` only if your project allows that worker to receive
restricted data. Omitting it keeps restricted data out of that lane.

Include only worker configurations suitable for delegation. Keep workspace
access, data handling and billing rules in the profile above. A profile
without this block produces an advisory ranking. An empty array explicitly
authorizes zero workers.

<!-- orchestration-lanes:v1 -->
```json
[
  {"model": "claude-opus-5-5", "effort": "medium", "pool": "claude", "runner": "claude -p", "roles": ["coding"], "restricted_data": true},
  {"model": "claude-opus-5-5", "effort": "high", "pool": "claude", "runner": "claude -p", "roles": ["coding", "reasoning", "review"], "restricted_data": true},
  {"model": "claude-sonnet-5-5", "effort": "high", "pool": "claude", "runner": "claude -p", "roles": ["coding"], "restricted_data": true},
  {"model": "gpt-6.2-sol", "effort": "high", "pool": "codex", "runner": "codex exec", "roles": ["coding", "review"]},
  {"model": "gpt-6.2-sol", "effort": "xhigh", "pool": "codex", "runner": "codex exec", "roles": ["reasoning"]}
]
```
