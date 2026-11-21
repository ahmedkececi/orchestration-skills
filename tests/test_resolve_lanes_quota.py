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
        self.assertTrue(any("Confirm live usage" in warning for warning in result["warnings"]))
