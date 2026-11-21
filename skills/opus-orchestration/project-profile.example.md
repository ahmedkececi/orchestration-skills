# Project orchestration profile example (Opus in Claude Code)

Copy this file to `.orchestration/project-profile.md` in your repository and replace the sample values with the lanes, paths and commands approved for your project. Keep only the pools you actually use — unconfigured lanes fall back automatically. Store secret values in your project's secret manager or environment variables, never in this file.

Reference the saved profile from your repository instructions (`CLAUDE.md` or `AGENTS.md`):

```markdown
## Orchestration
Read `.orchestration/project-profile.md` before delegating or switching pools.
```

| Setting | Example configuration (edit for your project) |
| --- | --- |
| Project instruction files | `CLAUDE.md`, `CONTRIBUTING.md` |
| Manager | `Claude Opus 5.5` at `high` or `xhigh` effort in Claude Code (confirm exact model ID in client) |
| Authorized workers | 1) **Codex pool (`codex-sub`)**: `gpt-6.2-sol` (`high`/`xhigh`) via `codex exec`, read/write code, internal data allowed.<br>2) **Claude pool (`claude-sub`)**: `Claude Sonnet 5.5` (`high`) and `Claude Opus 5.5` (`medium`, confirm exact IDs in client) via `claude -p` or Claude Agent tool, read/write code, restricted data allowed. *(Add Gemini/Antigravity or DeepSeek lanes here if authorized.)* |
| Default execution | Codex `gpt-6.2-sol` (`high` via `codex exec`) first to preserve Claude headroom, then Claude Sonnet (`high`) or Opus (`medium`) for restricted data and fallback |
| Measurement data | `.orchestration/model-measurements.md` (refresh via `/update-orchestration-skills`). Override: require verified coding scores on the same cohort before swapping primary implementation lane. |
| Independent review | Fresh worker from a different model family than the author (e.g., Codex `gpt-6.2-sol` or `gpt-6.2-astra` reviews Claude edits; Claude Opus/Sonnet reviews Codex edits). Same-family fallback allowed only with explicit `same-family review` label. |
| Data policy | **Public/Internal**: Claude and Codex pools. **Restricted/PII**: Claude pool only (or local only). **Publishable only**: metered third-party APIs (e.g., DeepSeek). |
| Workspace | Writable paths: `src/`, `tests/`, `docs/`. Read-only: `infra/prod/`, `.github/workflows/`. Branch convention: `feat/<topic>` or `fix/<topic>`. Local dev server allowed on `127.0.0.1` only. |
| Restricted paths | Paths excluded from external/non-Claude runners (e.g., `.env*`, `secrets/`, `data/pii/`). Strip secrets from every brief regardless of destination. |
| Verification | Lint: `ruff check .` · Focused tests: `pytest tests/unit` · Full suite: `pytest` · Build: `npm run build` |
| Usage and spending | Check `.orchestration/provider-state.json` before delegating. **Weekly limits**: move at `85%`, stop at `90%`. **5-hour windows**: move at `90%`, stop at `95%`. Metered API cap: `$0` (subscriptions only; if enabling an API, name the env var e.g. `DEEPSEEK_API_KEY` and set a hard monthly cap). |
| Decision gates | Maintainer approval required for DB schema migrations, auth/security changes, dependency major bumps, production deploys and force-pushes. |
| External actions | Forbidden for workers (`git push`, package publish, external API mutations, live DB migrations, destructive deletes outside writable paths); coordinator + explicit operator approval only. |
| Handoff | Checkpoint: `.orchestration/orchestration-checkpoint.md` · Ledger: `.orchestration/orchestration-ledger.md` · First check after transfer: `git status --short` + focused test command from checkpoint. |
| Source control | Manager reviews diffs and decides when to commit; workers never run `git commit` or `git push`. Preserve unrelated working-tree changes. |

For any new lane, check the installed runner's `--help` and run one read-only verification task before assigning file edits or batches. A credential reference may name an environment variable (such as `DEEPSEEK_API_KEY`); keep its value out of this file.
