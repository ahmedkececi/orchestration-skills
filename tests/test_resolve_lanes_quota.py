"""Regression checks for quota freshness, unified thresholds, projected overflow, and burn calibration."""

import json
import math
import os
from pathlib import Path
import tempfile
import unittest

from test_resolve_lanes import (
    REPO_ROOT,
    authorized_lane,
    fresh_state,
    make_candidate,
    profile_text,
    resolve_lanes,
    run_script,
)


class QuotaFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.now = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")

    def test_stale_or_future_percentages_cannot_rank_or_stop_a_lane(self):
        for timestamp in (None, "2026-11-21T15:35:00Z", "2026-11-21T16:03:00Z"):
            for weekly_pct in (5, 98):
                with self.subTest(timestamp=timestamp, weekly_pct=weekly_pct):
                    states, warnings = resolve_lanes.parse_provider_state(
                        {
                            "gemini": {"weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
                            "codex": {"weekly_pct": weekly_pct, "observed_at": timestamp},
                        },
                        self.now,
                        5,
                    )
                    self.assertTrue(states["codex"]["stale"])
                    self.assertFalse(states["codex"]["deprioritized"])
                    self.assertFalse(states["codex"]["excluded"])
                    self.assertIsNone(states["codex"]["headroom"])
                    self.assertTrue(any("stale" in warning for warning in warnings))
                    result = resolve_lanes.resolve_lanes(
                        [
                            make_candidate("stale", pool="codex", family="openai", coding=96),
                            make_candidate("fresh", pool="gemini", family="google", coding=95),
                        ],
                        states,
                        state_loaded=True,
                    )
                    self.assertEqual(result["ranked"][0]["model"], "fresh")
                    self.assertEqual(len(result["ranked"]), 2)

    def test_reset_between_observation_and_now_requires_new_reading(self):
        states, warnings = resolve_lanes.parse_provider_state(
            {
                "codex": {
                    "five_hour_pct": 96,
                    "weekly_pct": 97,
                    "observed_at": "2026-11-21T15:58:00Z",
                    "resets_at": "2026-11-21T15:59:00Z",
                },
                "gemini": {
                    "weekly_pct": 98,
                    "observed_at": "2026-11-21T15:58:00Z",
                    "resets_at": "2026-11-21T15:57:00Z",
                },
            },
            self.now,
            5,
        )
        self.assertTrue(states["codex"]["stale"])
        self.assertIsNone(states["codex"]["headroom"])
        self.assertFalse(states["codex"]["excluded"])
        self.assertEqual(states["codex"]["weekly_pct"], 97)
        self.assertEqual(states["codex"]["five_hour_pct"], 96)
        self.assertIn("reset after observed_at", warnings[0])
        self.assertTrue(states["gemini"]["excluded"])
        self.assertFalse(states["gemini"]["stale"])

    def test_outage_and_probe_only_status_block_normal_work(self):
        states, _ = resolve_lanes.parse_provider_state(
            {
                "claude": {"status": "down", "down_until": "2026-11-21T16:01:00Z"},
                "codex": {"status": "down", "down_until": "2026-11-21T15:59:00Z", "weekly_pct": 98},
            },
            self.now,
            5,
        )
        self.assertFalse(states["claude"]["probe_due"])
        self.assertTrue(states["codex"]["probe_due"])
        self.assertEqual(states["codex"]["effective_state"], "probe-only")
        result = resolve_lanes.resolve_lanes(
            [make_candidate("claude-lane", coding=95), make_candidate("codex-lane", pool="codex", coding=96)],
            states,
            state_loaded=True,
        )
        self.assertIsNone(result["recommended"])
        self.assertIn("probe", result["excluded"][0]["reasons"][0])

    def test_stale_model_quota_does_not_inflate_fresh_pool_headroom(self):
        states, _ = resolve_lanes.parse_provider_state(
            {
                "claude": {"weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
                "claude-lane": {"weekly_pct": 95, "observed_at": "2026-11-21T15:30:00Z"},
            },
            self.now,
            5,
        )
        result = resolve_lanes.resolve_lanes(
            [make_candidate("claude-lane", coding=95)], states, state_loaded=True
        )
        self.assertIn("stale", result["ranked"][0]["flags"])
        self.assertIsNone(result["ranked"][0]["headroom"])
        self.assertEqual(result["ranked"][0]["pool_state"], "stale")
        self.assertTrue(any("Confirm live usage" in warning for warning in result["warnings"]))

    def test_l3_provider_state_alias_collision_rejected(self):
        collisions = [
            {
                "anthropic": {"status": "down", "down_until": "2026-11-21T18:00:00Z"},
                "claude": {"status": "up", "weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
            },
            {
                "openai": {"status": "up", "weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
                "chatgpt": {"status": "down", "down_until": "2026-11-21T18:00:00Z"},
            },
            {
                "Claude": {"status": "down", "down_until": "2026-11-21T18:00:00Z"},
                "claude": {"status": "up", "weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
            },
        ]
        for raw in collisions:
            with self.subTest(keys=list(raw)):
                with self.assertRaisesRegex(ValueError, "Conflicting provider-state entries"):
                    resolve_lanes.parse_provider_state(raw, self.now, 5)

    def test_l8_overflow_timestamps_huge_int_pct_and_negative_zero(self):
        with self.assertRaises(ValueError):
            resolve_lanes.parse_iso_utc("9999-12-31T23:59:59-05:00")

        states, warnings = resolve_lanes.parse_provider_state(
            {"claude": {"weekly_pct": -0.0, "observed_at": "9999-12-31T23:59:59-05:00"}},
            self.now,
            5,
        )
        self.assertTrue(states["claude"]["stale"])
        self.assertEqual(states["claude"]["weekly_pct"], 0.0)
        self.assertEqual(str(states["claude"]["weekly_pct"]), "0.0")
        self.assertTrue(any("Invalid ISO-8601" in w for w in warnings))

        with self.assertRaises(ValueError):
            resolve_lanes.parse_provider_state(
                {"claude": {"weekly_pct": 10**400, "observed_at": "2026-11-21T15:59:00Z"}},
                self.now,
                5,
            )

    def test_l9_fresh_pool_with_untouched_template_model_placeholder_inherits_headroom(self):
        states, _ = resolve_lanes.parse_provider_state(
            {
                "claude": {
                    "status": "up",
                    "down_until": None,
                    "limit": None,
                    "five_hour_pct": 20,
                    "weekly_pct": 40,
                    "resets_at": None,
                    "observed_at": "2026-11-21T15:59:00Z",
                },
                "claude-opus-5-5": {
                    "status": "up",
                    "down_until": None,
                    "limit": None,
                    "five_hour_pct": None,
                    "weekly_pct": None,
                    "resets_at": None,
                    "observed_at": None,
                },
            },
            self.now,
            5,
        )
        result = resolve_lanes.resolve_lanes(
            [make_candidate("claude-opus-5-5", coding=81)], states, state_loaded=True
        )
        row = result["ranked"][0]
        self.assertEqual(row["pool_state"], "up")
        self.assertEqual(row["headroom"], 60.0)
        self.assertFalse(row["stale"])
        self.assertNotIn("stale", row["flags"])
        self.assertNotIn("probe_due", row)

    def test_l14_limit_validation_and_markdown_table_sanitization(self):
        for bad_limit in ("weekly | cap", "line1\nline2", "x" * 161, 42):
            with self.subTest(limit=bad_limit):
                with self.assertRaisesRegex(ValueError, "field 'limit'"):
                    resolve_lanes.parse_provider_state(
                        {"claude": {"status": "down", "limit": bad_limit}}, self.now, 5
                    )

        report = {
            "role": "coding",
            "scoring_method": "coding profile score",
            "equivalence_threshold_points": 3.0,
            "top_score": 80.0,
            "score_basis": "historical",
            "score_cohort": None,
            "cross_family_anchored": False,
            "author_family": None,
            "restricted_data": False,
            "allowed_providers": None,
            "evaluated_at": "2026-11-21T16:00:00Z",
            "stale_minutes": 5,
            "measurements_path": "m.md",
            "state_path": "s.json",
            "profile_path": None,
            "advisory": True,
            "candidate_counts": {"historical": 1, "workspace": 0, "total": 1},
            "warnings": [],
            "recommended": None,
            "ranked": [],
            "excluded": [
                {
                    "model": "m1",
                    "effort": "high",
                    "pool": "claude",
                    "family": "claude",
                    "score": 80.0,
                    "reasons": ["bad | pipe\nnewline"],
                }
            ],
        }
        md = resolve_lanes.render_markdown(report)
        self.assertIn("bad \\| pipe newline", md)

    def test_l15_threshold_precision_resets_at_active_outage_and_state_key_slash(self):
        states, warnings = resolve_lanes.parse_provider_state(
            {
                "claude": {"weekly_pct": 89.999999, "observed_at": "2026-11-21T15:59:00Z", "resets_at": "   "},
                "codex": {"five_hour_pct": 94.999999, "observed_at": "2026-11-21T15:59:00Z", "resets_at": ""},
                "xai": {"weekly_pct": 94.999999, "observed_at": "2026-11-21T15:59:00Z"},
                "gemini": {"weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z", "resets_at": "2026-11-21 16:00 UTC"},
                "deepseek": {"status": "down", "down_until": "2026-11-21T18:00:00Z", "observed_at": "2026-11-21T10:00:00Z"},
            },
            self.now,
            5,
        )
        # Never rounds 89.999999 up to 90% move or 94.999999 up to 95% stop.
        self.assertFalse(states["claude"]["excluded"])
        self.assertFalse(states["claude"]["deprioritized"])
        self.assertEqual(states["claude"]["effective_state"], "up")
        self.assertEqual(states["claude"]["reasons"], [])
        self.assertIsNone(states["claude"]["resets_at"])
        self.assertFalse(states["claude"]["stale"])

        self.assertFalse(states["codex"]["excluded"])
        self.assertTrue(states["codex"]["deprioritized"])
        self.assertIn("94.999999%", states["codex"]["reasons"][0])
        self.assertNotIn("95%", states["codex"]["reasons"][0])
        self.assertFalse(states["codex"]["stale"])

        self.assertFalse(states["xai"]["excluded"])
        self.assertTrue(states["xai"]["deprioritized"])
        self.assertIn("94.999999%", states["xai"]["reasons"][0])
        self.assertNotIn("95%", states["xai"]["reasons"][0])

        # Unparseable resets_at marks stale so potentially post-reset pct is not trusted.
        self.assertTrue(states["gemini"]["stale"])
        self.assertIsNone(states["gemini"]["headroom"])
        self.assertTrue(any("invalid resets_at" in w for w in warnings))

        # Active future down_until suppresses spurious stale warning even with old observed_at.
        self.assertTrue(states["deepseek"]["excluded"])
        self.assertFalse(states["deepseek"]["stale"])
        self.assertFalse(any("deepseek" in w for w in warnings))

        # normalize_state_key consistency for alias/pool slash forms without breaking namespaced model IDs.
        self.assertEqual(resolve_lanes.normalize_state_key("OpenAI/codex"), "codex")
        self.assertEqual(resolve_lanes.normalize_state_key("Anthropic/claude"), "claude")
        self.assertEqual(resolve_lanes.normalize_state_key("OpenAI/gpt-6.2-astra"), "openai/gpt-6.2-astra")
        self.assertEqual(resolve_lanes.normalize_state_key("example/alpha"), "example/alpha")


class PreDispatchQuotaAndCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.now = resolve_lanes.parse_iso_utc("2026-11-22T12:00:00Z")
        self.now_iso = "2026-11-22T12:00:00Z"
        self.obs_iso = "2026-11-22T11:58:00Z"

    def test_unified_90_move_and_95_stop_exact_boundaries_for_both_windows(self):
        self.assertEqual(resolve_lanes.WEEKLY_MOVE_PCT, 90.0)
        self.assertEqual(resolve_lanes.WEEKLY_STOP_PCT, 95.0)
        self.assertEqual(resolve_lanes.FIVE_HOUR_MOVE_PCT, 90.0)
        self.assertEqual(resolve_lanes.FIVE_HOUR_STOP_PCT, 95.0)

        cases = (
            (89.9, "up", False, False),
            (90.0, "deprioritized", True, False),
            (94.9, "deprioritized", True, False),
            (95.0, "stopped", False, True),
        )
        for window in ("five_hour_pct", "weekly_pct"):
            other = "weekly_pct" if window == "five_hour_pct" else "five_hour_pct"
            for pct, expected_state, expected_deprio, expected_excl in cases:
                with self.subTest(window=window, pct=pct):
                    raw = {
                        "codex": fresh_state(
                            now_iso=self.obs_iso,
                            **{window: pct, other: 20.0},
                        )
                    }
                    states, warnings = resolve_lanes.parse_provider_state(raw, self.now, 5)
                    self.assertEqual(warnings, [])
                    st = states["codex"]
                    self.assertEqual(st["effective_state"], expected_state)
                    self.assertEqual(st["deprioritized"], expected_deprio)
                    self.assertEqual(st["excluded"], expected_excl)
                    self.assertEqual(st["headroom"], round(100.0 - pct, 2))

    def test_operator_scenario_89pct_5h_large_unit_projected_overflow_blocks_before_dispatch(self):
        # Operator scenario: codex five_hour_pct = 89%, calibrated 'l' unit burns ~11% ->
        # projected >= 95% (89.0% + 11.0% * 1.2 = 102.2%) -> blocked before dispatch,
        # healthy equivalent Claude fallback recommended.
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            state_path = ws / "provider-state.json"
            profile_path = ws / "project-profile.md"

            state_payload = {
                "codex": fresh_state(now_iso=self.obs_iso, five_hour_pct=89, weekly_pct=45),
                "claude": fresh_state(now_iso=self.obs_iso, five_hour_pct=30, weekly_pct=40),
                "_calibration": {
                    "version": 1,
                    "alpha": 0.35,
                    "lanes": {
                        "codex/gpt-6.2-sol/high": {
                            "samples": 4,
                            "five_hour_per_m": 5.79,
                            "weekly_per_m": 2.1,
                            "max_ratio": 1.2,
                            "by_size": {
                                "l": {"samples": 2, "five_hour_pct": 11.0, "weekly_pct": 4.0},
                            },
                            "updated_at": self.obs_iso,
                        }
                    },
                    "pools": {
                        "codex": {
                            "samples": 4,
                            "five_hour_per_m": 5.79,
                            "weekly_per_m": 2.1,
                            "max_ratio": 1.2,
                            "updated_at": self.obs_iso,
                        }
                    },
                },
            }
            state_path.write_text(json.dumps(state_payload), encoding="utf-8")
            profile_path.write_text(
                profile_text(
                    authorized_lane("gpt-6.2-sol", "high", "codex", roles=("coding",)),
                    authorized_lane("claude-opus-5-5", "high", "claude", roles=("coding",)),
                ),
                encoding="utf-8",
            )

            # JSON CLI verification
            proc_json = run_script(
                "resolve_lanes.py",
                "--workspace",
                str(REPO_ROOT),
                "--profile",
                str(profile_path),
                "--state",
                str(state_path),
                "--role",
                "coding",
                "--unit-size",
                "l",
                "--now",
                self.now_iso,
                "--format",
                "json",
            )
            self.assertEqual(proc_json.returncode, 0, proc_json.stderr)
            report = json.loads(proc_json.stdout)
            self.assertEqual(report["unit_size"], "l")
            self.assertEqual(report["recommended"]["model"], "claude-opus-5-5")
            self.assertFalse(report["recommended"]["projected_overflow"])

            excluded_codex = [
                r for r in report["excluded"] if r["model"] == "gpt-6.2-sol" and r["effort"] == "high"
            ]
            self.assertEqual(len(excluded_codex), 1)
            blocked = excluded_codex[0]
            self.assertTrue(blocked["projected_overflow"])
            self.assertFalse(blocked["projected_deprioritized"])
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["pool_state"], "blocked")
            self.assertEqual(blocked["estimated_burn"]["source"], "lane_exact")
            self.assertEqual(blocked["estimated_burn"]["five_hour_pct"], 11.0)
            self.assertEqual(blocked["estimated_burn"]["safety_margin"], 1.2)
            self.assertEqual(blocked["projected_five_hour_pct"], 102.2)
            self.assertEqual(blocked["projected_headroom_pct"], 0.0)
            self.assertIn("projected five_hour_pct 102.2% >= 95% stop", blocked["reasons"][0])

            # Markdown CLI verification
            proc_md = run_script(
                "resolve_lanes.py",
                "--workspace",
                str(REPO_ROOT),
                "--profile",
                str(profile_path),
                "--state",
                str(state_path),
                "--role",
                "coding",
                "--unit-size",
                "l",
                "--now",
                self.now_iso,
                "--format",
                "markdown",
            )
            self.assertEqual(proc_md.returncode, 0, proc_md.stderr)
            self.assertIn("Unit size:** `l`", proc_md.stdout)
            self.assertIn("`claude-opus-5-5`", proc_md.stdout)
            self.assertIn("projected five_hour_pct 102.2% >= 95% stop", proc_md.stdout)

    def test_projected_deprioritized_ranks_healthy_equivalent_lane_ahead(self):
        # current = 86%, est = 5.0%, margin = 1.0 -> projected = 91.0% (90 <= projected < 95)
        for window in ("five_hour_pct", "weekly_pct"):
            other = "weekly_pct" if window == "five_hour_pct" else "five_hour_pct"
            with self.subTest(window=window):
                candidates = [
                    make_candidate("codex-top", effort="high", pool="codex", family="openai", coding=95, latency_s=200),
                    make_candidate("claude-equiv", effort="high", pool="claude", family="claude", coding=94, latency_s=300),
                ]
                cal = {
                    "version": 1,
                    "alpha": 0.35,
                    "lanes": {
                        "codex/codex-top/high": {
                            "samples": 3,
                            "five_hour_per_m": 5.0 if window == "five_hour_pct" else 1.0,
                            "weekly_per_m": 5.0 if window == "weekly_pct" else 1.0,
                            "max_ratio": 1.0,
                            "by_size": {
                                "m": {
                                    "samples": 3,
                                    "five_hour_pct": 5.0 if window == "five_hour_pct" else 1.0,
                                    "weekly_pct": 5.0 if window == "weekly_pct" else 1.0,
                                }
                            },
                            "updated_at": self.obs_iso,
                        }
                    },
                    "pools": {},
                }
                raw_state = {
                    "codex": fresh_state(now_iso=self.obs_iso, **{window: 86.0, other: 20.0}),
                    "claude": fresh_state(now_iso=self.obs_iso, five_hour_pct=30.0, weekly_pct=30.0),
                }
                states, _ = resolve_lanes.parse_provider_state(raw_state, self.now, 5)
                lanes = resolve_lanes.parse_authorized_lanes(
                    profile_text(
                        authorized_lane("codex-top", "high", "codex", roles=("coding",)),
                        authorized_lane("claude-equiv", "high", "claude", roles=("coding",)),
                    )
                )
                res = resolve_lanes.resolve_lanes(
                    candidates,
                    states,
                    role="coding",
                    authorized_lanes=lanes,
                    state_loaded=True,
                    unit_size="m",
                    safety_margin=1.0,
                    calibration=cal,
                )
                self.assertEqual(res["recommended"]["model"], "claude-equiv")
                self.assertEqual([r["model"] for r in res["ranked"]], ["claude-equiv", "codex-top"])
                codex_row = res["ranked"][1]
                self.assertTrue(codex_row["projected_deprioritized"])
                self.assertTrue(codex_row["deprioritized"])
                self.assertFalse(codex_row["projected_overflow"])
                self.assertEqual(codex_row["pool_state"], "deprioritized")
                self.assertIn("deprioritized", codex_row["flags"])
                self.assertIn("projected-deprioritized", codex_row["flags"])
                self.assertEqual(codex_row[f"projected_{window}"], 91.0)
                self.assertEqual(codex_row["projected_headroom_pct"], 9.0)

    def test_cold_start_vs_ewma_calibration_convergence_and_safety_margin_adaptation(self):
        # 1. Cold start (samples = 0)
        cold = resolve_lanes.estimate_burn("codex", "gpt-6.2-sol", "high", "l")
        self.assertEqual(cold["source"], "cold_start")
        self.assertEqual(cold["samples"], 0)
        self.assertEqual(cold["safety_margin"], 1.40)
        # codex default per_m = 5.0 / 2.0, weight(sol, high) = 1.0, mult(l) = 1.9
        self.assertEqual(cold["five_hour_pct"], 9.5)
        self.assertEqual(cold["weekly_pct"], 3.8)

        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "provider-state.json"
            state_path.write_text(
                json.dumps({"codex": fresh_state(now_iso=self.obs_iso, five_hour_pct=10, weekly_pct=10)}),
                encoding="utf-8",
            )

            # Observation 1: actual burn 12% 5h, 5% weekly on 'l' unit (ratio vs cold 9.5 = 1.2632)
            rec1 = run_script(
                "resolve_lanes.py",
                "--state",
                str(state_path),
                "--record-burn",
                "--burn-provider",
                "codex",
                "--burn-model",
                "gpt-6.2-sol",
                "--burn-effort",
                "high",
                "--unit-size",
                "l",
                "--before-5h",
                "10",
                "--after-5h",
                "22",
                "--before-weekly",
                "10",
                "--after-weekly",
                "15",
                "--now",
                "2026-11-22T12:01:00Z",
                "--format",
                "json",
            )
            self.assertEqual(rec1.returncode, 0, rec1.stderr)
            s1 = json.loads(rec1.stdout)
            self.assertTrue(s1["calibration_updated"])
            self.assertEqual(s1["deltas"], {"five_hour_pct": 12.0, "weekly_pct": 5.0})
            self.assertEqual(s1["lane_calibration"]["samples"], 1)
            self.assertEqual(s1["estimated_burn"]["source"], "lane_exact")
            self.assertEqual(s1["estimated_burn"]["safety_margin"], 1.25)
            self.assertEqual(s1["estimated_burn"]["five_hour_pct"], 12.0)
            self.assertEqual(s1["provider_state"]["five_hour_pct"], 22.0)
            self.assertEqual(s1["provider_state"]["weekly_pct"], 15.0)

            # Different unit size ('m') on the same calibrated lane uses lane_scaled
            cal1 = resolve_lanes.parse_calibration(json.loads(state_path.read_text(encoding="utf-8")))
            m_scaled = resolve_lanes.estimate_burn("codex", "gpt-6.2-sol", "high", "m", calibration=cal1)
            self.assertEqual(m_scaled["source"], "lane_scaled")
            self.assertEqual(m_scaled["samples"], 1)
            self.assertEqual(m_scaled["safety_margin"], 1.25)
            self.assertAlmostEqual(m_scaled["five_hour_pct"], round(12.0 / 1.9, 2), places=2)

            # Observation 2: actual burn 10% 5h, 4% weekly on 'l' unit -> EWMA moves smoothly toward 10/4
            s2 = resolve_lanes.record_burn(
                state_path,
                provider="codex",
                model="gpt-6.2-sol",
                effort="high",
                unit_size="l",
                before_5h=22,
                after_5h=32,
                before_weekly=15,
                after_weekly=19,
                now="2026-11-22T12:05:00Z",
            )
            self.assertEqual(s2["lane_calibration"]["samples"], 2)
            self.assertEqual(s2["estimated_burn"]["samples"], 2)
            self.assertEqual(s2["estimated_burn"]["safety_margin"], 1.25)
            # EWMA: 0.35 * 10 + 0.65 * 12 = 11.3
            self.assertEqual(s2["estimated_burn"]["five_hour_pct"], 11.3)
            # EWMA: 0.35 * 4 + 0.65 * 5 = 4.65
            self.assertEqual(s2["estimated_burn"]["weekly_pct"], 4.65)

            # Observation 3: actual burn 10% 5h, 4% weekly -> samples == 3 triggers adaptive safety margin
            s3 = resolve_lanes.record_burn(
                state_path,
                provider="codex",
                model="gpt-6.2-sol",
                effort="high",
                unit_size="l",
                before_5h=32,
                after_5h=42,
                before_weekly=19,
                after_weekly=23,
                now="2026-11-22T12:10:00Z",
            )
            self.assertEqual(s3["lane_calibration"]["samples"], 3)
            # EWMA: 0.35 * 10 + 0.65 * 11.3 = 10.845 -> 10.85
            self.assertEqual(s3["estimated_burn"]["five_hour_pct"], 10.85)
            # max_ratio was 12 / 9.5 = 1.2632, weekly 5 / 3.8 = 1.3158 -> adaptive margin = 1.32
            expected_margin = round(min(1.50, max(1.15, s3["lane_calibration"]["max_ratio"])), 2)
            self.assertEqual(s3["estimated_burn"]["safety_margin"], expected_margin)
            self.assertGreaterEqual(s3["estimated_burn"]["safety_margin"], 1.15)
            self.assertLessEqual(s3["estimated_burn"]["safety_margin"], 1.50)

            # Markdown rendering for --record-burn
            md = resolve_lanes.render_record_burn_markdown(s3)
            self.assertIn("# Burn calibration recorded", md)
            self.assertIn("codex/gpt-6.2-sol/high", md)

            # Blend check: 1 sample on a new size ('s') blends 0.65 * by_size + 0.35 * (per_m * mult)
            s4 = resolve_lanes.record_burn(
                state_path,
                provider="codex",
                model="gpt-6.2-sol",
                effort="high",
                unit_size="s",
                before_5h=42,
                after_5h=46,
                before_weekly=23,
                after_weekly=25,
                now="2026-11-22T12:15:00Z",
            )
            cal4 = resolve_lanes.parse_calibration(json.loads(state_path.read_text(encoding="utf-8")))
            lane4 = cal4["lanes"]["codex/gpt-6.2-sol/high"]
            expected_blend_5h = round(0.65 * 4.0 + 0.35 * (lane4["five_hour_per_m"] * 0.55), 2)
            self.assertEqual(s4["estimated_burn"]["source"], "lane_exact")
            self.assertEqual(s4["estimated_burn"]["five_hour_pct"], expected_blend_5h)

    def test_pool_level_fallback_calibration_for_new_model_in_same_pool(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "provider-state.json"
            state_path.write_text(
                json.dumps({"codex": fresh_state(now_iso=self.obs_iso, five_hour_pct=10, weekly_pct=10)}),
                encoding="utf-8",
            )
            # Calibrate codex pool using gpt-6.2-sol (weight=1.0) on 'm' (mult=1.0): 8% 5h, 3% weekly
            for idx in range(3):
                resolve_lanes.record_burn(
                    state_path,
                    provider="codex",
                    model="gpt-6.2-sol",
                    effort="high",
                    unit_size="m",
                    before_5h=10 + idx * 8,
                    after_5h=18 + idx * 8,
                    before_weekly=10 + idx * 3,
                    after_weekly=13 + idx * 3,
                    now=f"2026-11-22T12:0{idx + 1}:00Z",
                )

            cal = resolve_lanes.parse_calibration(json.loads(state_path.read_text(encoding="utf-8")))
            # New model in codex pool with 0 lane samples: gpt-6.2-astra (weight=1.6) on 'm' (mult=1.0)
            est = resolve_lanes.estimate_burn("codex", "gpt-6.2-astra", "high", "m", calibration=cal)
            self.assertEqual(est["source"], "pool_scaled")
            self.assertEqual(est["samples"], 3)
            # pool five_hour_per_m == 8.0 * weight 1.6 * mult 1.0 = 12.8; weekly == 3.0 * 1.6 = 4.8
            self.assertEqual(est["five_hour_pct"], 12.8)
            self.assertEqual(est["weekly_pct"], 4.8)

            # Uncalibrated different pool still falls back to cold_start
            claude_est = resolve_lanes.estimate_burn("claude", "claude-opus-5-5", "high", "m", calibration=cal)
            self.assertEqual(claude_est["source"], "cold_start")
            self.assertEqual(claude_est["samples"], 0)

    def test_window_reset_guard_skips_ewma_corruption_and_updates_live_state(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "provider-state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "codex": {
                            "status": "up",
                            "down_until": None,
                            "limit": "tier-note",
                            "five_hour_pct": 85,
                            "weekly_pct": 40,
                            "resets_at": "2026-11-22T13:00:00Z",
                            "observed_at": self.obs_iso,
                        }
                    }
                ),
                encoding="utf-8",
            )
            # Seed one valid observation first
            seed = resolve_lanes.record_burn(
                state_path,
                provider="codex",
                model="gpt-6.2-sol",
                effort="high",
                unit_size="m",
                before_5h=75,
                after_5h=85,
                before_weekly=37,
                after_weekly=40,
                now="2026-11-22T12:00:00Z",
            )
            self.assertEqual(seed["lane_calibration"]["five_hour_per_m"], 10.0)
            self.assertEqual(seed["lane_calibration"]["weekly_per_m"], 3.0)

            # Auto-detected 5h reset (after=6 < before=85), while weekly advanced normally (40 -> 43)
            partial = resolve_lanes.record_burn(
                state_path,
                provider="codex",
                model="gpt-6.2-sol",
                effort="high",
                unit_size="m",
                before_5h=85,
                after_5h=6,
                before_weekly=40,
                after_weekly=43,
                now="2026-11-22T12:05:00Z",
            )
            self.assertTrue(partial["calibration_updated"])
            self.assertEqual(partial["skipped_windows"], ["five_hour_pct"])
            self.assertIsNone(partial["deltas"]["five_hour_pct"])
            self.assertEqual(partial["deltas"]["weekly_pct"], 3.0)
            self.assertTrue(any("window reset detected" in w and "five_hour_pct" in w for w in partial["warnings"]))
            # 5h EWMA preserved untouched at 10.0, live 5h updated to 6.0, existing fields preserved
            self.assertEqual(partial["lane_calibration"]["five_hour_per_m"], 10.0)
            self.assertEqual(partial["provider_state"]["five_hour_pct"], 6.0)
            self.assertEqual(partial["provider_state"]["weekly_pct"], 43.0)
            self.assertEqual(partial["provider_state"]["limit"], "tier-note")
            self.assertEqual(partial["provider_state"]["resets_at"], "2026-11-22T13:00:00Z")

            # Explicit --reset-occurred via CLI skips all EWMA updates while updating live state
            proc = run_script(
                "resolve_lanes.py",
                "--state",
                str(state_path),
                "--record-burn",
                "--burn-provider",
                "codex",
                "--burn-model",
                "gpt-6.2-sol",
                "--burn-effort",
                "high",
                "--unit-size",
                "m",
                "--before-5h",
                "6",
                "--after-5h",
                "12",
                "--before-weekly",
                "43",
                "--after-weekly",
                "45",
                "--reset-occurred",
                "--now",
                "2026-11-22T12:10:00Z",
                "--format",
                "json",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            flagged = json.loads(proc.stdout)
            self.assertFalse(flagged["calibration_updated"])
            self.assertEqual(flagged["skipped_windows"], ["five_hour_pct", "weekly_pct"])
            self.assertEqual(flagged["lane_calibration"]["samples"], partial["lane_calibration"]["samples"])
            self.assertEqual(flagged["lane_calibration"]["five_hour_per_m"], 10.0)
            self.assertEqual(flagged["provider_state"]["five_hour_pct"], 12.0)
            self.assertEqual(flagged["provider_state"]["weekly_pct"], 45.0)
            self.assertTrue(any("reset_occurred" in w for w in flagged["warnings"]))

            # Zero-delta (after == before) is a valid observation and does not fail
            zero = resolve_lanes.record_burn(
                state_path,
                provider="codex",
                model="gpt-6.2-sol",
                effort="high",
                unit_size="xs",
                before_5h=12,
                after_5h=12,
                now="2026-11-22T12:15:00Z",
            )
            self.assertTrue(zero["calibration_updated"])
            self.assertEqual(zero["deltas"]["five_hour_pct"], 0.0)

    def test_security_and_validation_for_unit_size_margin_burn_args_and_symlinks(self):
        # CLI invalid --unit-size
        bad_size = run_script("resolve_lanes.py", "--workspace", str(REPO_ROOT), "--unit-size", "xxl")
        self.assertEqual(bad_size.returncode, 2)

        # CLI invalid --safety-margin (below 1.0, above 3.0, NaN, inf)
        for bad_margin in ("0.5", "3.1", "nan", "inf", "abc"):
            with self.subTest(cli_margin=bad_margin):
                proc = run_script(
                    "resolve_lanes.py", "--workspace", str(REPO_ROOT), "--unit-size", "m", "--safety-margin", bad_margin
                )
                self.assertEqual(proc.returncode, 2)

        # CLI unpaired before/after flags & missing pairs & burn flags without --record-burn
        bad_cli_cases = (
            ("--record-burn", "--burn-provider", "codex", "--burn-model", "gpt-6.2-sol", "--unit-size", "m"),
            ("--record-burn", "--burn-provider", "codex", "--burn-model", "gpt-6.2-sol", "--unit-size", "m", "--before-5h", "10"),
            ("--record-burn", "--burn-provider", "codex", "--burn-model", "gpt-6.2-sol", "--unit-size", "m", "--after-weekly", "20"),
            ("--record-burn", "--burn-provider", "codex", "--burn-model", "gpt-6.2-sol", "--unit-size", "m", "--before-5h", "-1", "--after-5h", "5"),
            ("--record-burn", "--burn-provider", "codex", "--burn-model", "gpt-6.2-sol", "--unit-size", "m", "--before-5h", "10", "--after-5h", "101"),
            ("--record-burn", "--burn-provider", "codex", "--burn-model", "gpt-6.2-sol", "--unit-size", "m", "--before-5h", "nan", "--after-5h", "10"),
            ("--burn-provider", "codex", "--before-5h", "10", "--after-5h", "15"),
        )
        for args in bad_cli_cases:
            with self.subTest(cli_args=args):
                proc = run_script("resolve_lanes.py", *args)
                self.assertEqual(proc.returncode, 2)
                self.assertNotIn("Traceback", proc.stderr)

        # Python API rejects invalid unit_size, safety_margin, booleans, NaN, inf, out-of-range, unpaired
        for bad_val in (True, False, -0.1, 100.1, float("nan"), float("inf"), "10"):
            with self.subTest(api_pct=bad_val):
                with tempfile.TemporaryDirectory() as td:
                    with self.assertRaises(ValueError):
                        resolve_lanes.record_burn(
                            Path(td) / "state.json",
                            provider="codex",
                            model="gpt-6.2-sol",
                            unit_size="m",
                            before_5h=bad_val,
                            after_5h=20,
                        )

        for bad_margin in (True, False, 0.99, 3.01, math.nan, math.inf, "1.2"):
            with self.subTest(api_margin=bad_margin):
                with self.assertRaises(ValueError):
                    resolve_lanes.estimate_burn("codex", "gpt-6.2-sol", "high", "m", safety_margin=bad_margin)

        with self.assertRaises(ValueError):
            resolve_lanes.estimate_burn("codex", "gpt-6.2-sol", "high", "huge")

        # Symlink target and symlink parent rejection on --record-burn
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            real_file = base / "real-state.json"
            real_file.write_text('{"codex": {"status": "up"}}\n', encoding="utf-8")
            link_file = base / "state-link.json"
            os.symlink(real_file, link_file)

            with self.assertRaisesRegex(ValueError, "symlink"):
                resolve_lanes.record_burn(
                    link_file,
                    provider="codex",
                    model="gpt-6.2-sol",
                    unit_size="m",
                    before_5h=10,
                    after_5h=15,
                )
            cli_sym = run_script(
                "resolve_lanes.py",
                "--state",
                str(link_file),
                "--record-burn",
                "--burn-provider",
                "codex",
                "--burn-model",
                "gpt-6.2-sol",
                "--unit-size",
                "m",
                "--before-5h",
                "10",
                "--after-5h",
                "15",
            )
            self.assertEqual(cli_sym.returncode, 1)
            self.assertIn("symlink", cli_sym.stderr.lower())
            # Real target file remains untouched
            self.assertEqual(real_file.read_text(encoding="utf-8"), '{"codex": {"status": "up"}}\n')

            real_dir = base / "real-dir"
            real_dir.mkdir()
            link_dir = base / "link-dir"
            os.symlink(real_dir, link_dir)
            with self.assertRaisesRegex(ValueError, "symlink"):
                resolve_lanes.record_burn(
                    link_dir / "provider-state.json",
                    provider="codex",
                    model="gpt-6.2-sol",
                    unit_size="m",
                    before_5h=10,
                    after_5h=15,
                )

    def test_backward_compatibility_without_unit_size_when_calibration_present(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "provider-state.json"
            profile_path = Path(td) / "project-profile.md"
            state_payload = {
                "claude": fresh_state(now_iso=self.obs_iso, five_hour_pct=30, weekly_pct=40),
                "codex": fresh_state(now_iso=self.obs_iso, five_hour_pct=25, weekly_pct=91),
                "_calibration": {
                    "version": 1,
                    "alpha": 0.35,
                    "lanes": {
                        "codex/gpt-6.2-sol/high": {
                            "samples": 3,
                            "five_hour_per_m": 6.0,
                            "weekly_per_m": 2.4,
                            "max_ratio": 1.25,
                            "by_size": {"m": {"samples": 3, "five_hour_pct": 6.0, "weekly_pct": 2.4}},
                            "updated_at": self.obs_iso,
                        }
                    },
                    "pools": {
                        "codex": {
                            "samples": 3,
                            "five_hour_per_m": 6.0,
                            "weekly_per_m": 2.4,
                            "max_ratio": 1.25,
                            "updated_at": self.obs_iso,
                        }
                    },
                },
            }
            state_path.write_text(json.dumps(state_payload), encoding="utf-8")
            profile_path.write_text(
                profile_text(
                    authorized_lane("gpt-6.2-sol", "high", "codex", roles=("coding",)),
                    authorized_lane("claude-opus-5-5", "high", "claude", roles=("coding",)),
                ),
                encoding="utf-8",
            )

            # _calibration must never appear as a provider/model entry in parse_provider_state or CLI JSON
            states, warnings = resolve_lanes.parse_provider_state(state_payload, self.now, 5)
            self.assertNotIn("_calibration", states)
            self.assertEqual(set(states), {"claude", "codex"})
            self.assertEqual(warnings, [])

            proc = run_script(
                "resolve_lanes.py",
                "--workspace",
                str(REPO_ROOT),
                "--profile",
                str(profile_path),
                "--state",
                str(state_path),
                "--role",
                "coding",
                "--now",
                self.now_iso,
                "--format",
                "json",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertIsNone(report["unit_size"])
            self.assertNotIn("_calibration", report["providers"])
            self.assertEqual(report["recommended"]["model"], "claude-opus-5-5")
            self.assertIsNone(report["recommended"]["estimated_burn"])
            self.assertFalse(report["recommended"]["projected_overflow"])
            self.assertEqual(report["warnings"], [])

            # --safety-margin without --unit-size warns cleanly without failing
            margin_only = resolve_lanes.resolve_from_paths(
                workspace=REPO_ROOT,
                profile_path=profile_path,
                state_path=state_path,
                role="coding",
                now=self.now,
                safety_margin=1.3,
            )
            self.assertTrue(any("--safety-margin is ignored" in w for w in margin_only["warnings"]))


class DispatchOkTests(unittest.TestCase):
    def test_dispatch_ok_helper(self):
        self.assertFalse(resolve_lanes.dispatch_ok(None))
        self.assertTrue(resolve_lanes.dispatch_ok({"deprioritized": False, "projected_deprioritized": False}))
        self.assertFalse(resolve_lanes.dispatch_ok({"deprioritized": True, "projected_deprioritized": False}))
        self.assertFalse(resolve_lanes.dispatch_ok({"deprioritized": True, "projected_deprioritized": True}))
        self.assertFalse(resolve_lanes.dispatch_ok({"deprioritized": False, "projected_overflow": True}))

    def _report(self, state):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            result = run_script(
                "resolve_lanes.py",
                "--workspace", str(REPO_ROOT),
                "--profile", str(REPO_ROOT / "skills" / "astra-orchestration" / "project-profile.example.md"),
                "--role", "coding",
                "--state", str(state_path),
                "--now", "2026-11-21T16:00:00Z",
                "--format", "json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_json_report_flags_deprioritized_recommendation(self):
        busy = {"status": "up", "five_hour_pct": 93, "weekly_pct": 93, "observed_at": "2026-11-21T15:58:00Z"}
        healthy = {"status": "up", "five_hour_pct": 20, "weekly_pct": 20, "observed_at": "2026-11-21T15:58:00Z"}
        everyone_busy = self._report({"claude": busy, "codex": busy, "gemini": busy, "deepseek": busy})
        self.assertIsNotNone(everyone_busy["recommended"])
        self.assertIn("deprioritized", everyone_busy["recommended"]["flags"])
        self.assertIs(everyone_busy["dispatch_ok"], False)
        healthy_report = self._report({"claude": healthy, "codex": healthy, "gemini": healthy, "deepseek": healthy})
        self.assertIs(healthy_report["dispatch_ok"], True)
