"""Regression checks for quota freshness and outage recovery."""

import unittest

from test_resolve_lanes import make_candidate, resolve_lanes


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
                "gemini": {"weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z", "resets_at": "2026-11-21 16:00 UTC"},
                "deepseek": {"status": "down", "down_until": "2026-11-21T18:00:00Z", "observed_at": "2026-11-21T10:00:00Z"},
            },
            self.now,
            5,
        )
        # Never rounds 89.999999 up to 90% or 94.999999 up to 95%.
        self.assertFalse(states["claude"]["excluded"])
        self.assertTrue(states["claude"]["deprioritized"])
        self.assertIn("89.999999%", states["claude"]["reasons"][0])
        self.assertNotIn("90%", states["claude"]["reasons"][0])
        self.assertIsNone(states["claude"]["resets_at"])
        self.assertFalse(states["claude"]["stale"])

        self.assertFalse(states["codex"]["excluded"])
        self.assertTrue(states["codex"]["deprioritized"])
        self.assertIn("94.999999%", states["codex"]["reasons"][0])
        self.assertNotIn("95%", states["codex"]["reasons"][0])
        self.assertFalse(states["codex"]["stale"])

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
