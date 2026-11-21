# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-11-21

### Added
- Deterministic offline lane resolver (`skills/update-orchestration-skills/scripts/resolve_lanes.py`) ranking authorized lanes from live `.orchestration/model-measurements.md` (or bundled snapshot) and `.orchestration/provider-state.json` by role (`coding`, `reasoning`, `accuracy`, `knowledge`, `review`), cross-family `--author-family` preference, `--restricted-data` filtering, quota thresholds, and 5-minute staleness TTL — plus sample state fixture (`examples/provider-state.json`) and zero-dependency tests (`tests/test_resolve_lanes.py`).
- Enriched 7-field `.orchestration/provider-state.json` schema (`status`, `down_until`, `limit`, `five_hour_pct`, `weekly_pct`, `resets_at`, `observed_at`), 5-minute staleness/TTL policy, and coordinator single-writer invariant for `.orchestration/*` across all five coordinator presets.
- Independent review `BLOCKER` / `NIT` severity classification, max-2-review-rounds circuit breaker, high-stakes tie-breaker rule, and Test Integrity Invariant across all five coordinator presets and `workflow-templates.md`.
- Class F (`Timeout / Hung lane`) error classification with non-interactive CLI budgets (`< /dev/null`, `CI=true`), Class E per-session/cooldown counter reset, Compaction Recovery checklist, and External Action Gate (`git push`, package publish, external API mutations, live DB migrations, and out-of-scope destructive deletes forbidden for workers).
- Structured `scope_drift` (`yes|no`) and `first_pass_ok` (`yes|no`) routing ledger fields, checkpoint `Depends on` column, `Restricted paths` and `External actions` rows in all five `project-profile.example.md` files, and an offline lane-resolution walkthrough in `examples/first-run.md`.

### Changed
- Enhanced `tests/test_skills.py` to validate `#fragment` heading anchors on local Markdown links (both same-file and cross-file) and assert all v1.2.0 orchestration invariants across all five coordinator presets.
- Updated `README.md` (English and Turkish), `skills/update-orchestration-skills/SKILL.md`, and `.github/workflows/ci.yml` with deterministic lane resolution, safety guardrails, and resolver smoke/unit checks.

## [1.1.0] - 2026-11-21

### Added
- Lossless progressive-disclosure `references/` files (`delegation-and-verification.md`, `quota-and-failover.md`, `cli-lanes-and-ledger.md`) across all five coordinator presets (`astra`, `sol`, `neon`, `fable`, `opus`), loaded on demand via a mandatory trigger table in each `SKILL.md`.
- Zero-dependency `tests/test_skills.py` integrity suite validating YAML frontmatter across all seven skills, lean `SKILL.md` line budgets and `references/` links for all five coordinator presets, local relative Markdown link resolution across documentation and skills, and byte-identical `workflow-templates.md` parity.
- Live GitHub Actions CI status badge and progressive-disclosure copy guidance (English and Turkish) in `README.md`.

### Changed
- Trimmed all five coordinator `SKILL.md` entry files to under 450 lines while preserving every original rule, CLI flag, model ID, failover ladder, and exception verbatim across `SKILL.md` and `references/`.
- Upgraded `.github/workflows/ci.yml` to Node 24 actions (`actions/checkout@v6`, `actions/setup-python@v6`), expanded the runner matrix to Python 3.9 (`ubuntu-24.04`), 3.12 (`ubuntu-latest`), and 3.13 (`ubuntu-latest`), and included `tests/test_skills.py` in syntax compilation checks.

## [1.0.1] - 2026-11-21

### Added
- Zero-dependency `unittest` suite (`tests/`) and GitHub Actions CI workflow (`.github/workflows/ci.yml`) testing Python 3.9 and 3.12.
- Open-source community templates: `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/bug-report.md`, `.github/ISSUE_TEMPLATE/config.yml`, and `CHANGELOG.md`.
- Concrete filled-in examples, `.orchestration/project-profile.md` save path, and `CLAUDE.md`/`AGENTS.md` wiring instructions in all `project-profile.example.md` files.
- Workspace files, `.gitignore` snippet, FAQ, prerequisites, manual/Antigravity copy-paste install commands, and expanded coordinator selection table in both English and Turkish sections of `README.md`.

### Changed
- Standardized quota thresholds across all five coordinator presets (weekly: 85% move / 90% stop; five-hour: 90% move / 95% stop) and consolidated all workspace runtime artifacts under `.orchestration/`.
- Aligned `skills/*/workflow-templates.md` with the 4-line worker return contract (`STATUS` / `RESULT` / `EVIDENCE` / `NOT DONE`), valid Markdown tables, and `.orchestration/orchestration-checkpoint.md`.
- Updated `examples/first-run.md` so the offline preview command filters to the live workspace section and matches actual `refresh.py --preview` table formatting and checkpoint layout.
- Tightened YAML frontmatter descriptions, fixed cross-preset routing/consistency bugs, and cleaned private-setup leftovers across all six `SKILL.md` files.
- Hardened `catalogs.py`, `benchmarks.py`, and `refresh.py` input validation (case-insensitive provider matching, strict public HTTPS URL validation, ISO date error handling, atomic file permissions, duplicate-key rejection, and benchmark unit checks).

## [1.0.0] - 2026-11-21

### Added
- Five portable coordinator orchestration presets (`astra-orchestration`, `sol-orchestration`, `neon-orchestration`, `fable-orchestration`, `opus-orchestration`) for Codex, Antigravity, and Claude Code.
- Live benchmark refresh skill (`update-orchestration-skills`) with bundled historical snapshot, benchmark checklist, and zero-dependency Python 3.9+ helper scripts (`benchmarks.py`, `catalogs.py`, `refresh.py`).
- Provider onboarding skill (`add-provider-orchestration-skills`) for registering additional model catalogs in `.orchestration/provider-catalogs.json`.
- Offline fixture walkthrough (`examples/first-run.md`, `examples/measurements.json`), bilingual English/Turkish `README.md`, `CONTRIBUTING.md`, MIT `LICENSE`, and workflow feedback issue template.
