"""Zero-dependency unit and CLI tests for resolve_lanes.py."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skills" / "update-orchestration-skills" / "scripts"
EXAMPLE_STATE = REPO_ROOT / "examples" / "provider-state.json"
EXAMPLE_MEASUREMENTS = REPO_ROOT / "examples" / "measurements.json"

sys.path.insert(0, str(SCRIPTS_DIR))
import resolve_lanes  # noqa: E402


def run_script(script_name, *args):
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPTS_DIR / script_name), *args],
        capture_output=True,
        text=True,
    )


def make_candidate(
    model,
    effort="high",
    pool="claude",
    family="claude",
    *,
    coding=None,
    reasoning=None,
    accuracy=None,
    knowledge=None,
    latency_s=None,
    source="historical",
):
    return {
        "model": model,
        "effort": effort,
        "pool": pool,
        "family": family,
        "provider_label": pool,
        "profiles": {
            "coding": coding,
            "reasoning": reasoning,
            "accuracy": accuracy,
            "knowledge": knowledge,
        },
        "review_override": None,
        "index": None,
        "latency_s": latency_s,
        "source": source,
    }


def fresh_state(now_iso="2026-11-21T15:57:00Z", **overrides):
    base = {
        "status": "up",
        "down_until": None,
        "limit": None,
        "five_hour_pct": 20,
        "weekly_pct": 30,
        "resets_at": None,
        "observed_at": now_iso,
    }
    base.update(overrides)
    return base


def authorized_lane(model, effort, pool, *, roles=("coding",), restricted_data=False):
    return {
        "model": model,
        "effort": effort,
        "pool": pool,
        "runner": f"{pool} runner",
        "roles": list(roles),
        "restricted_data": restricted_data,
    }


def profile_text(*lanes):
    return "# Project profile\n\n<!-- orchestration-lanes:v1 -->\n\n```json\n" + json.dumps(lanes) + "\n```\n"


class NormalizationAndParsingTests(unittest.TestCase):
    def test_provider_and_family_alias_normalization(self):
        self.assertEqual(resolve_lanes.normalize_pool("Anthropic / Claude"), "claude")
        self.assertEqual(resolve_lanes.normalize_pool("anthropic"), "claude")
        self.assertEqual(resolve_lanes.normalize_pool("OpenAI / Codex"), "codex")
        self.assertEqual(resolve_lanes.normalize_pool("chatgpt"), "codex")
        self.assertEqual(resolve_lanes.normalize_pool("Google / agy"), "gemini")
        self.assertEqual(resolve_lanes.normalize_pool("gemini"), "gemini")
        self.assertEqual(resolve_lanes.normalize_pool("DeepSeek"), "deepseek")
        self.assertEqual(resolve_lanes.normalize_pool("xai"), "xai")

        self.assertEqual(resolve_lanes.normalize_family("codex"), "openai")
        self.assertEqual(resolve_lanes.normalize_family("chatgpt"), "openai")
        self.assertEqual(resolve_lanes.normalize_family("gemini"), "google")
        self.assertEqual(resolve_lanes.normalize_family("agy"), "google")
        self.assertEqual(resolve_lanes.normalize_family("anthropic"), "claude")
        self.assertEqual(resolve_lanes.normalize_family("claude"), "claude")
        self.assertEqual(resolve_lanes.normalize_family("deepseek"), "deepseek")

    def test_parse_iso_utc_supports_z_suffix_and_offsets_on_python_39(self):
        dt_z = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")
        self.assertEqual(dt_z, datetime(2026, 11, 21, 16, 0, 0, tzinfo=timezone.utc))
        dt_offset = resolve_lanes.parse_iso_utc("2026-11-21T19:00:00+03:00")
        self.assertEqual(dt_offset, dt_z)
        with self.assertRaises(ValueError):
            resolve_lanes.parse_iso_utc("not-a-timestamp")

    def test_parse_bundled_historical_routing_reference(self):
        text = resolve_lanes.BUNDLED_MEASUREMENTS.read_text(encoding="utf-8")
        candidates = resolve_lanes.parse_historical_candidates(text)
        self.assertEqual(len(candidates), 20)

        by_key = {(c["model"], c["effort"]): c for c in candidates}
        neon_xhigh = by_key[("gemini-4-neon", "xhigh")]
        self.assertEqual(neon_xhigh["pool"], "gemini")
        self.assertEqual(neon_xhigh["family"], "google")
        self.assertEqual(neon_xhigh["profiles"]["coding"], 96.0)
        self.assertEqual(neon_xhigh["latency_s"], 1290.0)

        astra_high = by_key[("gpt-6.2-astra", "high")]
        self.assertEqual(astra_high["pool"], "codex")
        self.assertEqual(astra_high["family"], "openai")
        self.assertEqual(astra_high["profiles"]["coding"], 95.0)
        self.assertEqual(astra_high["latency_s"], 357.0)

        # En-dash missing accuracy must parse cleanly as None.
        neon_med = by_key[("gemini-4-neon", "medium")]
        self.assertIsNone(neon_med["profiles"]["accuracy"])
        self.assertIsNone(resolve_lanes.role_score(neon_med, "review"))

        # DeepSeek parenthetical effort parses cleanly.
        ds = by_key[("deepseek-flash", "max")]
        self.assertEqual(ds["pool"], "deepseek")
        self.assertEqual(ds["profiles"]["coding"], 58.0)

    def test_parse_profile_averages_fallback_table(self):
        md = """
