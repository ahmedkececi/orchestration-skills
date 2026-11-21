# Project orchestration profile example (Neon in Antigravity)

Copy this file to `.orchestration/project-profile.md` in your repository and replace the sample values with the lanes, paths and commands approved for your project. Keep only the pools you actually use — unconfigured lanes fall back automatically. Store secret values in your project's secret manager or environment variables, never in this file.

Reference the saved profile from your repository instructions (`AGENTS.md` or `CLAUDE.md`):

```markdown
## Orchestration
Read `.orchestration/project-profile.md` before delegating or switching pools.
```

| Setting | Example configuration (edit for your project) |
| --- | --- |
| Project instruction files | `AGENTS.md`, `CONTRIBUTING.md` |
| Manager | Orchestrator (Neon), or `gemini-4-neon` at `high` effort when selectable in Antigravity |
| Authorized workers | 1) **Codex pool (`codex-sub`)**: `gpt-6.2-sol` (`high`/`xhigh`) via `codex exec`, read/write code, internal data allowed.<br>2) **Claude pool (`claude-sub`)**: `Claude Opus 5.5` (`medium`/`high`) and `Claude Sonnet 5.5` (`high`, confirm exact IDs in client) via `claude -p`, read/write code, restricted data allowed.<br>3) **Antigravity/Gemini pool (`agy-sub`)**: `gemini-4-hydrogen` (`high`) via Native Swarm or `agy` for PDFs, media, screenshots and wide reading. |
| Default execution | Codex `gpt-6.2-sol` (`high`) for clear-spec coding, paired with Claude Opus (`medium`) or Claude Sonnet (`high`) so Antigravity quota stays reserved for the manager and cross-family reviews |
| Measurement data | `.orchestration/model-measurements.md` (refresh via `/update-orchestration-skills`). Override: require verified coding scores on the same cohort before swapping primary implementation lane. |
| Independent review | Fresh worker from a different model family than the author (e.g., isolated `gemini-4-neon` `high` reviews GPT/Claude edits; Claude Opus `high` or `gpt-6.2-astra` `medium` reviews Gemini/Neon edits). Same-family fallback allowed only with explicit `same-family review` label. |
| Data policy | **Public/Internal**: Antigravity, Codex and Claude pools. **Restricted/PII**: Claude pool only (or local only). **Publishable only**: metered third-party APIs (e.g., DeepSeek). |
| Workspace | Writable paths: `src/`, `tests/`, `docs/`. Read-only: `infra/prod/`, `.github/workflows/`. Branch convention: `feat/<topic>` or `fix/<topic>`. Local dev server allowed on `127.0.0.1` only. |
| Verification | Lint: `ruff check .` · Focused tests: `pytest tests/unit` · Full suite: `pytest` · Build: `npm run build` |
| Usage and spending | Check `.orchestration/provider-state.json` before delegating. **Weekly limits**: move at `85%`, stop at `90%`. **5-hour windows**: move at `90%`, stop at `95%`. Metered API cap: `$0` (subscriptions only; if enabling an API, name the env var e.g. `DEEPSEEK_API_KEY` and set a hard monthly cap). |
| Decision gates | Maintainer approval required for DB schema migrations, auth/security changes, dependency major bumps, production deploys and force-pushes. |
| Handoff | Checkpoint: `.orchestration/orchestration-checkpoint.md` · Ledger: `.orchestration/orchestration-ledger.md` · First check after transfer: `git status --short` + focused test command from checkpoint. |
| Source control | Manager reviews diffs and decides when to commit; workers never run `git commit` or `git push`. Preserve unrelated working-tree changes. |

For any new lane, check the installed runner's `--help` and run one read-only verification task before assigning file edits or batches. A credential reference may name an environment variable (such as `DEEPSEEK_API_KEY`); keep its value out of this file.
