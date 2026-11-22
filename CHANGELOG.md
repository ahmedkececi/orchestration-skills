# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-11-22

### Added
- **Self-calibrating pre-dispatch quota guard (`resolve_lanes.py` + all five coordinator presets):**
  - Pre-dispatch projected usage protection via `--unit-size {xs,s,m,l,xl}` and optional `--safety-margin` — blocks lanes with `projected-overflow` (`projected >= 95%` stop, e.g., an ~11% `l` unit at `89%` five-hour usage) before dispatch and deprioritizes lanes at `projected >= 90%`.
  - Post-unit EWMA burn calibration (`--record-burn`, `--burn-provider`, `--burn-model`, `--burn-effort`, `--before-5h`/`--after-5h`, `--before-weekly`/`--after-weekly`, `--reset-occurred`) stored under reserved key `_calibration` in `.orchestration/provider-state.json` (atomic writes with symlink guard and automatic window-reset skip when `after < before`), adapting automatically to each operator's subscription plan after 2–3 units.
  - Mandatory pre-dispatch and post-unit quota checks across all five coordinator presets (retaining the 5-minute TTL as the upper bound for idle readings).
- **Claude Code native plugin & marketplace support:** Added `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and 512×512 `.claude-plugin/icon.png` (passing `claude plugin validate` with zero warnings), enabling one-step installation via `/plugin install ultimate-orchestration-skills --marketplace ahmedkececi/ultimate-orchestration-skills`.
- **One-line zero-Node installer (`install.sh`):** POSIX `sh` installer supporting `--client codex|claude|antigravity`, `--preset`, `--with-provider`, `--dir`, `--ref`, `--source`, and `--dry-run`.
- **Interactive browser Quota & Lane Simulator (`docs/index.html`, live on GitHub Pages):** Zero-dependency EN/TR simulator with 1:1 parity against `resolve_lanes.py`, featuring unified `90%`/`95%` thresholds, Unit Size (`XS–XL`), EWMA plan calibration profiles, a one-click `5h 89% + Large Unit (Projected Overflow)` scenario, and a modeled Quota Runway & Token Savings Estimator.
- **Terminal demo GIF (`assets/demo.gif`)** embedded at the top of `README.md`, showcasing first-run CLI checks, deterministic quota routing, blind cross-family `BLOCKER` review, and checkpoint handoff.
- **Concrete impact metrics & OmniRoute comparison (`README.md` EN/TR):** Added a clear comparison against open-source local AI gateways/proxies (such as OmniRoute and LiteLLM) and a transparent measured + modeled impact table.
- **Live CLI model ID mapping in first-run bootstrap:** All five coordinator `SKILL.md` presets now detect and map reference model names to the live model IDs actually supported by the operator's installed CLIs/accounts when creating `.orchestration/project-profile.md`.
- **Expanded test coverage (100 total unit tests):** Added tests for unified `90%`/`95%` boundaries, `projected-overflow`, `projected-deprioritized`, EWMA convergence, pool fallback, window-reset guard, symlink/input validation, Claude Code plugin manifests/icon, `install.sh`, `docs/index.html`, and `assets/demo.gif`.

### Changed
- **Unified quota thresholds across both 5-hour and weekly windows:** Standardized all routing logic, example profiles, walkthrough fixtures (`examples/provider-state.json` `codex.weekly_pct: 91`), docs, and simulator controls to **90% move (`deprioritized`) / 95% stop (`blocked`)** for both five-hour and weekly windows.
- **Setup-first starter prompt:** Updated starter chat prompts in `README.md` and `examples/first-run.md` (EN/TR) so new users can copy-paste a single zero-placeholder prompt to check CLIs, sign in, initialize `.orchestration/`, and wait for their first task.

## [1.2.3] - 2026-11-22

### Added
- **4-step first-run CLI & `.orchestration/` bootstrap across all five coordinator presets (`astra`, `sol`, `neon`, `fable`, `opus`):** Before delegating on a fresh workspace, coordinators now detect installed worker CLIs and read-only auth status (`claude`, `codex`, `agy`), show a `CLI | Installed | Signed in` status table, ask which pools/paths/tests to enable, guide official installation (only with explicit operator approval) and interactive terminal sign-in (never pasting tokens into chat), re-verify auth, and create `.orchestration/project-profile.md` (with `<!-- orchestration-lanes:v1 -->`) and `.orchestration/provider-state.json` before starting work.
- `CLI installation and login` quick-reference section in all five `references/cli-lanes-and-ledger.md` files (covering macOS/Linux, Windows PowerShell, and SSH/device-auth sign-in) plus an optional collapsible CLI install/sign-in reference in both English and Turkish sections of `README.md`.
- Copy-paste starter chat prompts (`What to type in chat` / `Chate ne yazarak başlarsın?`) for Claude Code, Codex, and Antigravity in `README.md` and `examples/first-run.md` (English and Turkish parity).
- Onboarding invariant assertions (`First-run bootstrap`, `claude auth status`, `codex login status`, `agy auth login`) in `tests/test_skills.py`.

### Fixed
- Eliminated first-run stalls when `.orchestration/project-profile.md` or `.orchestration/provider-state.json` is missing and prevented coordinators from silently falling back past uninstalled or signed-out CLIs that the operator wants to use.

## [1.2.2] - 2026-11-22

### Added
- Automated schema and multi-role resolution test (`test_example_project_profiles_authorize_valid_lanes`) in `tests/test_skills.py` validating all five `skills/*/project-profile.example.md` files against `resolve_lanes.py`, plus 25 additional regression tests across `tests/test_resolve_lanes*.py` and `tests/test_updater.py` (89 total unit tests).

### Fixed
- **Resolver comparable-group & cross-family review logic (`resolve_lanes.py`):** Replaced all-candidate source intersection with largest comparable subset selection so a single outlier source never wipes out matched live scores; prioritized cross-family comparable groups and prevented a single live same-family lane from outranking eligible cross-family reviewers; preserved direct `review` scores when `accuracy`+`reasoning` lack matched sources; kept excluded-lane live scores and historical review formulas consistent.
- **Provider state, alias & parsing correctness (`resolve_lanes.py`):** Rejected colliding pool aliases in `provider-state.json` so `down` status cannot be silently dropped; allowed custom/registered providers in CLI `--author-family` and normalized `allowed_providers` in the Python API; preserved fresh pool headroom when a model-specific entry is an untouched all-null placeholder; fixed backtick/namespaced model parsing, malformed number continuations/signed ranges, token-boundary provider inference, case-insensitive `model`/`cohort`/`source` matching, `limit`/Markdown escaping, DEL (`0x7f`) runner rejection, and `OverflowError`/`RecursionError` handling.
- **Updater, catalog & URL hardening (`refresh.py`, `catalogs.py`, `benchmarks.py`, `collection.md`):** Canonicalized built-in provider aliases (`codex`, `claude`, `gemini`, `chatgpt`, `agy`, `antigravity`) before `official_url()` verification; strictly validated stored `catalog_audit` payloads and rejected decoy `<!-- observations:start -->` markers (including spaced variants); enforced case-insensitive merging/rendering and `points`/`seconds` profile/latency units; hardened `valid_url()` against shorthand/octal/hex IPv4, CGNAT, 6to4/Teredo, non-ASCII/ideographic dots, `.internal`/`.home.arpa`, C1/bidi controls, trailing dots, and port `0`.

## [1.2.1] - 2026-11-21

### Added
- Machine-readable `<!-- orchestration-lanes:v1 -->` worker authorization JSON blocks (`model`, `effort`, `pool`, `runner`, `roles`, and optional `restricted_data`) across all five `skills/*/project-profile.example.md` files, plus unmatched authorized-lane warnings when a configured worker has no entry in the active measurement snapshot.
- `--cohort ID` flag and cohort/source-intersection comparable scoring in `resolve_lanes.py`, plus new benchmark and quota unit test suites (`tests/test_resolve_lanes_benchmarks.py`, `tests/test_resolve_lanes_quota.py`).

### Changed
- Updated `README.md` (English and Turkish) default `npx skills add` quick-install commands to install both client coordinator options (`sol-orchestration` + `astra-orchestration` for Codex; `opus-orchestration` + `fable-orchestration` for Claude Code) alongside `update-orchestration-skills`.

### Fixed
- Require exact worker authorization from the project profile (`<!-- orchestration-lanes:v1 -->`) for resolver recommendations while keeping profile-less rankings advisory, and align example profile roles so `gpt-6.2-sol` (`xhigh`) is reserved for `reasoning` and routine `coding` compares `gpt-6.2-sol` (`high`) against `claude-opus-5-5` (`high`) within the ±3-point equivalence band.
- Keep live benchmark cohorts, units, and comparable source evidence separate, and apply measured-only latency tie-breaking only when all primary sort keys are tied.
- Treat stale quota readings as unknown, clear expired reset windows, keep expired `down_until` outages probe-only (`degraded`), and match model-specific limits against canonical IDs.
- Isolate manual installs in a fresh `mktemp -d` temporary directory and require a Claude Code subscription preflight (`CI=true claude auth status --text`) in the worker's execution environment before launching headless Claude subscription lanes.

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