# Synthetic Measurements

## Profile averages

| Model / effort | Coding | Reasoning | Accuracy | Knowledge work |
| --- | ---: | ---: | ---: | ---: |
| opus-5.5/high | 81.00 (n=3, 81.00–81.00, 0.00) | 72.00 (n=4) | 55.00 (n=4) | 85.00 (n=5) |
| neon/medium | 84.00 (n=1, AA only) | 78.00 (n=1) | — (n=0) | 84.00 (n=1) |
"""
        candidates = resolve_lanes.parse_historical_candidates(md)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["pool"], "claude")
        self.assertEqual(candidates[0]["profiles"]["coding"], 81.0)
        self.assertEqual(candidates[1]["pool"], "gemini")
        self.assertIsNone(candidates[1]["profiles"]["accuracy"])

    def test_parse_workspace_observations_and_merge(self):
        obs = {
            "models": [
                {"model": "claude-opus-6", "provider": "Anthropic", "released": "2026-11-21", "url": "https://anthropic.com/"},
                {"model": "gpt-6.2-astra", "provider": "OpenAI", "released": "2026-11-19", "url": "https://openai.com/"},
            ],
            "benchmark_checks": [],
            "measurements": [
                {"model": "claude-opus-6", "effort": "high", "metric": "coding", "cohort": "v1", "unit": "points", "source": "aa", "date": "2026-11-21", "value": 98, "url": "https://example.com/"},
                {"model": "claude-opus-6", "effort": "high", "metric": "seconds-per-task", "cohort": "v1", "unit": "seconds", "source": "aa", "date": "2026-11-21", "value": 310, "url": "https://example.com/"},
                {"model": "gpt-6.2-astra", "effort": "high", "metric": "coding", "cohort": "v1", "unit": "points", "source": "aa", "date": "2026-11-21", "value": 99, "url": "https://example.com/"},
            ],
        }
        md = (
            resolve_lanes.BUNDLED_MEASUREMENTS.read_text(encoding="utf-8")
            + "\n<!-- workspace-measurements:v1 -->\n"
            + "<!-- observations:start -->\n```json\n"
            + json.dumps(obs, indent=2)
            + "\n```\n<!-- observations:end -->\n"
        )
        hist = resolve_lanes.parse_historical_candidates(md)
        ws = resolve_lanes.parse_workspace_observations(md)
        merged = resolve_lanes.merge_candidates(hist, ws)

        by_key = {(c["model"], c["effort"]): c for c in merged}
        self.assertIn(("claude-opus-6", "high"), by_key)
        self.assertEqual(by_key[("claude-opus-6", "high")]["pool"], "claude")
        self.assertEqual(by_key[("gpt-6.2-astra", "high")]["profiles"]["coding"], 95.0)
        report = resolve_lanes.resolve_lanes(merged, {}, cohort="v1")
        by_key = {(c["model"], c["effort"]): c for c in report["ranked"]}
        self.assertEqual(by_key[("claude-opus-6", "high")]["score"], 98.0)
        self.assertEqual(by_key[("claude-opus-6", "high")]["latency_s"], 310.0)
        self.assertEqual(by_key[("gpt-6.2-astra", "high")]["score"], 99.0)
        self.assertEqual(by_key[("gpt-6.2-astra", "high")]["source"], "workspace")


class ProviderStateEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.now = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")

    def test_down_until_active_and_expired(self):
        raw = {
            "anthropic": fresh_state(status="down", down_until="2026-11-21T17:00:00Z", limit="5h window"),
            "openai": fresh_state(status="down", down_until="2026-11-21T15:30:00Z", limit="5h window"),
            "google": fresh_state(status="down", down_until=None, limit="outage"),
        }
        states, warnings = resolve_lanes.parse_provider_state(raw, self.now, stale_minutes=45)
        self.assertEqual(warnings, [])
        self.assertTrue(states["claude"]["excluded"])
        self.assertEqual(states["claude"]["effective_state"], "down")
        self.assertTrue(states["gemini"]["excluded"])
        self.assertEqual(states["gemini"]["effective_state"], "down")
        # Cooldown expired: block normal work while allowing a recovery probe.
        self.assertTrue(states["codex"]["excluded"])
        self.assertTrue(states["codex"]["probe_due"])
        self.assertEqual(states["codex"]["effective_state"], "probe-only")

    def test_quota_move_and_stop_thresholds_and_headroom(self):
        raw = {
            "claude": fresh_state(five_hour_pct=90, weekly_pct=40),   # 5h move -> deprioritized, headroom 10
            "codex": fresh_state(five_hour_pct=25, weekly_pct=85),    # weekly move -> deprioritized, headroom 15
            "gemini": fresh_state(five_hour_pct=95, weekly_pct=40),   # 5h stop -> excluded
            "deepseek": fresh_state(five_hour_pct=10, weekly_pct=90), # weekly stop -> excluded
        }
        states, _ = resolve_lanes.parse_provider_state(raw, self.now, stale_minutes=45)

        self.assertFalse(states["claude"]["excluded"])
        self.assertTrue(states["claude"]["deprioritized"])
        self.assertEqual(states["claude"]["headroom"], 10.0)

        self.assertFalse(states["codex"]["excluded"])
        self.assertTrue(states["codex"]["deprioritized"])
        self.assertEqual(states["codex"]["headroom"], 15.0)

        self.assertTrue(states["gemini"]["excluded"])
        self.assertEqual(states["gemini"]["effective_state"], "stopped")

        self.assertTrue(states["deepseek"]["excluded"])
        self.assertEqual(states["deepseek"]["effective_state"], "stopped")

    def test_stale_ttl_and_legacy_schema_without_crashing(self):
        self.assertEqual(resolve_lanes.DEFAULT_STALE_MINUTES, 5)
        raw = {
            "claude": fresh_state(observed_at="2026-11-21T15:50:00Z"),  # 10 min old -> stale
            "codex": {"status": "up", "down_until": None, "limit": None},  # legacy 3-field -> stale, unknown headroom
            "gemini": fresh_state(observed_at="2026-11-21T15:57:00Z"),  # 3 min old -> fresh
        }
        states, warnings = resolve_lanes.parse_provider_state(
            raw, self.now, stale_minutes=resolve_lanes.DEFAULT_STALE_MINUTES
        )
        self.assertTrue(states["claude"]["stale"])
        self.assertTrue(states["codex"]["stale"])
        self.assertIsNone(states["codex"]["headroom"])
        self.assertFalse(states["gemini"]["stale"])
        self.assertEqual(len(warnings), 2)

    def test_invalid_provider_state_values_rejected(self):
        with self.assertRaises(ValueError):
            resolve_lanes.parse_provider_state({"claude": fresh_state(weekly_pct=True)}, self.now, 45)
        with self.assertRaises(ValueError):
            resolve_lanes.parse_provider_state({"claude": fresh_state(five_hour_pct=120)}, self.now, 45)
        with self.assertRaises(ValueError):
            resolve_lanes.parse_provider_state({"claude": fresh_state(status="paused")}, self.now, 45)

    def test_python_api_rejects_boolean_and_negative_stale_minutes(self):
        for bad_ttl in (True, False, -1, -45, 1.5, "45"):
            with self.subTest(stale_minutes=bad_ttl):
                with self.assertRaisesRegex(ValueError, "stale_minutes"):
                    resolve_lanes.parse_provider_state({}, self.now, stale_minutes=bad_ttl)
                with self.assertRaisesRegex(ValueError, "stale_minutes"):
                    resolve_lanes.resolve_from_paths(workspace=REPO_ROOT, stale_minutes=bad_ttl)


class EquivalenceAndRankingTests(unittest.TestCase):
    def setUp(self):
        self.now = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")

    def test_equivalence_band_prefers_healthy_then_higher_headroom_then_score_then_latency(self):
        candidates = [
            make_candidate("top-deprioritized", pool="codex", family="openai", coding=96, latency_s=200),
            make_candidate("equiv-low-headroom", pool="claude", family="claude", coding=95, latency_s=100),
            make_candidate("equiv-high-headroom-slow", pool="gemini", family="google", coding=94, latency_s=900),
            make_candidate("equiv-high-headroom-fast", pool="gemini", family="google", coding=94, latency_s=400),
            make_candidate("below-lane", pool="gemini", family="google", coding=92, latency_s=150),
            make_candidate("unmeasured-lane", pool="deepseek", family="deepseek", coding=None, latency_s=100),
        ]
        raw_state = {
            "codex": fresh_state(weekly_pct=87, five_hour_pct=20),   # deprioritized, headroom 13
            "claude": fresh_state(weekly_pct=60, five_hour_pct=40),  # healthy, headroom 40
            "gemini": fresh_state(weekly_pct=30, five_hour_pct=20),  # healthy, headroom 70
            "deepseek": fresh_state(weekly_pct=None, five_hour_pct=None),  # healthy, unknown headroom
        }
        states, warnings = resolve_lanes.parse_provider_state(raw_state, self.now, 45)
        res = resolve_lanes.resolve_lanes(
            candidates, states, role="coding", state_loaded=True, state_warnings=warnings
        )
        ranked_models = [row["model"] for row in res["ranked"]]
        self.assertEqual(
            ranked_models,
            [
                "equiv-high-headroom-fast",
                "equiv-high-headroom-slow",
                "equiv-low-headroom",
                "top-deprioritized",
                "below-lane",
                "unmeasured-lane",
            ],
        )
        by_model = {row["model"]: row for row in res["ranked"]}
        self.assertEqual(by_model["equiv-high-headroom-fast"]["tier"], "equivalent")
        self.assertEqual(by_model["top-deprioritized"]["tier"], "equivalent")
        self.assertIn("deprioritized", by_model["top-deprioritized"]["flags"])
        self.assertEqual(by_model["below-lane"]["tier"], "below (+1 verification)")
        self.assertIn("below (+1 verification)", by_model["below-lane"]["flags"])
        self.assertEqual(by_model["unmeasured-lane"]["tier"], "unmeasured")
        self.assertIn("unmeasured", by_model["unmeasured-lane"]["flags"])

    def test_review_cross_family_priority_and_same_family_flag(self):
        candidates = [
            make_candidate("google-top", pool="gemini", family="google", accuracy=84, reasoning=87, knowledge=90),
            make_candidate("openai-strong", pool="codex", family="openai", accuracy=60, reasoning=92, knowledge=83),
            make_candidate("claude-equiv", pool="claude", family="claude", accuracy=65, reasoning=77, knowledge=84),
            make_candidate("partial-no-knowledge", pool="deepseek", family="deepseek", accuracy=70, reasoning=70, knowledge=None),
            make_candidate("missing-acc", pool="gemini", family="google", accuracy=None, reasoning=80, knowledge=84),
        ]
        raw_state = {
            "gemini": fresh_state(weekly_pct=40, five_hour_pct=30),
            "codex": fresh_state(weekly_pct=87, five_hour_pct=25),   # deprioritized
            "claude": fresh_state(weekly_pct=58, five_hour_pct=42),  # healthy
            "deepseek": fresh_state(weekly_pct=None, five_hour_pct=None),
        }
        states, _ = resolve_lanes.parse_provider_state(raw_state, self.now, 45)

        # Author family = google -> cross-family (claude, codex, deepseek) must rank before google!
        res = resolve_lanes.resolve_lanes(
            candidates, states, role="review", author_family="google", state_loaded=True
        )
        ranked = res["ranked"]
        self.assertEqual(ranked[0]["model"], "claude-equiv")  # healthy equivalent beats deprioritized openai-strong
        self.assertEqual(ranked[1]["model"], "openai-strong")
        self.assertEqual(ranked[2]["model"], "partial-no-knowledge")  # 0.6*70 + 0.4*70 = 70.0
        self.assertEqual(ranked[2]["score"], 70.0)
        self.assertEqual(ranked[3]["model"], "google-top")
        self.assertTrue(ranked[3]["same_family"])
        self.assertIn("same-family", ranked[3]["flags"])
        self.assertEqual(ranked[4]["model"], "missing-acc")
        self.assertEqual(ranked[4]["tier"], "unmeasured")
        self.assertIn("same-family", ranked[4]["flags"])

    def test_restricted_data_and_providers_allowlist_and_model_specific_limit(self):
        candidates = [
            make_candidate("Fable 5.2", effort="medium", pool="claude", family="claude", coding=85),
            make_candidate("Opus 5.5", effort="high", pool="claude", family="claude", coding=81),
            make_candidate("gpt-6.2-astra", effort="high", pool="codex", family="openai", coding=95),
        ]
        raw_state = {
            "claude": fresh_state(weekly_pct=30, five_hour_pct=20),
            "fable-5.2": fresh_state(status="down", down_until="2026-11-21T18:00:00Z", limit="model cap"),
            "codex": fresh_state(weekly_pct=20, five_hour_pct=20),
        }
        states, _ = resolve_lanes.parse_provider_state(raw_state, self.now, 45)
        lanes = resolve_lanes.parse_authorized_lanes(profile_text(
            authorized_lane("claude-fable-5-2", "medium", "claude", restricted_data=True),
            authorized_lane("claude-opus-5-5", "high", "claude", restricted_data=True),
            authorized_lane("gpt-6.2-astra", "high", "codex"),
        ))
        res = resolve_lanes.resolve_lanes(
            candidates, states, role="coding", authorized_lanes=lanes, restricted_data=True, state_loaded=True
        )
        self.assertEqual([r["model"] for r in res["ranked"]], ["claude-opus-5-5"])
        excluded_models = {r["model"] for r in res["excluded"]}
        self.assertEqual(excluded_models, {"Fable 5.2", "gpt-6.2-astra"})

        # Empty intersection (--restricted-data + --providers openai) returns empty ranked cleanly.
        empty = resolve_lanes.resolve_lanes(
            candidates, states, role="coding", allowed_providers=["codex"], authorized_lanes=lanes,
            restricted_data=True, state_loaded=True
        )
        self.assertEqual(empty["ranked"], [])
        self.assertIsNone(empty["recommended"])
        self.assertTrue(any("No eligible lanes" in w for w in empty["warnings"]))

    def test_model_specific_state_key_with_spaces_matches_bundled_model_names(self):
        candidates = [
            make_candidate("Fable 5.2", effort="medium", pool="claude", family="claude", coding=85),
            make_candidate("Opus 5.5", effort="high", pool="claude", family="claude", coding=81),
            make_candidate("Sonnet 5.5", effort="high", pool="claude", family="claude", coding=80),
        ]
        raw_state = {
            "claude": fresh_state(weekly_pct=30, five_hour_pct=20),
            "Fable 5.2": fresh_state(status="down", down_until="2026-11-21T18:00:00Z", limit="model cap"),
            "Opus 5.5": fresh_state(weekly_pct=87, five_hour_pct=20),
        }
        states, _ = resolve_lanes.parse_provider_state(raw_state, self.now, 45)
        res = resolve_lanes.resolve_lanes(candidates, states, role="coding", state_loaded=True)
        self.assertEqual([r["model"] for r in res["excluded"]], ["Fable 5.2"])
        # Sonnet 5.5 (80, healthy) is within 3 pts of Opus 5.5 (81, deprioritized) and wins #1.
        self.assertEqual([r["model"] for r in res["ranked"]], ["Sonnet 5.5", "Opus 5.5"])
        self.assertIn("deprioritized", res["ranked"][1]["flags"])

    def test_catalog_model_id_blocks_the_same_bundled_display_name(self):
        candidates = [
            make_candidate("Opus 5.5", effort="high", coding=81),
            make_candidate("Opus 5.5", effort="medium", coding=76),
            make_candidate("Sonnet 5.5", coding=73),
        ]
        states, _ = resolve_lanes.parse_provider_state(
            {"claude-opus-5-5": fresh_state(status="down", down_until="2026-11-21T18:00:00Z")},
            self.now,
            5,
        )
        res = resolve_lanes.resolve_lanes(candidates, states, state_loaded=True)
        self.assertEqual([r["model"] for r in res["ranked"]], ["Sonnet 5.5"])
        self.assertEqual([r["model"] for r in res["excluded"]], ["Opus 5.5", "Opus 5.5"])

    def test_model_outage_for_namespaced_id_does_not_apply_to_sibling_id(self):
        candidates = [
            make_candidate("example/alpha", pool="example", family="example", coding=90),
            make_candidate("example/beta", pool="example", family="example", coding=85),
        ]
        states, _ = resolve_lanes.parse_provider_state(
            {"example/alpha": fresh_state(status="down", down_until="2026-11-21T18:00:00Z")},
            self.now,
            5,
        )
        res = resolve_lanes.resolve_lanes(candidates, states, state_loaded=True)
        self.assertEqual([r["model"] for r in res["ranked"]], ["example/beta"])
        self.assertEqual([r["model"] for r in res["excluded"]], ["example/alpha"])

    def test_author_family_ignored_with_warning_on_non_review_role(self):
        report = resolve_lanes.resolve_from_paths(
            workspace=REPO_ROOT,
            state_path=EXAMPLE_STATE,
            role="coding",
            author_family="openai",
            now=self.now,
        )
        self.assertTrue(
            any("ignored for role 'coding'" in w for w in report["warnings"]),
            report["warnings"],
        )
        self.assertTrue(all(not r["same_family"] for r in report["ranked"]))
        md = resolve_lanes.render_markdown(report)
        self.assertIn("ignored for role `coding`; applies only to `--role review`", md)
        self.assertNotIn("cross-family lanes prioritized first", md)

    def test_shared_latencies_ignores_estimated_latency_in_different_headroom_or_deprioritized_bucket(self):
        candidates = [
            make_candidate("a-slow", pool="gemini", family="google", coding=94, latency_s=900),
            make_candidate("z-fast", pool="gemini", family="google", coding=94, latency_s=400),
            {
                **make_candidate("other-bucket-est", pool="codex", family="openai", coding=94, latency_s=150),
                "latency_kind": "estimate",
            },
        ]
        raw_state = {
            "gemini": fresh_state(weekly_pct=30, five_hour_pct=20),  # healthy, headroom 70
            "codex": fresh_state(weekly_pct=87, five_hour_pct=20),   # deprioritized, headroom 13
        }
        states, _ = resolve_lanes.parse_provider_state(raw_state, self.now, 45)
        res = resolve_lanes.resolve_lanes(candidates, states, role="coding", state_loaded=True)
        self.assertEqual(
            [row["model"] for row in res["ranked"]],
            ["z-fast", "a-slow", "other-bucket-est"],
        )

    def test_render_markdown_unavailable_score_basis_with_named_cohort(self):
        report = resolve_lanes.resolve_from_paths(
            workspace=REPO_ROOT,
            state_path=EXAMPLE_STATE,
            role="coding",
            cohort="missing-cohort",
            now=self.now,
        )
        self.assertEqual(report["score_basis"], "unavailable")
        self.assertEqual(report["score_cohort"], "missing-cohort")
        md = resolve_lanes.render_markdown(report)
        self.assertIn("- **Score cohort:** no comparable score available for `missing-cohort`", md)
        self.assertNotIn("live `missing-cohort`", md)

    def test_warns_when_authorized_lane_is_absent_from_measurements(self):
        candidates = [
            make_candidate("gpt-6.2-sol", effort="high", pool="codex", family="openai", coding=87),
        ]
        lanes = resolve_lanes.parse_authorized_lanes(profile_text(
            authorized_lane("gpt-6.2-sol", "high", "codex", roles=("coding",)),
            authorized_lane("claude-mythos-6", "high", "claude", roles=("coding",)),
        ))
        res = resolve_lanes.resolve_lanes(candidates, {}, role="coding", authorized_lanes=lanes)
        self.assertEqual(res["recommended"]["model"], "gpt-6.2-sol")
        self.assertIn(
            "Authorized lane 'claude-mythos-6' (high) in pool 'claude' has no measurements in model-measurements.md.",
            res["warnings"],
        )


class CliIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.profile = Path(directory.name) / "project-profile.md"
        self.profile.write_text(profile_text(
            authorized_lane("gemini-4-neon", "xhigh", "gemini", roles=("coding", "review")),
            authorized_lane("gemini-4-neon", "medium", "gemini", roles=("review",)),
            authorized_lane("gpt-6.2-astra", "high", "codex", roles=("coding", "review")),
        ), encoding="utf-8")

    def test_cli_example_provider_state_coding_and_review_json_and_markdown(self):
        coding = run_script(
            "resolve_lanes.py",
            "--workspace",
            str(REPO_ROOT),
            "--role",
            "coding",
            "--state",
            str(EXAMPLE_STATE),
            "--profile",
            str(self.profile),
            "--now",
            "2026-11-21T16:00:00Z",
            "--format",
            "json",
        )
        self.assertEqual(coding.returncode, 0, coding.stderr)
        data = json.loads(coding.stdout)
        self.assertEqual(data["recommended"]["model"], "gemini-4-neon")
        self.assertEqual(data["recommended"]["effort"], "xhigh")
        self.assertEqual(data["ranked"][1]["model"], "gpt-6.2-astra")
        self.assertIn("deprioritized", data["ranked"][1]["flags"])
        self.assertEqual(data["warnings"], [])

        # Markdown output for review --author-family openai
        review = run_script(
            "resolve_lanes.py",
            "--workspace",
            str(REPO_ROOT),
            "--role",
            "review",
            "--author-family",
            "openai",
            "--state",
            str(EXAMPLE_STATE),
            "--profile",
            str(self.profile),
            "--now",
            "2026-11-21T16:00:00Z",
            "--format",
            "markdown",
        )
        self.assertEqual(review.returncode, 0, review.stderr)
        self.assertIn("# Lane resolution · review", review.stdout)
        self.assertIn("`gemini-4-neon` (`xhigh`)", review.stdout)
        self.assertIn("same-family", review.stdout)
        self.assertIn("unmeasured", review.stdout)

    def test_cli_stale_warning_when_now_exceeds_ttl(self):
        proc = run_script(
            "resolve_lanes.py",
            "--workspace",
            str(REPO_ROOT),
            "--role",
            "coding",
            "--state",
            str(EXAMPLE_STATE),
            "--profile",
            str(self.profile),
            "--now",
            "2026-11-21T18:00:00Z",
            "--stale-minutes",
            "45",
            "--format",
            "json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(all(p["stale"] for p in data["providers"].values()))
        self.assertTrue(any("stale" in w.lower() for w in data["warnings"]))
        self.assertIn("stale", data["recommended"]["flags"])

    def test_cli_workspace_auto_discovery_with_refreshed_observations(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            obs = {
                "models": [
                    {
                        "model": "claude-opus-6-preview",
                        "provider": "Anthropic",
                        "released": "2026-11-21",
                        "url": "https://docs.anthropic.com/en/docs/about-claude/models",
                    }
                ],
                "measurements": [
                    {
                        "model": "claude-opus-6-preview",
                        "effort": "high",
                        "metric": "coding",
                        "cohort": "aa-v5-ref",
                        "unit": "points",
                        "source": "artificial-analysis",
                        "date": "2026-11-21",
                        "value": 98,
                        "url": "https://artificialanalysis.ai/leaderboards/models",
                    },
                    {
                        "model": "claude-opus-6-preview",
                        "effort": "high",
                        "metric": "seconds-per-task",
                        "cohort": "aa-v5-ref",
                        "unit": "seconds",
                        "source": "artificial-analysis",
                        "date": "2026-11-21",
                        "value": 420,
                        "url": "https://artificialanalysis.ai/leaderboards/models",
                    },
                ],
            }
            obs_path = ws / "obs.json"
            obs_path.write_text(json.dumps(obs), encoding="utf-8")

            ref = run_script("refresh.py", "--workspace", str(ws), "--input", str(obs_path))
            self.assertEqual(ref.returncode, 0, ref.stderr)

            state = {
                "claude": fresh_state(five_hour_pct=20, weekly_pct=20),
                "codex": fresh_state(five_hour_pct=20, weekly_pct=92),   # stopped!
                "gemini": fresh_state(five_hour_pct=30, weekly_pct=40),
                "deepseek": fresh_state(five_hour_pct=None, weekly_pct=None),
            }
            (ws / ".orchestration" / "provider-state.json").write_text(json.dumps(state), encoding="utf-8")
            (ws / ".orchestration" / "project-profile.md").write_text(profile_text(
                authorized_lane("claude-opus-6-preview", "high", "claude"),
            ), encoding="utf-8")

            # Omit --measurements and --state to test automatic <workspace>/.orchestration/ discovery.
            res = run_script(
                "resolve_lanes.py",
                "--workspace",
                str(ws),
                "--role",
                "coding",
                "--now",
                "2026-11-21T16:00:00Z",
                "--format",
                "json",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            report = json.loads(res.stdout)
            self.assertEqual(report["candidate_counts"]["workspace"], 1)
            self.assertEqual(report["recommended"]["model"], "claude-opus-6-preview")
            self.assertEqual(report["recommended"]["source"], "workspace")
            self.assertEqual(report["recommended"]["score"], 98.0)
            self.assertTrue(all(r["pool"] != "codex" for r in report["ranked"]))
            self.assertTrue(any(r["pool"] == "codex" for r in report["excluded"]))

    def test_cli_example_measurements_raw_only_models_do_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            ref = run_script("refresh.py", "--workspace", str(ws), "--input", str(EXAMPLE_MEASUREMENTS))
            self.assertEqual(ref.returncode, 0, ref.stderr)
            res = run_script(
                "resolve_lanes.py",
                "--workspace",
                str(ws),
                "--role",
                "coding",
                "--state",
                str(EXAMPLE_STATE),
                "--now",
                "2026-11-21T16:00:00Z",
                "--format",
                "json",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            report = json.loads(res.stdout)
            ws_models = {r["model"]: r for r in report["ranked"] if r["source"] == "workspace"}
            self.assertEqual(set(ws_models), {"demo-primary", "demo-backup"})
            self.assertEqual(ws_models["demo-primary"]["tier"], "unmeasured")

    def test_cli_provider_filter_is_advisory_without_explicit_lanes(self):
        with tempfile.TemporaryDirectory() as td:
            proc = run_script(
                "resolve_lanes.py", "--workspace", td, "--role", "coding",
                "--providers", "claude,codex", "--format", "json",
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertTrue(report["advisory"])
        self.assertIsNone(report["recommended"])
        self.assertTrue(report["ranked"])
        self.assertTrue(all(row["pool"] in ("codex", "claude") for row in report["ranked"]))

    def test_cli_reports_exact_authorized_variant_and_filters_roles(self):
        self.profile.write_text(profile_text(
            authorized_lane("gpt-6.2-sol", "high", "codex", roles=("coding",)),
            authorized_lane("claude-opus-5-5", "medium", "claude", roles=("review",)),
        ), encoding="utf-8")
        for role, expected in (("coding", ("gpt-6.2-sol", "high", "codex runner")),
                               ("review", ("claude-opus-5-5", "medium", "claude runner"))):
            with self.subTest(role=role):
                proc = run_script(
                    "resolve_lanes.py", "--workspace", str(REPO_ROOT), "--profile", str(self.profile),
                    "--role", role, "--providers", "claude,codex", "--format", "json",
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                report = json.loads(proc.stdout)
                self.assertFalse(report["advisory"])
                self.assertEqual(len(report["ranked"]), 1)
                rec = report["recommended"]
                self.assertEqual((rec["model"], rec["effort"], rec["runner"]), expected)

    def test_cli_rejects_invalid_profile_permissions(self):
        lane = authorized_lane("gpt-6.2-sol", "high", "codex")
        lane["restricted_data"] = "false"
        self.profile.write_text(profile_text(lane), encoding="utf-8")
        proc = run_script("resolve_lanes.py", "--profile", str(self.profile))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("boolean restricted_data", proc.stderr)

    def test_cli_error_exit_codes(self):
        bad_now = run_script("resolve_lanes.py", "--workspace", str(REPO_ROOT), "--now", "invalid")
        self.assertEqual(bad_now.returncode, 2)

        bad_ttl = run_script("resolve_lanes.py", "--workspace", str(REPO_ROOT), "--stale-minutes", "-5")
        self.assertEqual(bad_ttl.returncode, 2)

        bad_fam = run_script("resolve_lanes.py", "--workspace", str(REPO_ROOT), "--author-family", "unknown")
        self.assertEqual(bad_fam.returncode, 2)

        missing_state = run_script(
            "resolve_lanes.py", "--workspace", str(REPO_ROOT), "--state", "/nonexistent/provider-state.json"
        )
        self.assertEqual(missing_state.returncode, 1)


if __name__ == "__main__":
    unittest.main()
